"""Exercise real HTTP adapters with provider-shaped responses, not envelope fixtures."""
import asyncio
import json
from dataclasses import replace
import httpx
import pytest
from cronos.providers import Gemini,ProviderError,parse_structured_reply
from cronos.integrations import CompatibleProvider,ProviderSpec
from cronos.studio.validation import parse_bundle,validate
from cronos.studio.designs import site
from test_backend import settings

CLIENT=httpx.AsyncClient


def compatible(monkeypatch,handler,**kwargs):
 monkeypatch.setattr('cronos.integrations.httpx.AsyncClient',lambda **kw:CLIENT(transport=httpx.MockTransport(handler),trust_env=False,**kw))
 return CompatibleProvider(ProviderSpec(id='mistral',kind='openai',model='fixture',base_url='https://example.com/v1',**kwargs))


def test_direct_and_old_envelopes_have_the_same_complete_files():
 bundle={'summary':'Site de estudo.','files':site('restaurante','Casa teste')}
 for raw in [json.dumps(bundle),json.dumps({'reply':bundle}),json.dumps({'reply':json.dumps(bundle),'topics':[]}), '```json\n'+json.dumps(bundle)+'\n```']:
  files,summary=parse_bundle(parse_structured_reply(raw))
  assert validate(files)['passed'] and summary==bundle['summary']
 with pytest.raises(ProviderError):parse_structured_reply(json.dumps({**bundle,'tool_calls':[{'name':'exec','arguments':{}}]}))


def test_http_json_mode_is_negotiated_only_on_an_explicit_parameter_rejection(monkeypatch):
 seen=[]
 def handle(r):
  p=json.loads(r.content);seen.append(p)
  if 'response_format' in p:return httpx.Response(400,json={'error':{'message':'response_format json_object is not supported'}})
  return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'summary':'ok','files':site('hotel','Hotel teste')})}}]})
 provider=compatible(monkeypatch,handle,max_output_tokens=2048)
 result=asyncio.run(provider.reply_structured('Crie o objeto JSON do site.',[{'role':'user','content':'Briefing'}]))
 assert parse_bundle(result)[0]['index.html']
 assert len(seen)==2 and seen[0]['max_tokens']==seen[1]['max_tokens']==2048
 assert 'response_format' not in seen[1]
 assert '"topics"' not in seen[0]['messages'][0]['content']


def test_new_token_parameter_does_not_disable_json_mode(monkeypatch):
 seen=[]
 def handle(r):
  p=json.loads(r.content);seen.append(p)
  if 'max_tokens' in p:return httpx.Response(400,json={'error':{'message':'Unsupported parameter max_tokens; use max_completion_tokens'}})
  return httpx.Response(200,json={'choices':[{'message':{'content':'{"directions":[]}'},'finish_reason':'stop'}]})
 provider=compatible(monkeypatch,handle,max_output_tokens=4096)
 asyncio.run(provider.reply_structured('Planos',[]))
 assert len(seen)==2 and seen[1]['max_completion_tokens']==4096 and seen[1]['response_format']


@pytest.mark.parametrize('status',[400,401,403,404,422,429,503])
def test_http_errors_keep_the_real_status_and_never_echo_sensitive_server_text(monkeypatch,status):
 seen=[]
 def handle(r):
  seen.append(r);return httpx.Response(status,json={'error':{'message':'PRIVATE secret response'}})
 provider=compatible(monkeypatch,handle)
 with pytest.raises(ProviderError) as error:asyncio.run(provider.reply_structured('Site',[]))
 assert error.value.http_status==status and 'PRIVATE' not in str(error.value) and len(seen)==1


def test_finished_but_truncated_code_is_classified_as_output_limit(monkeypatch):
 provider=compatible(monkeypatch,lambda r:httpx.Response(200,json={'choices':[{'finish_reason':'length','message':{'content':'{"files":'}}]}))
 with pytest.raises(ProviderError) as error:asyncio.run(provider.reply_structured('Site',[]))
 assert error.value.kind=='output_limit'


def test_gemini_studio_uses_direct_json_without_conversation_or_thinking_budget(settings,monkeypatch):
 seen=[]
 def handle(r):
  seen.append(json.loads(r.content));return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{"directions":[]}'}]}}]})
 monkeypatch.setattr('cronos.providers.httpx.AsyncClient',lambda **kw:CLIENT(transport=httpx.MockTransport(handle),trust_env=False,**kw))
 provider=Gemini(replace(settings,gemini_key='fixture',gemini_model='gemini-2.5-flash'))
 result=asyncio.run(provider.reply_structured('Propostas',[]))
 assert json.loads(result['reply'])=={'directions':[]}
 assert '"topics"' not in seen[0]['systemInstruction']['parts'][0]['text']
 assert seen[0]['generationConfig']['thinkingConfig']['thinkingBudget']==0


def test_inline_packaging_is_lifted_and_still_checked_for_unsafe_code():
 original=site('hotel','Hotel teste');files=original.copy()
 files['index.html']=files['index.html'].replace('<link rel="stylesheet" href="styles.css">','<style>'+files['styles.css']+'</style>').replace('<script src="app.js" defer></script>','<script>'+files['app.js']+'</script>')
 files['styles.css']='';files['app.js']=''
 normalized,_=parse_bundle({'reply':json.dumps({'summary':'Site.','files':files})})
 assert validate(normalized)['passed'] and '<style>' not in normalized['index.html']
 files['index.html']=files['index.html'].replace('</body>','<script>fetch("https://example.com")</script></body>')
 bad,_=parse_bundle({'reply':json.dumps({'summary':'Site.','files':files})})
 assert not validate(bad)['passed']
