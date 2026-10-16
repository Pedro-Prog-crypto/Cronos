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
async def fake_photo(category,orientation='any'):
 return (Path(__file__).resolve().parents[2]/'cronos/studio/media/restaurant-fire.jpg').read_bytes(),'File:Fixture photograph.jpg',{'url':'https://commons.wikimedia.org/wiki/File:Fixture.jpg','author':'Autor de teste','license':'CC0'}
image_search.suggest_image=fake_photo
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
  if 'simular falha 429' in data.get('request','').lower():raise ProviderError('Integração de teste: limite temporário (HTTP 429).',429)
  files['index.html']=files['index.html'].replace('Conteúdo de demonstração. Substitua por informações confirmadas do seu negócio.','Conteúdo específico deste briefing de teste.').replace('O que faz sentido para você faz parte de cada escolha.','Uma direção preparada para este projeto de teste.')
  if any(a['purpose']=='model' for a in data.get('assets',[])):files['index.html']=files['index.html'].replace('<section id="sobre"','<section class="product-demo"><div data-studio-model></div></section><section id="sobre"')
  files['index.html']=files['index.html'].replace('Uma cozinha de encontros.','Um projeto de teste gerado a partir do briefing.')
  return {'reply':json.dumps({'summary':'Senhor, esta é uma geração de teste. Composição e formulários disponíveis para verificar no navegador. Nenhuma chamada a provedores externos.', 'files':files}),'topics':[]}
app=create_app(settings,Builder())
@app.get('/fixture/calls')
async def fixture_calls():return calls
uvicorn.run(app,host='127.0.0.1',port=int(os.getenv('STUDIO_TEST_PORT','8871')),log_level='warning')
