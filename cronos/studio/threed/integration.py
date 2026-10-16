"""Connect the complete supplied templates to Cronos' preview/forms/export contracts.

Originals are retained byte for byte in ../mistral_original. This module does not
execute model-authored code on the host, change credentials, or contact an AI.
"""
import json
import re
from html import escape
from html.parser import HTMLParser
from pathlib import Path

from ..references import REFERENCE_SITES, get_reference
from .config import FREE_3D_MODEL_SOURCES
from .models import get_model, list_models
from .pricing_config import PRICING_TIERS

ROOT = Path(__file__).parent
MODEL_NAMES = {'earbuds': 'Fones com estojo', 'airplane': 'Avião comercial', 'hotel': 'Edifício com andares'}
TEMPLATES = {'basic', 'standard', 'premium'}


def wants_3d(text):
    text=text.casefold()
    text=re.sub(r'\b(?:sem|n[aã]o(?:\s+(?:quero|use|usar|utilize|utilizar|coloque|incluir|inclua|preciso))?|dispensar)\s+(?:(?:um|uma|o|nenhum|visualizador|modelo|efeito|site|em|de)\s+){0,4}(?:3d|3-d|tr[eê]s dimens[oõ]es)\b','',text)
    return bool(re.search(r'\b(?:3d|3-d|tr[eê]s dimens[oõ]es)\b',text))


def reference_id(category, brief='', requested=''):
    if requested:
        if requested not in REFERENCE_SITES or REFERENCE_SITES[requested].category != category:
            raise ValueError('Escolha uma referência que pertença à categoria do projeto.')
        return requested
    if wants_3d(brief) and category + '_3d' in REFERENCE_SITES:
        return category + '_3d'
    return category if category in REFERENCE_SITES else 'personalizado'


def selected_model(category, brief='', requested='auto'):
    if requested != 'auto':
        if requested not in MODEL_NAMES: raise ValueError('Modelo procedural não encontrado.')
        return requested
    text = brief.casefold()
    if any(term in text for term in ('avião', 'aviao', 'aeronave')): return 'airplane'
    if category in {'hotel', 'imobiliaria', 'eventos'}: return 'hotel'
    return 'earbuds'


def suggested_model(category, brief='', requested='auto'):
    """AI projects should not receive unrelated earphones just for choosing 3D."""
    if requested != 'auto':return selected_model(category,brief,requested)
    text=brief.casefold()
    if any(term in text for term in ('avião','aviao','aeronave')):return 'airplane'
    if any(term in text for term in ('fone','earbud','headphone','buds')):return 'earbuds'
    if category in {'hotel','imobiliaria'}:return 'hotel'
    return None


def reference_payload(identifier):
    ref = REFERENCE_SITES[identifier]
    return {'id': identifier, **ref.to_dict(), 'demo': True,
            'notice': 'Referência demonstrativa fornecida pelo usuário. Confira dados, recursos e direitos das fotografias antes de publicar; integrações comerciais não são configuradas por um template.'}


def enrich_catalog(items):
    return [{**item, 'references': [reference_payload(key) for key, ref in REFERENCE_SITES.items() if ref.category == item['id']],
             'templates': ['basic', 'standard', 'premium'], 'models': [{'id': key, 'name': value} for key, value in MODEL_NAMES.items()]}
            for item in items]


def pricing_options():
    return [{'id': key, **value, 'estimate_only': True} for key, value in PRICING_TIERS.items()]


def estimate(category, brief, old, *, tier='reference', reference=''):
    ref = REFERENCE_SITES[reference_id(category, brief, reference)]
    wants_3d = old.get('has_3d', False) or (tier == 'reference' and ref.template_type == '3d') or tier == 'premium_3d'
    if tier == 'reference':
        low, high = ref.price_range
        if wants_3d and ref.template_type != '3d': low, high = 5000, 15000
        elif old.get('complex_features'): low, high = old['min'], old['max']
        label = ref.name
    else:
        if tier not in PRICING_TIERS: raise ValueError('Faixa de preço desconhecida.')
        if wants_3d and tier != 'premium_3d': tier = 'premium_3d'
        low, high = PRICING_TIERS[tier]['price_range']; label = PRICING_TIERS[tier]['name']
    return {**old, 'min': low, 'max': high, 'tier': tier, 'tier_name': label, 'has_3d': wants_3d,
            'site_type': '3d' if wants_3d else ('2d' if ref.template_type == '3d' else ref.template_type),
            'difficulty': 'Avançada' if wants_3d else old['difficulty']}


class Compiler(HTMLParser):
    """Lift known template styles without changing their design or weakening CSP."""
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts, self.css, self.scripts = [], [], []
        self.mode = None
        self.label_depth = 0
        self.extra_textarea_label = False
    def handle_decl(self, decl): self.parts.append('<!' + decl + '>')
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'header' and self.model: values['class'] = (values.get('class','') + ' header').strip()
        if tag == 'label': self.label_depth += 1
        wrap_label = tag in {'input','textarea','select'} and not self.label_depth and values.get('type') != 'hidden'
        if wrap_label:
            label = {'name':'Nome','email':'E-mail','message':'Mensagem','phone':'Telefone','service':'Serviço','date':'Data','time':'Horário'}.get(values.get('name'), values.get('placeholder', 'Campo'))
            self.parts.append('<label>' + escape(label))
            if tag in {'textarea','select'}: self.extra_textarea_label = True
        if tag == 'style': self.mode = 'style'; return
        if tag == 'script':
            self.mode = 'discard' if values.get('src') else 'script'
            return
        if 'style' in values:
            name = 'cs-inline-' + str(len(self.css))
            self.css.append('.' + name + '{' + values.pop('style') + '}')
            values['class'] = (values.get('class', '') + ' ' + name).strip()
        if values.get('id') == 'canvas-container': values['data-studio-procedural'] = self.model
        if tag == 'form': values['data-studio-form'] = values.get('data-studio-form', 'contact')
        self.parts.append('<' + tag + ''.join(' ' + k + ('="' + escape(v, quote=True) + '"' if v is not None else '') for k, v in values.items()) + '>')
        if wrap_label and tag == 'input': self.parts.append('</label>')
    def handle_endtag(self, tag):
        if tag in {'style', 'script'}: self.mode = None; return
        self.parts.append('</' + tag + '>')
        if tag == 'label': self.label_depth = max(0,self.label_depth-1)
        if tag in {'textarea','select'} and self.extra_textarea_label:
            self.parts.append('</label>'); self.extra_textarea_label = False
    def handle_data(self, text):
        if self.mode == 'style': self.css.append(text)
        elif self.mode == 'script': self.scripts.append(text)
        elif self.mode != 'discard': self.parts.append(text)
    def handle_entityref(self, name): self.handle_data('&' + name + ';')
    def handle_charref(self, name): self.handle_data('&#' + name + ';')
    def handle_startendtag(self, tag, attrs): self.handle_starttag(tag, attrs)


CONSENT = '<label class="consent"><input type="checkbox" name="consent" required>Autorizo o uso dos dados para responder à solicitação.</label><p data-form-status role="status"></p>'
BOOKING = '<section class="cs-booking" id="agendamento"><h2>Solicite um horário</h2><form data-studio-form="booking"><label>Nome<input name="name" required maxlength="100"></label><label>E-mail<input name="email" type="email" required maxlength="180"></label><label>Serviço<input name="service" required maxlength="160" value="Atendimento"></label><label>Data<input name="date" type="date" required></label><label>Horário<input name="time" type="time" required></label>' + CONSENT + '<button type="submit">Solicitar horário</button></form><p>A solicitação depende de confirmação da equipe.</p></section>'
COMMON_CSS = '''img{max-width:100%;height:auto}button,input,textarea,select{font:inherit}button{cursor:pointer}a:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible{outline:3px solid #60a5fa;outline-offset:4px}.cs-booking{padding:4rem 2rem;max-width:1000px;margin:auto}.cs-booking form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}.cs-booking label{display:grid;gap:.5rem}.cs-booking input,.cs-booking button{padding:.8rem;min-width:0}.cs-concept{padding:12px 2rem;font-size:13px;line-height:1.6}.cs-controls{display:flex;gap:10px;flex-wrap:wrap;padding:1rem 2rem}.cs-controls button{padding:10px 16px;color:inherit;background:transparent;border:1px solid currentColor;border-radius:5px;min-height:44px}.cs-booking .consent,.cs-booking [data-form-status]{grid-column:1/-1}.consent{display:flex;gap:.7rem;align-items:center}.consent input{width:auto}.cs-booking button{color:inherit;background:transparent;border:1px solid currentColor}.cs-demo-notice{padding:12px 2rem;border-bottom:1px solid #8885;font:13px/1.6 Arial,sans-serif}#canvas-container{min-width:0;flex-basis:50%;width:100%;height:70vh;min-height:360px}#canvas-container canvas{width:100%;height:100%;display:block}@media(max-width:760px){.cs-booking form{grid-template-columns:1fr}.hero-content{min-width:0}#canvas-container{flex:none;height:52vh;min-height:300px}.hero{gap:1rem}.nav-links{flex-wrap:wrap;gap:.8rem}header{max-width:100vw}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{animation:none!important;transition:none!important}.feature-card{opacity:1!important;transform:none!important}}'''


def normalize(files, *, model='', notice=True):
    compiler = Compiler(); compiler.model = model
    compiler.feed(files['index.html']); compiler.close()
    html = ''.join(compiler.parts)
    css = files.get('styles.css', '').replace('{{', '{').replace('}}', '}')
    # Supplied BASE_CSS has unmatched media braces; preserve rules and close them.
    css += '}' * max(0, css.count('{') - css.count('}'))
    css += '\n' + '\n'.join(compiler.css) + '\n' + COMMON_CSS
    css += '\n#canvas-container .cs-controls{position:absolute;bottom:0;left:0;right:0;z-index:5;background:#0f172acc;padding:12px}#canvas-container .cs-concept{position:absolute;left:0;right:0;top:0;z-index:4;margin:0;background:#0f172acc;font-size:11px;padding:10px}.cs-booking input{background:var(--glass,#ffffff0a);color:inherit;border:1px solid #8887;border-radius:4px}.cs-booking .consent{display:flex;align-items:center;gap:10px}.cs-booking .consent input{width:18px;flex:none}'
    js = files.get('app.js', '') + '\n' + '\n'.join(compiler.scripts)
    js = re.sub(r"\s*document\.(?:getElementById\('contact-form'\)|querySelector\('\.contact-form'\))\??\.addEventListener\('submit',\s*\(e\)\s*=>\s*\{[^{}]*alert\([^;]*;\s*\}\);", '', js)
    if '<main' not in html:
        html = re.sub(r'(<body[^>]*>)', r'\1<main>', html, count=1).replace('</body>', '</main></body>')
    if 'name="description"' not in html:
        html = html.replace('</head>', '<meta name="description" content="Referência demonstrativa do Cronos Studio"></head>')
    if 'href="styles.css"' not in html: html = html.replace('</head>', '<link rel="stylesheet" href="styles.css"></head>')
    html = html.replace('</head>', '<script src="app.js" defer></script></head>')
    if 'data-studio-form="contact"' in html and 'name="consent"' not in html:
        html = html.replace('</form>', CONSENT + '</form>', 1)
    if 'data-studio-form="booking"' not in html: html = html.replace('</main>', BOOKING + '</main>', 1)
    if 'id="recursos"' not in html: html = html.replace('class="features"', 'class="features" id="recursos"', 1)
    if 'id="contato"' not in html: html = html.replace('class="contact"', 'class="contact" id="contato"', 1)
    if notice:
        html = re.sub(r'(<body[^>]*>)', r'\1<p class="cs-demo-notice">Referência demonstrativa enviada ao Cronos. Textos e imagens de exemplo precisam ser confirmados antes de publicar.</p>', html, count=1)
    if model:
        html = re.sub(r'<div class="controls">.*?</div>', '', html, count=1, flags=re.S)
        controls = '<div class="controls cs-controls" aria-label="Controles do modelo 3D">' + ''.join('<button type="button" data-cs-action="' + action + '">' + title + '</button>' for action, title in [('rotate','Rotacionar'),('zoom-in','Aproximar'),('zoom-out','Afastar'),('reset','Resetar'),('explode','Explodir'),('transparent','Transparência')] + ([('open','Abrir estojo'),('close','Fechar estojo')] if model == 'earbuds' else [('takeoff','Decolar'),('landing','Pousar'),('fly','Voar')] if model == 'airplane' else [])) + '</div><p class="cs-concept">Modelo procedural conceitual: ' + MODEL_NAMES[model] + '. Não é uma reprodução técnica de um produto ou imóvel real.</p>'
        html = re.sub(r'(<div[^>]*data-studio-procedural[^>]*>)(</div>)', lambda match: match[1] + controls + match[2], html, count=1)
    return {'index.html': html, 'styles.css': css, 'app.js': js}


def template_site(category, name, *, reference='', tier='reference', model='auto', template='premium', brief=''):
    from .generator import Site3DGenerator
    identifier = reference_id(category, brief, reference)
    ref = REFERENCE_SITES[identifier]
    from ..catalog import quote
    price = quote(category, brief, tier, identifier)
    money = lambda amount: 'R$' + format(amount, ',').replace(',', '.')
    price_text = money(price['min']) + '–' + money(price['max'])
    has_3d = (tier == 'reference' and ref.template_type == '3d') or tier == 'premium_3d' or bool(re.search(r'\b(?:3d|3-d)\b', brief.casefold()))
    if has_3d:
        model = selected_model(category, brief, model)
        if template == 'premium':
            html = (ROOT/'templates/premium.html').read_text()
            for key,value in {'[NOME]':name,'[SUBTÍTULO]':ref.sample_texts.get('hero_subtitle',''),'[TÍTULO PRINCIPAL]':ref.sample_texts['hero_title'],'[DESCRIÇÃO ATRAENTE]':ref.sample_texts['hero_description']}.items():
                html = html.replace(key,escape(value.replace('[NOME]',name),quote=True))
            for index,feature in enumerate(ref.features[:3],1): html = html.replace('Recurso '+str(index),escape(feature))
            # The complete original script remains in the source template. The
            # app uses the complete models.py scene and its trusted controls,
            # avoiding two renderers/listeners and the template's fake submit.
            html = re.sub(r'<script>.*?</script>', '', html, flags=re.S)
            files = normalize({'index.html':html},model=model)
            files['styles.css'] += '\n:root{' + ';'.join('--'+key+':'+value for key,value in ref.color_scheme.items() if key in {'primary','secondary','accent'}) + ';--bg:'+ref.color_scheme['background']+';--text:'+ref.color_scheme['text']+'}'
            files['app.js'] = "window.addEventListener('scroll',()=>{document.querySelector('header')?.classList.toggle('scrolled',scrollY>50);},{passive:true});"
            return files
        generated = Site3DGenerator().generate_3d_site(category, escape(name, quote=True), model, template,
                     color_scheme=ref.color_scheme, sample_texts={k: escape(v.replace('[NOME]', name), quote=True) for k, v in ref.sample_texts.items()}, features=ref.features[:3])
        generated['app.js'] = ''  # Scene code is injected from the trusted supplied module, not model-authored JS.
        return normalize(generated, model=model)
    if template in {'basic', 'standard'}:
        html = (ROOT / 'templates' / (template + '.html')).read_text()
        html = html.replace('R$[PREÇO],-[PREÇO]', price_text)
        replacements = {'[NOME]': name, '[TÍTULO PRINCIPAL]': ref.sample_texts['hero_title'], '[DESCRIÇÃO ATRAENTE]': ref.sample_texts['hero_description'], '[DESCRIÇÃO CURTA]': ref.sample_texts['hero_description'], '[PREÇO]': str(ref.price_range[0])}
        for key, value in replacements.items(): html = html.replace(key, escape(value, quote=True))
        for index, feature in enumerate(ref.features[:3], 1): html = html.replace('Recurso ' + str(index), escape(feature))
        files = normalize({'index.html': html})
        files['styles.css'] += '\n:root{--primary:' + ref.color_scheme['primary'] + ';--secondary:' + ref.color_scheme['secondary'] + ';--bg:' + ref.color_scheme['background'] + ';--text:' + ref.color_scheme['text'] + '}'
        files['app.js'] += "\ndocument.querySelector('.hero button')?.addEventListener('click',()=>document.querySelector('#recursos')?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'}));"
        return files
    from ..catalog import starter
    files = starter(category, name, reference_id=identifier)
    files['index.html'] = re.sub(r'Faixa de preço:[^<]*', 'Faixa de preço: ' + price_text, files['index.html'])
    return files


def procedural_kind(html):
    values = re.findall(r'data-studio-procedural=[\'\"]([^\'\"]+)', html)
    if not values: return None
    if len(values) != 1 or values[0] not in MODEL_NAMES: raise ValueError('Escolha somente um dos três modelos procedurais fornecidos.')
    return values[0]


def libraries():
    return '\n'.join((ROOT/'vendor'/name).read_text() for name in ('three-0.128.0.min.js', 'orbit-controls-0.128.0.js', 'gsap-3.11.4.min.js'))


def scene_code(model):
    from .generator import Site3DGenerator
    code = Site3DGenerator()._generate_js(get_model(model), get_reference('personalizado').color_scheme)
    # The supplied generator duplicates smaller model functions. Connect its
    # controls to the complete geometry in models.py, including roof, antenna,
    # entrance, windows, buttons, lights and all ten floors.
    metadata = {
        'earbuds': "earbudLeftGroup.userData.originalPosition=earbudLeftGroup.position.clone();earbudRightGroup.userData.originalPosition=earbudRightGroup.position.clone();earbudGroup.userData={type:'earbuds',lid:caseLid,leftEarbud:earbudLeftGroup,rightEarbud:earbudRightGroup};",
        'airplane': "airplaneGroup.userData={type:'airplane'};",
        'hotel': "const floors=hotelGroup.children.filter(o=>o.isGroup);floors.forEach((o,i)=>{o.userData.floor=i;o.userData.originalPosition=o.position.clone();});hotelGroup.userData={type:'hotel',floors};"
    }
    groups = {'earbuds': 'earbudGroup', 'airplane': 'airplaneGroup', 'hotel': 'hotelGroup'}
    for identifier in MODEL_NAMES:
        group = groups[identifier]
        geometry = get_model(identifier).models[0]['geometry']['code']
        geometry = geometry.replace('return ' + group + ';', metadata[identifier] + '\nmodelGroup.add(' + group + ');')
        function = 'create' + identifier.title() + 'Model'
        code = re.sub(r'function ' + function + r'\(\) \{.*?^\}', lambda match: 'function ' + function + '(){\n' + geometry + '\n}', code, count=1, flags=re.S|re.M)
    # All original model geometry/control functions are kept. Fix group metadata,
    # container measurements and frame lifetime at this trusted integration boundary.
    code = code.replace('    // Centralizar câmera\n    centerCamera();', '    modelGroup.userData = modelGroup.children[0].userData;\n    modelGroup.traverse(o=>{o.userData.csPosition=o.position.clone();o.userData.csRotation=o.rotation.clone();if(o.isMesh&&o.material)o.material=o.material.clone();});\n    // Centralizar câmera\n    centerCamera();')
    code = code.replace("if (window.scrollY > 50)", "if (!header) return;\n        if (window.scrollY > 50)")
    code = code.replace('mouse.x = (event.clientX / window.innerWidth) * 2 - 1;\n    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;', 'const rect=renderer.domElement.getBoundingClientRect();\n    mouse.x=((event.clientX-rect.left)/rect.width)*2-1;\n    mouse.y=-((event.clientY-rect.top)/rect.height)*2+1;')
    code = code.replace('renderer.setPixelRatio(window.devicePixelRatio);', 'renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1));')
    code = code.replace('renderer.setSize(window.innerWidth, window.innerHeight);', "renderer.setSize(document.getElementById(CONFIG.canvasContainer).clientWidth,document.getElementById(CONFIG.canvasContainer).clientHeight);")
    code = code.replace('window.innerWidth / window.innerHeight', '(document.getElementById(CONFIG.canvasContainer).clientWidth / document.getElementById(CONFIG.canvasContainer).clientHeight)')
    code = code.replace("    // Formulário de contato\n    document.getElementById('contact-form')?.addEventListener('submit', (e) => {\n        e.preventDefault();\n        alert('Mensagem enviada! (Demo - formulário não funcional)');\n    });", '')
    code = code.replace('function animate() {\n    requestAnimationFrame(animate);', 'let lastFrame=0,frameId=0,renderedFrames=0,canvasVisible=true;\nfunction animate(now=0) {\n    frameId=requestAnimationFrame(animate);\n    if(document.hidden||!canvasVisible||now-lastFrame<32)return;\n    lastFrame=now;')
    code = code.replace('    renderer.render(scene, camera);', '    renderer.render(scene, camera);renderedFrames++;')
    code = code.replace('        animateModel();', "        if(!matchMedia('(prefers-reduced-motion: reduce)').matches)animateModel();")
    failure = "window.__studioProceduralState='failed';const loader=document.getElementById(CONFIG.loader);if(loader)loader.classList.add('hidden');document.querySelectorAll('[data-cs-action],#cta-button').forEach(button=>button.disabled=true);const warning=document.createElement('p');warning.className='cs-concept';warning.textContent='WebGL indisponível neste navegador. O conteúdo e os formulários 2D continuam disponíveis.';host.prepend(warning);"
    code = code.replace('        init();\n    } else', '        try{init();}catch(error){' + failure + '}\n    } else')
    flight = next(animation['code'] for animation in get_model('airplane').animations if animation['name'] == 'fly')
    code += '\nlet stopProvidedFlight=null;\nfunction startProvidedFlight(){const airplaneGroup=modelGroup.children[0];\n' + flight + '\nstopProvidedFlight=()=>cancelAnimationFrame(animateFly.animationId);}\n'
    code += '''\nfunction installControls(){
 const host=document.getElementById(CONFIG.canvasContainer);
 if(!document.querySelector('[data-cs-action]')){
  const bar=document.createElement('div');bar.className='cs-controls';
  const actions=[['rotate','Rotacionar'],['zoom-in','Aproximar'],['zoom-out','Afastar'],['reset','Resetar'],['explode','Explodir'],['transparent','Transparência']];
  if(CONFIG.modelName==='earbuds_3d')actions.push(['open','Abrir estojo'],['close','Fechar estojo']);
  if(CONFIG.modelName==='airplane_3d')actions.push(['takeoff','Decolar'],['landing','Pousar'],['fly','Voar']);
  actions.forEach(([action,title])=>{const button=document.createElement('button');button.type='button';button.dataset.csAction=action;button.textContent=title;bar.append(button);});host.after(bar);
 }
 document.querySelectorAll('[data-cs-action]').forEach(button=>button.addEventListener('click',event=>{
  event.stopPropagation();
  if(!modelLoaded)return;const action=button.dataset.csAction;
  if(['reset','takeoff','landing','fly'].includes(action)&&stopProvidedFlight){stopProvidedFlight();stopProvidedFlight=null;}
  if(action==='rotate'){camera.position.applyAxisAngle(new THREE.Vector3(0,1,0),.25);orbitControls.update();}
  if(action==='zoom-in'||action==='zoom-out'){camera.position.sub(orbitControls.target).multiplyScalar(action==='zoom-in'?.85:1.15).add(orbitControls.target);orbitControls.update();}
  if(action==='open')openCase();if(action==='close')closeCase();
  if(action==='explode'){explodeModel();if(CONFIG.modelName==='airplane_3d')modelGroup.children[0].children.forEach((o,i)=>gsap.to(o.position,{x:o.userData.csPosition.x+(i%2?2:-2),y:o.userData.csPosition.y+(i%3),duration:1}));}if(action==='transparent')toggleTransparent();
  if(action==='reset'){modelGroup.traverse(o=>{gsap.killTweensOf(o.position);gsap.killTweensOf(o.rotation);if(o.userData.csPosition)o.position.copy(o.userData.csPosition);if(o.userData.csRotation)o.rotation.copy(o.userData.csRotation);if(o.isMesh){o.material.transparent=false;o.material.opacity=1;}});modelGroup.position.set(0,0,0);modelGroup.rotation.set(0,0,0);centerCamera();}
  if(action==='takeoff'){gsap.to(modelGroup.children[0].position,{y:5,z:-10,duration:3,ease:'power2.out'});gsap.to(modelGroup.children[0].rotation,{x:-.2,duration:3});}
  if(action==='landing'){gsap.to(modelGroup.children[0].position,{y:0,z:0,duration:3,ease:'power2.in'});gsap.to(modelGroup.children[0].rotation,{x:0,duration:3});}
  if(action==='fly')startProvidedFlight();
 }));
 const resizeObserver=new ResizeObserver(()=>{if(renderer)onWindowResize();});resizeObserver.observe(host);
 const visibilityObserver=new IntersectionObserver(entries=>{canvasVisible=entries.some(entry=>entry.isIntersecting);});visibilityObserver.observe(host);
 renderer.domElement.tabIndex=0;renderer.domElement.setAttribute('aria-label','Modelo 3D: arraste para girar, use a roda para ampliar.');
 window.__studioProceduralState='ready';window.__studioProceduralModel=CONFIG.modelName;
 window.__studioProceduralSnapshot=()=>({model:CONFIG.modelName,renderedFrames,visible:canvasVisible,position:modelGroup.children[0].position.toArray(),pieces:modelGroup.children[0].children.map(o=>({position:o.position.toArray(),rotation:o.rotation.toArray().slice(0,3),opacity:o.material?.opacity})),camera:camera.position.toArray(),floors:modelGroup.userData.floors?.length||0,meshes:(()=>{let count=0;modelGroup.traverse(o=>{if(o.isMesh)count++;});return count;})()});
 window.addEventListener('pagehide',()=>{cancelAnimationFrame(frameId);resizeObserver.disconnect();visibilityObserver.disconnect();if(stopProvidedFlight)stopProvidedFlight();orbitControls.dispose();scene.traverse(o=>{if(o.geometry)o.geometry.dispose();if(o.material)o.material.dispose();});renderer.dispose();},{once:true});
}
window.addEventListener('DOMContentLoaded',()=>{if(window.__studioProceduralState==='failed')return;try{installControls();}catch(error){window.__studioProceduralState='failed';const loader=document.getElementById(CONFIG.loader);if(loader)loader.classList.add('hidden');}});
'''
    setup = "const host=document.querySelector('[data-studio-procedural]');if(!host)return;window.__studioProceduralState='loading';host.id='canvas-container';if(!document.getElementById('loader')){const loader=document.createElement('p');loader.id='loader';loader.textContent='Carregando modelo procedural…';host.append(loader);}\n"
    return '(function(){\n' + setup + code + '\n})();'
