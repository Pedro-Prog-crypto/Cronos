"""Independent checks for generated code. Passing is not a security certification."""
import json
import re
import shutil
import subprocess
import tempfile
from html import escape
from html.parser import HTMLParser
from pathlib import Path

FILES = {'index.html', 'styles.css', 'app.js'}
BLOCKED_TAGS = {'iframe', 'object', 'embed', 'base', 'foreignobject', 'animate', 'set'}
ASSET = re.compile(r'^assets/[a-f0-9]{32}\.(jpg|png|glb)$')


class InvalidProject(ValueError):
    pass


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []; self.anchors = []; self.forms = []; self.form_fields = []; self.active_form = None; self.images = []; self.inputs = []; self.tags = []
        self.models = 0
        self.procedural = []
        self.resources = []; self.errors = []; self.title = False; self.viewport = False; self.lang = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs); self.tags.append(tag)
        if tag in BLOCKED_TAGS: self.errors.append('Elemento proibido: ' + tag)
        if any(k.startswith('on') or k in {'srcdoc', 'ping', 'formaction', 'action'} for k, _ in attrs):
            self.errors.append('Eventos inline, formulários externos e documentos embutidos não são permitidos.')
        if len(values) != len(attrs): self.errors.append('Atributos duplicados.')
        if values.get('id'): self.ids.append(values['id'])
        if tag == 'html': self.lang = bool(values.get('lang'))
        if tag == 'title': self.title = True
        if tag == 'style': self.errors.append('Use styles.css, sem CSS inline.')
        if 'style' in values: self.errors.append('Use classes em styles.css, sem atributo style.')
        if tag == 'meta':
            if 'http-equiv' in values: self.errors.append('Metadados HTTP não são permitidos no projeto.')
            if values.get('name') == 'viewport': self.viewport = True
        if 'data-studio-model' in values: self.models += 1
        if 'data-studio-procedural' in values: self.procedural.append(values['data-studio-procedural'])
        if tag == 'form':
            if self.active_form is not None: self.errors.append('Formulários aninhados não são permitidos.')
            self.forms.append(values.get('data-studio-form'))
            self.form_fields.append([]); self.active_form = len(self.form_fields)-1
        if tag in {'input', 'textarea', 'select'}:
            self.inputs.append(values)
            if self.active_form is not None: self.form_fields[self.active_form].append(values)
        if tag == 'img': self.images.append(values)
        for key in ('href', 'src', 'poster', 'srcset', 'xlink:href'):
            value = values.get(key)
            if value is None: continue
            if key == 'srcset': self.errors.append('Use src com um asset local, sem srcset.'); continue
            if value.startswith('#'):
                if tag == 'a': self.anchors.append(value[1:])
                continue
            if tag == 'a' and key == 'href':
                if not re.match(r'^(https://[^\s<>]+|mailto:[\w.+@-]+|tel:[+\d -]+)$', value): self.errors.append('Link externo inválido ou sem destino real.')
            elif tag == 'img' and key == 'src' and value in reference_images():
                self.resources.append(value)
            elif (tag == 'link' and value == 'styles.css') or (tag == 'script' and value == 'app.js') or ASSET.fullmatch(value):
                self.resources.append(value)
            else: self.errors.append('Recurso não autorizado: ' + value[:80])
        if tag == 'script' and values.get('src') != 'app.js': self.errors.append('JavaScript inline ou externo não é permitido.')

    def handle_endtag(self, tag):
        if tag == 'form': self.active_form = None

    def handle_startendtag(self, tag, attrs): self.handle_starttag(tag, attrs)


def parse_bundle(result):
    if result.get('tool_calls'): raise InvalidProject('O modelo pediu ferramentas em vez de gerar o projeto. Nenhuma ferramenta foi executada.')
    raw = result.get('reply', '')
    if not isinstance(raw, str): raise InvalidProject('A IA não retornou código textual.')
    raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw.strip())
    try: payload = json.loads(raw)
    except ValueError: raise InvalidProject('O modelo não entregou o pacote JSON completo. A versão anterior foi preservada. Tente um pedido menor ou um modelo com mais saída.') from None
    if not isinstance(payload, dict) or not isinstance(payload.get('files'), dict): raise InvalidProject('Pacote sem files.')
    files = payload['files']
    if set(files) != FILES or any(not isinstance(v, str) or len(v) > 180_000 for v in files.values()):
        raise InvalidProject('O pacote deve conter somente index.html, styles.css e app.js, até 180 mil caracteres por arquivo.')
    if not isinstance(payload.get('summary'), str) or len(payload['summary']) > 4000: raise InvalidProject('Resumo do projeto ausente ou grande demais.')
    return files, payload['summary']


def validate(files, assets=(), *, run_syntax=True):
    if set(files) != FILES or any(not isinstance(v, str) or len(v) > 180_000 or '\0' in v for v in files.values()):
        raise InvalidProject('Arquivos ou limites inválidos.')
    doc = Document()
    try: doc.feed(files['index.html']); doc.close()
    except Exception: raise InvalidProject('HTML malformado.') from None
    checks = []
    def check(name, ok, detail): checks.append({'name': name, 'status': 'passed' if ok else 'failed', 'detail': detail})
    check('Recursos isolados', not doc.errors, '; '.join(dict.fromkeys(doc.errors)) or 'Sem script externo, eventos inline, frames ou formulários externos.')
    check('IDs e navegação interna', len(set(doc.ids)) == len(doc.ids) and all(anchor and anchor in doc.ids for anchor in doc.anchors), 'IDs únicos e destinos internos existentes.')
    check('Documento responsivo', doc.lang and doc.viewport and doc.title and 'main' in doc.tags, 'Idioma, título, viewport e conteúdo principal presentes; o layout ainda precisa de inspeção no navegador.')
    check('Imagens e recursos', all(img.get('alt') is not None for img in doc.images) and all(not ASSET.fullmatch(r) or r[7:] in assets for r in doc.resources), 'Texto alternativo e arquivos locais existentes.')
    check('Formulários conectados', set(doc.forms) >= {'contact', 'booking'} and all(f in {'contact', 'booking'} for f in doc.forms), 'Contato e solicitação de horário usam o runtime do estúdio.')
    contracts = True
    allowed_fields = {'name', 'email', 'phone', 'message', 'date', 'time', 'service', 'consent', 'company'}
    for kind, inputs in zip(doc.forms, doc.form_fields):
        fields_by_name = {i.get('name'): i for i in inputs}
        needed = {'name', 'email', 'consent', 'message'} if kind == 'contact' else {'name', 'email', 'consent', 'date', 'time', 'service'}
        contracts = contracts and needed <= set(fields_by_name) and set(fields_by_name) <= allowed_fields
        contracts = contracts and fields_by_name.get('email', {}).get('type') == 'email' and fields_by_name.get('consent', {}).get('type') == 'checkbox'
        if kind == 'booking': contracts = contracts and fields_by_name.get('date', {}).get('type') == 'date' and fields_by_name.get('time', {}).get('type') == 'time'
    check('Contrato de cada formulário', contracts, 'Cada formulário tem seus próprios campos, tipos de e-mail/data/horário e consentimento compatíveis com o servidor.')
    fields = {i.get('name') for i in doc.inputs}
    check('Campos de atendimento', {'name', 'email', 'message', 'date', 'time', 'service', 'consent'} <= fields, 'Campos necessários para contato e agendamento presentes.')
    if doc.models:
        check('Modelo 3D conectado', doc.models == 1 and any(name.endswith('.glb') for name in assets), 'O visualizador precisa de um GLB fornecido e um único ponto data-studio-model.')
    if doc.procedural:
        check('Modelo procedural conectado', not doc.models and len(doc.procedural) == 1 and doc.procedural[0] in {'earbuds','airplane','hotel'}, 'Um dos três modelos procedurais enviados, sem GLB obrigatório nem JavaScript remoto.')
    css, js = files['styles.css'], files['app.js']
    css_urls = re.findall(r'url\(\s*[\'"]?([^\)\'"\s]+)', css, re.I)
    check('CSS sem dependências remotas', not re.search(r'@import|expression\s*\(|-moz-binding|javascript:', css, re.I) and all(v.startswith('#') or (ASSET.fullmatch(v) and v[7:] in assets) for v in css_urls), 'CSS não baixa dependências ou imagens não autorizadas.')
    denied = re.search(r'\b(?:fetch|XMLHttpRequest|WebSocket|EventSource|Worker|SharedWorker|eval|Function|importScripts)\s*\(|\bimport\s*(?:[\'"({*]|[A-Za-z_$])|\b(?:document\s*\.\s*cookie|localStorage|sessionStorage)|\b(?:top|parent|opener)\s*[.\[]|\b(?:location|document\.location)\s*(?:[.=\[])|\bserviceWorker\b|\binnerHTML\s*=|\binsertAdjacentHTML\s*\(', js)
    check('JavaScript sem acesso ao sistema', not denied, 'Código gerado não usa rede, armazenamento do navegador, frames-pai, avaliação dinâmica ou HTML não sanitizado.')
    # This check only parses; it does not execute generated JavaScript on the host.
    node = shutil.which('node') if run_syntax else None
    if node:
        with tempfile.TemporaryDirectory(prefix='cronos-js-check-') as directory:
            path = Path(directory) / 'app.js'; path.write_text(js, encoding='utf-8')
            try:
                result = subprocess.run([node, '--check', str(path)], capture_output=True, timeout=5, shell=False, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                diagnostic = result.stderr.decode('utf-8', errors='replace').replace(str(path), 'app.js')[-1500:] if result.returncode else ''
                check('Sintaxe JavaScript', result.returncode == 0, 'Parser Node.js; não executa o código do projeto.' + ('\n' + diagnostic if diagnostic else ''))
            except (OSError, subprocess.TimeoutExpired): checks.append({'name': 'Sintaxe JavaScript', 'status': 'unavailable', 'detail': 'Parser não respondeu; verifique no navegador.'})
    else: checks.append({'name': 'Sintaxe JavaScript', 'status': 'unavailable', 'detail': 'Node não encontrado; nada foi instalado. Verifique no navegador.'})
    return {'checks': checks, 'passed': not any(c['status'] == 'failed' for c in checks), 'browser': None,
            'limitations': ['Análise estática não comprova correção de todo JavaScript nem ausência de vulnerabilidades.', 'Execute os testes no navegador e revise conteúdo, direitos de imagem, privacidade, hospedagem e integrações antes de vender/publicar.']}


def reference_images():
    from .references import REFERENCE_SITES
    return {url for ref in REFERENCE_SITES.values() for url in ref.sample_images}


class InlinePreview(HTMLParser):
    def __init__(self, files, assets, nonce):
        super().__init__(convert_charrefs=False)
        self.files, self.assets, self.nonce, self.parts, self.skip_script = files, assets, nonce, [], False

    def handle_decl(self, decl): self.parts.append('<!' + decl + '>')
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'link' and values.get('href') == 'styles.css':
            self.parts.append('<style nonce="' + self.nonce + '">' + re.sub(r'</style', r'<\\/style', self.files['styles.css'], flags=re.I) + '</style>'); return
        if tag == 'script': self.skip_script = True; return
        result = []
        for key, value in attrs:
            if value and value.startswith('assets/'): value = self.assets.get(value[7:], '')
            if value is not None: result.append(key + '="' + escape(value, quote=True) + '"')
            else: result.append(key)
        if tag == 'a' and values.get('target') == '_blank': result.append('rel="noopener noreferrer"')
        self.parts.append('<' + tag + (' ' + ' '.join(result) if result else '') + '>')
    def handle_endtag(self, tag):
        if tag == 'script': self.skip_script = False; return
        if tag in {'body', 'html'}: return
        self.parts.append('</' + tag + '>')
    def handle_data(self, data):
        if not self.skip_script: self.parts.append(data)
    def handle_entityref(self, name): self.parts.append('&' + name + ';')
    def handle_charref(self, name): self.parts.append('&#' + name + ';')
    def handle_startendtag(self, tag, attrs):
        before = len(self.parts)
        self.handle_starttag(tag, attrs)
        if len(self.parts) > before and tag not in {'script', 'link'}:
            self.parts[-1] = self.parts[-1][:-1] + '/>'
