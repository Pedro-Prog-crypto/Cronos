"""Real audio playback must survive opening/dragging analysis and free card movement."""
import asyncio,http.server,threading,json,io,wave,math,struct
from pathlib import Path
from functools import partial
from playwright.async_api import async_playwright,expect
ROOT=Path(__file__).resolve().parents[2]
def audio(seconds):
 data=io.BytesIO()
 with wave.open(data,'wb') as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(b''.join(struct.pack('<h',int(1000*math.sin(i*.12))) for i in range(int(seconds*8000))))
 return data.getvalue()
WAV=audio(3)
REPLY='\n\n'.join(f'## Tema {i+1}\nExemplo {i+1}.' for i in range(6))
ANALYSIS='A análise terminou sem interromper a explicação.'
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'cronos')))
threading.Thread(target=server.serve_forever,daemon=True).start()
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
  page=await browser.new_page(viewport={'width':1600,'height':900})
  await page.add_init_script("window.pywebview={api:{connection:async()=>({token:'test'})}};window.players=[];const play=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){if(!window.players.includes(this))window.players.push(this);return play.call(this)}")
  await page.route('**/status',lambda r:r.fulfill(json={'fish_configured':True,'fish_speech_configured':True}))
  await page.route('**/panels',lambda r:r.fulfill(json={'preferences':{'device_auto_connect':False}}))
  await page.route('**/monitor?*',lambda r:r.fulfill(json={'cursor':0,'alerts':[],'events':[]}))
  await page.route('**/memory/**',lambda r:r.fulfill(json={'nodes':[],'edges':[],'total':0,'next_offset':None}))
  await page.route('**/panels/latency',lambda r:r.fulfill(json={'recorded':True}))
  chats=[];speech=[];current_reply=REPLY
  async def chat(r):
   chats.append(json.loads(r.request.post_data));await r.fulfill(body='\n'.join(json.dumps(e) for e in [{'type':'reply','reply':current_reply},{'type':'result','result':{'reply':current_reply,'session_id':'test','tool_results':[]}}])+'\n',content_type='application/x-ndjson')
  await page.route('**/chat/stream',chat)
  async def speak(r):
   text=json.loads(r.request.post_data)['text'];speech.append(text)
   if text.startswith('A análise'):assert await page.evaluate('players.slice(0,2).every(p=>p.ended||p.src==="")'), 'analysis voice must wait for the explanation'
   await r.fulfill(body=WAV,content_type='audio/wav')
  await page.route('**/voice/speech',speak)
  image=ROOT/'frontend/src/assets/images/news_ai_safety_1791817511005.jpg'
  await page.route('**/vision/preview',lambda r:r.fulfill(body=image.read_bytes(),content_type='image/jpeg'))
  analysis_release=asyncio.Event()
  async def analysis(r):
   await analysis_release.wait();await r.fulfill(json={'reply':ANALYSIS+'\n'+'Detalhe da imagem. '*200})
  await page.route('**/vision/analyze',analysis)
  await page.route('**/documents/preview',lambda r:r.fulfill(json={'files':[{'name':'main.py','truncated':False}],'skipped':[],'truncated':False}))
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto(f'http://127.0.0.1:{server.server_port}/ui/index.html')
  async def ask(text):
   await page.get_by_role('button',name='ENTENDIMENTO DE LINGUAGEM',exact=True).click();await page.locator('.phrase-card').click()
   await page.locator('#chat-input').fill(text);await page.get_by_role('button',name='Enviar mensagem').click()
  await ask('Explique em seis cards')
  await expect(page.locator('.floating-answer-card')).to_have_count(6)
  await page.wait_for_function('players.length>0&&!players[0].paused')
  boxes=await page.locator('.floating-answer-card').evaluate_all('nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}})')
  assert len([r for r in boxes if r['x']+r['w']/2<800])==3 and len([r for r in boxes if r['x']+r['w']/2>800])==3
  await page.get_by_role('button',name='Analisar imagem',exact=True).click()
  assert await page.evaluate('!players[0].paused&&players[0].currentTime>0'), 'opening analysis must not stop speech'
  await expect(page.locator('.floating-answer-card')).to_have_count(6)
  await page.get_by_label('Selecionar imagem',exact=True).set_input_files(str(image))
  await page.get_by_role('button',name='Analisar',exact=True).click()
  panel=page.get_by_role('region',name='Análise de imagem',exact=True)
  initial=await panel.bounding_box();header=panel.locator('header');h=await header.bounding_box()
  await page.mouse.move(h['x']+70,h['y']+12);await page.mouse.down();await page.mouse.move(500,180,steps=10);await page.mouse.up()
  moved=await panel.bounding_box();assert abs(moved['x']-initial['x'])>100
  analysis_release.set();await expect(page.locator('.analysis-result')).to_be_visible()
  after_result=await panel.bounding_box();assert abs(after_result['y']-moved['y'])<2, 'incoming analysis must not move a dragged panel'
  assert not any(t.startswith('A análise') for t in speech),'analysis must queue, not replace ongoing speech'
  assert await page.evaluate('players[0].src!==""'), 'dragging must not clear the current voice source'
  assert await panel.evaluate('n=>getComputedStyle(n).scrollbarWidth')=='none'
  assert await panel.locator('textarea').evaluate('n=>getComputedStyle(n).resize')=='none'
  # Drag the content itself to read more, with no visible scrollbar.
  text=panel.locator('.analysis-result');b=await text.bounding_box();pr=await panel.bounding_box()
  start_y=min(pr['y']+pr['height']-25,b['y']+30)
  await page.mouse.move(pr['x']+80,start_y);await page.mouse.down();await page.mouse.move(pr['x']+80,start_y-130,steps=8);await page.mouse.up()
  assert await panel.evaluate('n=>n.scrollTop')>0
  # A ZIP can open without destroying the selected image or its result.
  await page.get_by_role('button',name='Analisar ZIP ou código',exact=True).click()
  await expect(page.locator('.analysis-panel')).to_have_count(2)
  await expect(panel.locator('img')).to_be_visible()
  await page.get_by_role('region',name='Análise de arquivo',exact=True).get_by_role('button',name='Fechar análise').click()
  await panel.get_by_role('button',name='Fechar análise').click()
  card=page.locator('.floating-answer-card').first;old=await card.bounding_box();heading=await card.locator('h2').bounding_box()
  await page.mouse.move(heading['x']+55,heading['y']+8);await page.mouse.down();await page.mouse.move(50,710,steps=10);await page.mouse.up()
  new=await card.bounding_box();assert abs(new['y']-old['y'])>250 and new['x']>=0
  await expect(page.locator('.floating-answer-card')).to_have_count(6)
  await page.screenshot(path='/tmp/cronos-movable-cards-real.png')
  await page.wait_for_function('(prefix)=>window.players.length>=3',arg='A análise',timeout=15000)
  assert any(t.startswith('A análise') for t in speech)
  # Positioning the active explanation is local and leaves its six cards intact.
  await ask('Cronos, coloque os cards na direita');assert len(chats)==1
  await expect(page.locator('.floating-answer-card')).to_have_count(6)
  right=await page.locator('.floating-answer-card').evaluate_all('nodes=>nodes.map(n=>n.getBoundingClientRect().x)')
  assert all(x>=800 for x in right),right
  await page.keyboard.press('Escape');await page.wait_for_timeout(150)
  # Overflowing card text scrolls by dragging; handles also support keyboard movement.
  current_reply='\n\n'.join(f'## Longo {i+1}\n'+('Detalhe legível para estudar. '*90) for i in range(6))
  await ask('Explique novamente em cards')
  await expect(page.get_by_role('heading',name='Longo 1',exact=True)).to_be_visible()
  await page.keyboard.press('Escape');await ask('Cronos, abrir texto na tela')
  card=page.locator('.floating-answer-card').first;text=card.locator('.holo-text')
  assert await text.evaluate('n=>n.scrollHeight>n.clientHeight&&getComputedStyle(n).scrollbarWidth==="none"')
  box=await text.bounding_box()
  await page.mouse.move(box['x']+30,box['y']+box['height']-10);await page.mouse.down();await page.mouse.move(box['x']+30,box['y']+10,steps=8);await page.mouse.up()
  assert await text.evaluate('n=>n.scrollTop')>0
  heading=card.locator('h2');await heading.focus();before=await card.bounding_box();await page.keyboard.press('ArrowRight');after=await card.bounding_box();assert after['x']>=before['x']+9
  await page.set_viewport_size({'width':1200,'height':700});await page.wait_for_timeout(150)
  resized=await card.bounding_box();assert resized['x']>=0 and resized['x']+resized['width']<=1201 and resized['y']+resized['height']<=701
  question=page.locator('.spoken-question');q=await question.bounding_box();handle=await question.locator('h2').bounding_box()
  await page.mouse.move(handle['x']+20,handle['y']+5);await page.mouse.down();await page.mouse.move(120,610,steps=8);await page.mouse.up()
  moved_question=await question.bounding_box();assert abs(moved_question['x']-q['x'])>100
  assert not errors,errors
  print('PASS: real speech survives opening and dragging analysis; analysis speech queues; two analysis panels preserve image; six cards orbit, move freely and reposition by local command; hidden scrollbars and mouse-drag scrolling.')
  await browser.close()
try:asyncio.run(main())
finally:server.shutdown()
