"""Compare actual page structure, not photographs, brand names or colour changes."""
import hashlib
from html.parser import HTMLParser
import json
import re
from difflib import SequenceMatcher

LAYOUT_PROPERTIES = {'display','position','grid-template-columns','grid-template-rows','grid-template-areas','grid-auto-flow','flex-direction','flex-wrap','order','justify-content','align-items','align-self','width','max-width','min-width','height','min-height','max-height','gap','column-gap','row-gap','padding','padding-top','padding-bottom','padding-inline','margin','margin-top','margin-bottom','inset','top','left','right','bottom','float','columns','overflow','overflow-x','overflow-y','aspect-ratio'}


class Structure(HTMLParser):
    def __init__(self):
        super().__init__();self.tokens=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in {'head','svg','script','style'}:self.skip+=1
        if self.skip:return
        values=dict(attrs)
        kind=values.get('data-studio-form','')
        self.tokens.append(tag+(':'+kind if kind else ''))
    def handle_endtag(self,tag):
        if self.skip:
            if tag in {'head','svg','script','style'}:self.skip-=1
            return
        if tag not in {'img','input','br','hr','meta','link','source'}:self.tokens.append('/'+tag)
    def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs)


def profile(files):
    doc=Structure();doc.feed(files['index.html'])
    blocks=[]
    css=re.sub(r'/\*.*?\*/','',files['styles.css'],flags=re.S)
    for block in re.findall(r'\{([^{}]*)\}',css):
        pairs=[]
        for prop,value in re.findall(r'([\w-]+)\s*:\s*([^;{}]+)',block):
            if prop.lower() in LAYOUT_PROPERTIES and not prop.lower().startswith(('margin','padding')) and prop.lower() not in {'gap','column-gap','row-gap'}:
                pairs.append(prop.lower()+':'+re.sub(r'\s+',' ',value.strip().lower()))
        if pairs:blocks.append(';'.join(sorted(pairs)))
    structure=' '.join(doc.tokens)
    layout='|'.join(blocks)
    return {'structure':structure[:18000],'layout':layout[:18000],
            'signature':hashlib.sha256(json.dumps([structure,layout]).encode()).hexdigest()}


def recent_projects(store, project_id):
    recent=[]
    for saved in store.list():
        if saved['id']==project_id:continue
        current=store.revision(saved)
        direction=next((d for d in saved.get('directions',[]) if d.get('id')==saved.get('direction_id')),None)
        built=current['report'].get('origin') in {'generated','manual','edited'}
        if not built and not direction:continue
        assets=store.get(saved['id']).get('assets',[])
        recent.append({'category':saved['category'],'profile':profile(current['files']) if built else None,
                       'image_titles':[(a.get('source') or {}).get('title','') for a in assets if a.get('purpose')=='image'],
                       'direction':{k:direction[k] for k in ('composition','typography','palette','sections','interaction')} if direction else None})
        if len(recent)>=12:break
    return recent


def plan_context(recent):
    # Other clients' names, contact details and source code never enter the prompt.
    return [{'category':r['category'],**(r['direction'] or {'composition':'Projeto anterior sem direção registrada; evite a estrutura visual repetitiva.'})} for r in recent]


def choose_plan(plans,recent):
    def similarity(plan,other):
        composition=SequenceMatcher(None,plan['composition'].casefold(),other.get('composition','').casefold()).ratio()
        sections=SequenceMatcher(None,plan['sections'],other.get('sections',[])).ratio()
        palette=len(set(c.lower() for c in plan['palette']) & set(c.lower() for c in other.get('palette',[])))/max(1,len(plan['palette']))
        return .65*composition+.25*sections+.1*palette
    scores=[max((similarity(p,r['direction']) for r in recent if r['direction']),default=0) for p in plans]
    index=min(range(len(plans)),key=lambda i:scores[i])
    return plans[index],{'compared_projects':len(recent),'reason':'Composição com menor semelhança textual às direções recentes; a aparência final será verificada na prévia.', 'similarity':round(scores[index],3)}


def review(files,recent,*,enabled):
    if not enabled:return [{'name':'Comparação de composição','status':'unavailable','detail':'Não aplicada a uma revisão ou referência escolhida pelo senhor.'}]
    candidate=profile(files)
    duplicate=any(r['profile'] and candidate['signature']==r['profile']['signature'] for r in recent)
    return [{'name':'Composição diferente dos projetos recentes','status':'failed' if duplicate else 'passed',
             'detail':('A estrutura e a disposição em CSS repetem outro projeto. Trocar textos, imagens, fontes ou cores não atende: reorganize a página.' if duplicate else f'Comparadas estrutura HTML e regras de disposição com {sum(bool(r["profile"]) for r in recent)} projetos recentes. Não certifica originalidade artística nem beleza.')}]
