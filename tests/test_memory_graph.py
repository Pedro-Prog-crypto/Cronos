from uuid import uuid4
from cronos.memory import Memory
from fastapi.testclient import TestClient
from cronos.app import create_app
from test_backend import AUTH, settings


def test_graph_has_real_notes_resolves_links_and_ignores_missing_or_ambiguous(tmp_path):
    memory=Memory(tmp_path/'vault')
    (memory.vault/'Platão.md').write_text('# Platão\n[[Sócrates]] [[Ausente]] [[Sócrates|mestre]]')
    (memory.vault/'Sócrates.md').write_text('# Sócrates\n[[Platão#Vida]]')
    memory.sync_notes()
    graph=memory.graph()
    assert len(graph['nodes'])==2
    assert graph['edges']==[{'source':'Platão.md','target':'Sócrates.md'}]
    assert memory.graph(0,1)['next_offset']==1
    (memory.vault/'Sócrates.md').unlink();memory.sync_notes()
    assert not memory.graph()['edges']


def test_each_turn_creates_an_immutable_markdown_memory(tmp_path):
    memory=Memory(tmp_path/'vault');session=uuid4()
    memory.record(session,'Quem foi Platão?','Resposta 1',[{'title':'Platão','summary':'Resumo 1'}])
    memory.record(session,'E suas ideias?','Resposta 2',[{'title':'Platão','summary':'Resumo 2'}])
    records=list((memory.vault/'Memorias').glob('*.md'))
    assert len(records)==2
    contents=''.join(path.read_text() for path in records)
    assert 'Resposta 1' in contents and 'Resposta 2' in contents
    assert memory.stats()['pending_exports']==0
    assert len(list((memory.vault/'Temas').glob('*.md')))==1
    memory.flush_exports()
    assert len(list((memory.vault/'Memorias').glob('*.md')))==2
    assert memory.graph()['edges']


def test_graph_is_authenticated_and_paged(settings):
    with TestClient(create_app(settings)) as client:
        assert client.get('/memory/graph').status_code==401
        assert client.get('/memory/graph?limit=1001',headers=AUTH).status_code==422
        assert client.get('/memory/graph',headers=AUTH).json()=={'nodes':[],'edges':[],'total':0,'next_offset':None}
        assert client.get('/world/places?q=Lisboa').status_code==401
