"""Local integration fixture; never use real provider keys. Not included in runtime ZIP."""
import sys, json, asyncio, os, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from cronos.app import create_app
from cronos.config import Settings
from cronos.studio.catalog import starter
import uvicorn
root=Path(tempfile.mkdtemp(prefix='cronos-studio-functional-'))
(root/'personality.md').write_text('Seja franco e paciente, com boas explicações.')
settings=Settings(root/'vault',root/'personality.md','studio-test-only','gemini','','gemini-2.5-flash','','','s1','http://127.0.0.1:11434','gemma3:4b',providers_file=root/'providers.json',gemini_transport='rest')
class Builder:
 async def reply(self,system,messages):
  await asyncio.sleep(.3)
  data=json.loads(messages[-1]['content']);files=starter(data['business']['category'],data['business']['name'],[a['name'] for a in data.get('assets',[]) if a['purpose']=='image'])
  if any(a['purpose']=='model' for a in data.get('assets',[])):files['index.html']=files['index.html'].replace('<section id="sobre"','<section class="product-demo"><div data-studio-model></div></section><section id="sobre"')
  files['index.html']=files['index.html'].replace('Uma cozinha de encontros.','Um projeto de teste gerado a partir do briefing.')
  return {'reply':json.dumps({'summary':'Senhor, esta é uma geração de teste. Composição e formulários disponíveis para verificar no navegador. Nenhuma chamada a provedores externos.', 'files':files}),'topics':[]}
app=create_app(settings,Builder())
uvicorn.run(app,host='127.0.0.1',port=int(os.getenv('STUDIO_TEST_PORT','8871')),log_level='warning')
