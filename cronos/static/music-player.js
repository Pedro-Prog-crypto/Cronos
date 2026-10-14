// Fixed official embed. No keys, cookies from Kronos, or arbitrary URLs.
(()=>{
 const id=new URLSearchParams(location.search).get('id');
 if(!/^[A-Za-z0-9_-]{11}$/.test(id||''))return;
 let parentOrigin;
 try{const url=new URL(new URLSearchParams(location.search).get('parentOrigin'));if(!['localhost','127.0.0.1','[::1]'].includes(url.hostname)||url.hostname===location.hostname||url.protocol!==location.protocol||url.port!==location.port)return;parentOrigin=url.origin;}catch{return;}
 let player=null,timer=null,ready=false;
 const send=(type,values={})=>parent.postMessage({type:'cronos:music:'+type,...values},parentOrigin);
 const frame=document.getElementById('player');
 frame.src='https://www.youtube-nocookie.com/embed/'+id+'?'+new URLSearchParams({enablejsapi:'1',autoplay:'1',playsinline:'1',controls:'1',fs:'1',rel:'0',origin:location.origin});
 const timeout=setTimeout(()=>{if(!ready)send('error',{code:0});},15000);
 window.onYouTubeIframeAPIReady=()=>{
  player=new YT.Player(frame,{events:{
   onReady:()=>{ready=true;clearTimeout(timeout);send('ready');player.playVideo();timer=setInterval(()=>send('progress',{elapsed:player.getCurrentTime(),duration:player.getDuration()}),500);},
   onStateChange:event=>send('state',{state:event.data}),
   onAutoplayBlocked:()=>send('blocked'),
   onError:event=>send('error',{code:event.data})
  }});
 };
 window.addEventListener('message',event=>{
  if(event.origin!==parentOrigin||event.source!==parent||event.data?.type!=='cronos:music:command'||!ready)return;
  const {command,value}=event.data;
  if(command==='play')player.playVideo();
  if(command==='pause')player.pauseVideo();
  if(command==='seek'&&Number.isFinite(value)&&value>=0)player.seekTo(value,true);
  if(command==='volume'&&Number.isFinite(value))player.setVolume(Math.max(0,Math.min(100,value)));
 });
 const script=document.createElement('script');script.src='https://www.youtube.com/iframe_api';script.referrerPolicy='strict-origin-when-cross-origin';script.onerror=()=>send('error',{code:0});document.head.append(script);
 window.addEventListener('pagehide',()=>{clearTimeout(timeout);clearInterval(timer);player?.destroy();},{once:true});
})();
