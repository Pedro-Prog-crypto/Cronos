import io
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from cronos.app import create_app
from cronos.studies import LAYOUTS, MAX_LIBRARY_BYTES, MAX_PDF_BYTES, StudyStore, _PageText, _media_search_terms, _public_http_url
from cronos.study_intent import is_study_request, requests_exhaustive_lookup
from test_backend import AUTH, settings


def pdf_bytes():
    writer = PdfWriter()
    writer.add_blank_page(width=240, height=240)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_subjects_and_study_files_persist_separately_from_general_memory(settings):
    with TestClient(create_app(settings)) as client:
        assert client.get('/studies/overview').status_code == 401
        created = client.post('/studies/subjects', headers=AUTH, json={'name': 'Biologia'})
        assert created.status_code == 200
        subject = created.json()
        uploaded = client.post(f"/studies/subjects/{subject['id']}/sources?name=celulas.pdf",
                               headers={**AUTH, 'Content-Type': 'application/pdf'}, content=pdf_bytes())
        assert uploaded.status_code == 200
        source = uploaded.json()
        assert source['filename'] == 'celulas.pdf' and source['page_count'] == 1
        file_response = client.get(f"/studies/sources/{source['id']}/file", headers=AUTH)
        assert file_response.status_code == 200 and file_response.content.startswith(b'%PDF-')
        refreshed = client.get('/studies/overview', headers=AUTH).json()
        assert refreshed['subjects'][0]['source_count'] == 1
        assert refreshed['storage']['used_bytes'] == len(pdf_bytes())

    assert (settings.vault / 'Estudos' / 'estudos.sqlite3').exists()
    assert not list((settings.vault / 'Temas').glob('*'))


def test_pdf_upload_rejects_non_pdf_and_duplicate_sources(settings):
    with TestClient(create_app(settings)) as client:
        subject = client.post('/studies/subjects', headers=AUTH, json={'name': 'História'}).json()
        url = f"/studies/subjects/{subject['id']}/sources?name=aula.pdf"
        headers = {**AUTH, 'Content-Type': 'application/pdf'}
        assert client.post(url, headers=headers, content=b'not a pdf').status_code == 415
        assert client.post(url, headers=headers, content=pdf_bytes()).status_code == 200
        assert client.post(url, headers=headers, content=pdf_bytes()).status_code == 409
        assert client.post(f"/studies/subjects/{subject['id']}/sources?name=../fora.txt",
                           headers=headers, content=pdf_bytes()).status_code == 415


def test_lesson_uses_only_relevant_pages_and_saves_rotating_layouts(settings):
    class Tutor:
        calls = []

        async def reply(self, system, messages):
            self.calls.append((system, messages))
            return {'reply': '## Ideia central\nA célula transforma energia e mantém a vida.\n\n- Exemplo: a mitocôndria.', 'topics': [], 'tool_calls': []}

    tutor = Tutor()
    store = StudyStore(settings.vault / 'Estudos')
    subject = store.create_subject('Biologia')
    temp = settings.vault / 'fonte.pdf'
    temp.parent.mkdir(parents=True, exist_ok=True)
    temp.write_bytes(b'%PDF-stored-fixture')
    store.add_source(subject['id'], 'biologia.pdf', temp, temp.stat().st_size, 'a' * 64,
                     ['A célula é a unidade básica da vida. A mitocôndria participa da produção de energia.', 'Um parágrafo sobre outro assunto.'])
    with TestClient(create_app(settings, tutor)) as client:
        result = client.post(f"/studies/subjects/{subject['id']}/lessons", headers=AUTH,
                             json={'question': 'Explique a mitocôndria na célula.'})
        assert result.status_code == 200, result.text
        lesson = result.json()
        assert lesson['answer'].startswith('## Ideia central')
        assert lesson['citations'] and lesson['citations'][0]['source'] == 'biologia.pdf'
        assert 'FONTE: biologia.pdf, página 1' in tutor.calls[0][0]
        assert 'outro assunto' not in tutor.calls[0][0]
        assert lesson['layout'] in LAYOUTS
        history = client.get(f"/studies/subjects/{subject['id']}/sources", headers=AUTH).json()['lessons']
        assert history[0]['id'] == lesson['id']


def test_study_limits_are_large_but_bounded():
    assert MAX_PDF_BYTES == 100 * 1024 * 1024
    assert MAX_LIBRARY_BYTES == 5 * 1024 * 1024 * 1024


def test_study_intent_prefers_deep_explanation_and_allows_requested_complete_web_lists():
    assert is_study_request('Me explica a Primeira Guerra Mundial com exemplos do cotidiano.')
    assert is_study_request('Quais são todas as obras do PAIS?')
    assert requests_exhaustive_lookup('Cronos, me fale todas as obras do PAIS.')
    assert requests_exhaustive_lookup('Quero a lista completa de leis vigentes.')
    assert not requests_exhaustive_lookup('Não pesquise na web; explique o conceito de fotossíntese.')


def test_visual_explanation_intent_covers_people_processes_and_events_without_grabbing_small_talk():
    assert is_study_request('Quem foi Sócrates?')
    assert is_study_request('Como funciona um avião a jato?')
    assert is_study_request('O que aconteceu na crise de 1929?')
    assert is_study_request('Me conta sobre as ideias políticas de Darcy Ribeiro.')
    assert is_study_request('Analise os argumentos de cada candidato nesta eleição.')
    assert not is_study_request('Cronos, você está me ouvindo?')
    assert not is_study_request('Coloca minha música preferida.')


def test_visual_media_search_expands_famous_subjects_into_searchable_image_terms():
    terms = _media_search_terms('Sócrates e o julgamento')
    assert 'Socrates ancient Greek philosopher' in terms
    assert 'portrait bust sculpture' in terms
    assert _media_search_terms('Restaurante Casa Azul') == 'Restaurante Casa Azul'


def test_media_endpoint_returns_a_dense_openly_attributed_image_wall_and_licensed_video(settings, monkeypatch):
    class Response:
        def __init__(self, payload): self.payload = payload
        def raise_for_status(self): pass
        def json(self): return self.payload

    class Client:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url, params=None, **kwargs):
            pages=[]
            for index in range(20):
                is_video=index==0
                ext='webm' if is_video else 'jpg'
                base=f'https://upload.wikimedia.org/wikipedia/commons/demo/{index}.{ext}'
                pages.append({'title':f'File:Visual {index}.{ext}','imageinfo':[{
                    'url':base,'thumburl':base.replace(f'.{ext}', '.jpg'),
                    'descriptionurl':f'https://commons.wikimedia.org/wiki/File:Visual_{index}',
                    'extmetadata':{'LicenseShortName':{'value':'CC BY-SA'},'Artist':{'value':'Artist'}}}]})
            return Response({'query':{'pages':pages}})
        def stream(self, method, url, **kwargs):
            class Stream:
                status_code=200
                headers={'content-type':'image/jpeg','content-length':'3'}
                async def __aenter__(self): return self
                async def __aexit__(self,*args): pass
                async def aiter_bytes(self,chunk_size=65536): yield b'\xff\xd8\xff'
            return Stream()

    monkeypatch.setattr('cronos.studies.httpx.AsyncClient', Client)
    monkeypatch.setattr('cronos.studies._public_http_url', lambda value: value)
    with TestClient(create_app(settings)) as client:
        response=client.get('/studies/images?query=S%C3%B3crates&limit=18',headers=AUTH)
        image_response=client.get(response.json()['images'][0]['proxy_url'],headers=AUTH)
        poster_response=client.get(response.json()['videos'][0]['poster_proxy_url'],headers=AUTH)
    assert response.status_code==200,response.text
    result=response.json()
    assert len(result['images'])==18
    assert result['images'][0]['license']=='CC BY-SA'
    assert result['images'][0]['proxy_url'].startswith('/studies/media/')
    assert image_response.status_code==200
    assert image_response.headers['content-type']=='image/jpeg'
    assert image_response.content==b'\xff\xd8\xff'
    assert result['videos'][0]['kind']=='video'
    assert result['videos'][0]['poster_proxy_url'].startswith('/studies/media/')
    assert poster_response.status_code==200 and poster_response.content==b'\xff\xd8\xff'
    assert 'ancient Greek philosopher' in result['search_query']


def test_media_endpoint_falls_back_to_openverse_when_commons_has_no_matches(settings, monkeypatch):
    class Response:
        def __init__(self,payload):self.payload=payload
        def raise_for_status(self):pass
        def json(self):return self.payload

    class Client:
        def __init__(self,*args,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def get(self,url,params=None,**kwargs):
            if 'commons.wikimedia.org' in url:return Response({'query':{'pages':[]}})
            items=[{'url':f'https://media.example/{i}.jpg','thumbnail':f'https://thumb.example/{i}.jpg',
                    'foreign_landing_url':f'https://openverse.example/{i}','title':f'Open image {i}',
                    'creator':'Public artist','license':'cc-by'} for i in range(params['page_size'])]
            return Response({'results':items})

    monkeypatch.setattr('cronos.studies.httpx.AsyncClient',Client)
    with TestClient(create_app(settings)) as client:
        response=client.get('/studies/images?query=filosofia&limit=12',headers=AUTH)
    assert response.status_code==200,response.text
    result=response.json()
    assert len(result['images'])==12
    assert {item['provider'] for item in result['images']}=={'Openverse'}


def test_web_source_is_saved_and_retrieved_by_indexed_text(tmp_path):
    store = StudyStore(tmp_path / 'study')
    subject = store.create_subject('História')
    text = ('A Primeira Guerra Mundial começou em 1914 após a crise de julho. ' * 6)
    result = store.add_link_source(subject['id'], 'Primeira Guerra — artigo', 'https://example.org/guerra', text)
    assert result['kind'] == 'link'
    assert result['source_url'] == 'https://example.org/guerra'
    assert store.sources(subject['id'])[0]['kind'] == 'link'
    pages = store.relevant_pages(subject['id'], 'crise de julho em 1914')
    assert pages and pages[0]['source'] == 'Primeira Guerra — artigo'
    assert 'crise de julho' in pages[0]['text']
    assert store.source_path(result['id']) is None


def test_web_page_parser_ignores_scripts_and_private_urls():
    parser = _PageText()
    parser.feed('<html><title>História</title><body><h1>Fonte primária</h1><p>Texto importante.</p><script>ignore segredo</script></body></html>')
    assert 'História' in parser.title_parts
    assert 'Texto importante.' in ''.join(parser.parts)
    assert 'ignore segredo' not in ''.join(parser.parts)
    for url in ('http://127.0.0.1/admin', 'http://localhost/', 'file:///etc/passwd', 'https://user:pass@example.org/'):
        try:
            _public_http_url(url)
        except ValueError:
            pass
        else:
            raise AssertionError(f'unsafe URL accepted: {url}')


def test_link_import_route_stores_a_public_page_in_the_selected_subject(settings, monkeypatch):
    async def fake_fetch(url):
        return 'link', 'Aula pública', 'Texto de aula sobre fotossíntese e a transformação de luz em energia. ' * 5
    monkeypatch.setattr('cronos.studies._fetch_study_link', fake_fetch)
    with TestClient(create_app(settings), base_url='http://localhost', client=('127.0.0.1', 12345)) as client:
        subject = client.post('/studies/subjects', headers=AUTH, json={'name': 'Biologia'}).json()
        result = client.post(f"/studies/subjects/{subject['id']}/links", headers=AUTH,
                             json={'url': 'https://example.org/aula'})
        assert result.status_code == 200, result.text
        assert result.json()['kind'] == 'link'
        assert result.json()['filename'] == 'Aula pública'
        duplicate = client.post(f"/studies/subjects/{subject['id']}/links", headers=AUTH,
                                json={'url': 'https://example.org/aula'})
        assert duplicate.status_code == 409
