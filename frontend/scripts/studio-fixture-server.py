"""Local integration fixture; never use real provider keys. Not included in runtime ZIP."""
import sys, json, asyncio, os, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from cronos.app import create_app
from cronos.config import Settings
from cronos.studio.catalog import starter
from cronos.providers import ProviderError
import cronos.studio.images as image_search
import cronos.studio.image_generation as image_generation
import uvicorn
root=Path(tempfile.mkdtemp(prefix='cronos-studio-functional-'))
(root/'personality.md').write_text('Seja franco e paciente, com boas explicações.')
settings=Settings(root/'vault',root/'personality.md','studio-test-only','gemini','','gemini-2.5-flash','','','s1','http://127.0.0.1:11434','gemma3:4b',providers_file=root/'providers.json',gemini_transport='rest')
settings.providers_file.write_text(json.dumps({'providers':[{'id':'image-fixture','kind':'openai','model':'fixture-text','base_url':'https://api.openai.com/v1','key_env':'STUDIO_FIXTURE_IMAGE_KEY'}]}))
os.environ['STUDIO_FIXTURE_IMAGE_KEY']='not-a-real-key-fixture-only'
calls={'plans':0,'site':0,'image':0}
async def fake_photo(category,orientation='any',**kwargs):
 return (Path(__file__).resolve().parents[2]/'cronos/studio/media/restaurant-fire.jpg').read_bytes(),'File:Fixture photograph.jpg',{'url':'https://commons.wikimedia.org/wiki/File:Fixture.jpg','author':'Autor de teste','license':'CC0'}
image_search.suggest_image=fake_photo
import base64
import cronos.studio.threed.reference_images as reference_photos
async def fake_reference_photo(url):
 return 'data:image/jpeg;base64,'+base64.b64encode((await fake_photo('restaurante'))[0]).decode()
reference_photos.download=fake_reference_photo
async def fake_image(settings,provider,prompt,orientation,model):
 calls['image']+=1
 await asyncio.sleep(.3)
 from PIL import Image
 import io
 data=io.BytesIO();Image.new('RGB',(1536,1024) if orientation=='horizontal' else (1024,1536),'#265c66').save(data,'JPEG');return data.getvalue()
image_generation.generate_image=fake_image
class Builder:
 async def reply(self,system,messages):
  await asyncio.sleep(.3)
  if 'EXATAMENTE três direções' in system:
   calls['plans']+=1
   directions=[{'name':name,'concept':'Uma identidade específica para o público e os objetivos deste restaurante, com conteúdo que orienta a visita.',
    'composition':composition,'typography':'Georgia editorial e Arial para controles claros.','palette':['#efe9dc','#251d19','#c84829'],
    'sections':['A cozinha','Cardápio','Pedir uma mesa'],'horizontal_image':'Fotografia ampla do prato finalizado com luz lateral e fogo ao fundo.',
    'vertical_image':'Retrato das mãos do cozinheiro finalizando um prato em enquadramento vertical.',
    'interaction':'Filtros do cardápio e navegação de teclado, com comportamento adaptado ao celular.'}
    for name,composition in [('Caderno do fogo','Composição editorial com fotografia vertical e notas de cozinha distribuídas pelas margens.'),('O prato em cena','Abertura com fotografia horizontal imersiva e tipografia sobre a área de menor detalhe.'),('A mesa primeiro','Cardápio em destaque com faixas de conteúdo e fotografias intercaladas sem blocos repetidos.')]]
   return {'reply':json.dumps({'directions':directions})}
  calls['site']+=1
  data=json.loads(messages[-1]['content']);files=starter(data['business']['category'],data['business']['name'],[a['name'] for a in data.get('assets',[]) if a['purpose']=='image'])
  if 'simular falha 429' in data.get('request','').lower() and not calls.get('recover_retry'):raise ProviderError('Integração de teste: limite temporário (HTTP 429).',429)
  files['index.html']=files['index.html'].replace('Conteúdo de demonstração. Substitua por informações confirmadas do seu negócio.','Conteúdo específico deste briefing de teste.').replace('O que faz sentido para você faz parte de cada escolha.','Uma direção preparada para este projeto de teste.')
  if data.get('screen_observations'):
   files=data['current_files'].copy();files['styles.css']+='\nform label{margin-bottom:12px}form input,form button{min-height:48px}'
  if data.get('design_policy',{}).get('unique_creation'):
   variant=sum(ord(c) for c in data['business']['name'])%3
   files['styles.css']+='\nmain{display:grid;grid-template-columns:'+['1fr 2fr','2fr 1fr','1fr'][variant]+';gap:37px}'
  if any(a['purpose']=='model' for a in data.get('assets',[])):files['index.html']=files['index.html'].replace('<section id="sobre"','<section class="product-demo"><div data-studio-model></div></section><section id="sobre"')
  files['index.html']=files['index.html'].replace('Uma cozinha de encontros.','Um projeto de teste gerado a partir do briefing.')
  return {'reply':json.dumps({'summary':'Senhor, esta é uma geração de teste. Composição e formulários disponíveis para verificar no navegador. Nenhuma chamada a provedores externos.', 'files':files}),'topics':[]}
if os.getenv('STUDIO_TEST_SCREEN') == '1':
 class ScreenVision:
  async def reply(self,system,messages):
   calls['screen']=calls.get('screen',0)+1
   calls['screen_has_image']=bool(messages[0].get('image',{}).get('data'))
   return {'reply':json.dumps({'summary':'Os campos do formulário visível estão pequenos e sem espaço entre os rótulos.',
    'issues':[{'title':'Campos muito pequenos','detail':'O formulário visível precisa de campos mais altos e rótulos separados.','severity':'high'}],
    'correction_request':'Amplie os campos e botões do formulário e organize os rótulos em linhas separadas.'})}
vision_fixture=ScreenVision() if os.getenv('STUDIO_TEST_SCREEN') == '1' else None
if os.getenv('STUDIO_TEST_FALLBACK') == '1':
 from dataclasses import replace
 import cronos.studio.service as studio_service
 settings=replace(settings,gemini_key='fixture-not-a-real-key')
 entries=json.loads(settings.providers_file.read_text())
 entries['providers'].insert(0,{'id':'mistral','kind':'openai','model':'fixture-code','base_url':'https://example.com/v1','key_env':'STUDIO_FIXTURE_IMAGE_KEY'})
 settings.providers_file.write_text(json.dumps(entries))
 calls['adapters']={}
 class ReserveBuilder(Builder):
  def __init__(self,identifier):self.identifier=identifier
  async def reply(self,system,messages):
   calls['adapters'][self.identifier]=calls['adapters'].get(self.identifier,0)+1
   if self.identifier=='gemini':raise ProviderError('Fixture quota',429)
   if 'aguardar cancelamento manual' in messages[-1]['content']:
    await asyncio.Event().wait()
   await asyncio.sleep(2)
   return await super().reply(system,messages)
 studio_service.make_provider=lambda config: ReserveBuilder(config.provider)
 app=create_app(settings,vision_provider=vision_fixture)
elif os.getenv('STUDIO_TEST_ENGINEERING') == '1':
 sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tests'))
 from test_studio_engineering import shop_files
 class EngineeringBuilder(Builder):
  async def reply(self,system,messages):
   if 'EXATAMENTE três direções' in system:return await super().reply(system,messages)
   if not messages[-1]['content'].lstrip().startswith('{'):
    calls['chat']=calls.get('chat',0)+1;calls['screen_context']=bool(messages[-1].get('image'))
    return {'reply':'Senhor, a captura atual está disponível para a pergunta solicitada.','topics':[],'tool_calls':[]}
   calls['site']+=1
   import re
   files=shop_files()
   data=json.loads(messages[-1]['content'])
   photos=[a for a in data.get('assets',[]) if a['purpose']=='image']
   if photos:files['index.html']=files['index.html'].replace('</main>','<figure><img src="assets/'+photos[0]['name']+'" alt="Fotografia ilustrativa do teste"><figcaption>Imagem ilustrativa do teste, CC0.</figcaption></figure></main>')
   files['index.html']=re.sub(r'<form\b[^>]*data-studio-form="booking"[\s\S]*?</form>','',files['index.html'])
   await asyncio.sleep(.3)
   return {'reply':json.dumps({'summary':'Senhor, catálogo fictício para verificar as interações internas. Nenhum pagamento real.','files':files})}
 app=create_app(settings,EngineeringBuilder(),vision_provider=vision_fixture)
elif os.getenv('STUDIO_TEST_BACKGROUND') == '1':
 class BackgroundBuilder(Builder):
  pending=''
  async def reply(self,system,messages):
   if 'CONTRATO DESTA ETAPA' in system:
    calls['continuations']=calls.get('continuations',0)+1
    data=json.loads(messages[0]['content']);prefix=data['received_prefix']
    assert self.pending.startswith(prefix)
    await asyncio.sleep(4)
    return {'reply':json.dumps({'continuation':self.pending[len(prefix):]})}
   result=await super().reply(system,messages)
   if 'files' in json.loads(result['reply']):
    self.pending=result['reply'];await asyncio.sleep(4)
    raise ProviderError('Fixture output limit',502,kind='output_limit',partial_output=self.pending[:len(self.pending)//2])
   return result
 app=create_app(settings,BackgroundBuilder(),vision_provider=vision_fixture)
else:
 app=create_app(settings,Builder(),vision_provider=vision_fixture)
if os.getenv('STUDIO_TEST_LIVE_SCREEN') == '1':
 from contextlib import asynccontextmanager
 previous_lifespan=app.router.lifespan_context
 @asynccontextmanager
 async def screen_lifespan(application):
  async with previous_lifespan(application):
   def fake_screen():
    from PIL import Image
    import io
    calls['screen_captures']=calls.get('screen_captures',0)+1
    output=io.BytesIO();Image.new('RGB',(800,450),(15,calls['screen_captures']%255,70)).save(output,'PNG');return output.getvalue()
   application.state.live_screen.capture=fake_screen
   yield
 app.router.lifespan_context=screen_lifespan
 @app.post('/fixture/reset-live-screen')
 async def reset_live_screen():
  await app.state.live_screen.close()
  calls['screen_context']=False
  return {'active':False}
if os.getenv('STUDIO_TEST_SCREEN') == '1':
 @app.post('/fixture/recover-retry')
 async def fixture_recover():
  calls['recover_retry']=True
  return {'recovered':True}
if os.getenv('STUDIO_TEST_OPPORTUNITIES') == '1':
 from uuid import uuid4
 from cronos.prospects import recommendation
 async def fixture_search(args):
  leads=[]
  for index,name in enumerate(('Mesa da Praça','Cozinha do Lago')):
   lead={'id':'osm:node:fixture-'+str(index),'name':name,'city':'Brasília, DF','category':'restaurante','address':'Endereço público de teste','phone':None,'website':None,'rating':None,'rating_count':None,'seats':None,'site_status':'unverified','evidence':[{'source':'Fixture de teste — não é estabelecimento captado','url':'https://www.openstreetmap.org','note':'Fonte simulada para verificar a interface.'}]}
   leads.append(recommendation(lead))
  report={'id':str(uuid4()),'city':'Brasília, DF','category':args.category,'source':'osm','leads':leads,'attribution':'Fixture de teste. Nenhum cliente real.','coverage':'Somente dois registros de teste.'}
  app.state.prospects.reports[report['id']]=report
  return report
 app.state.prospects.search=fixture_search
@app.get('/fixture/calls')
async def fixture_calls():return calls
@app.post('/fixture/reset-cooldowns')
async def fixture_reset_cooldowns():
 app.state.studio.provider_cooldowns.clear()
 app.state.studio.vision_cooldowns.clear()
 return {'reset':True}
uvicorn.run(app,host='127.0.0.1',port=int(os.getenv('STUDIO_TEST_PORT','8871')),log_level='warning')
