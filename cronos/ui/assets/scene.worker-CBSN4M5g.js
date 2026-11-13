function e(e,t){let n=Math.min(1,Math.max(0,(Math.min(1,Math.max(0,Number.isFinite(t)?t:0))-.055)/.5)),r=n*n*(3-2*n);return e===`SPEAKING`?{rate:.62+1.05*r,energy:.18+.57*r,expansion:.01+.05*r}:e===`LISTENING`?{rate:.25+.91*r,energy:.035+.45*r,expansion:.001+.03*r}:{rate:.22,energy:.018,expansion:0}}function t(e){return e.getContext(`2d`)}function n(t,n,i,a,o){let s=Math.min(900,Math.round(n*Math.min(a,900/n)));t.width=t.height=s;let c=t.getContext(`webgl`,{alpha:!0,antialias:!0,premultipliedAlpha:!1});if(!c)return r(t,n,i,a,o);let l=(e,t)=>{let n=c.createShader(e);if(!n)throw Error(`Hologram shader unavailable`);if(c.shaderSource(n,t),c.compileShader(n),!c.getShaderParameter(n,c.COMPILE_STATUS))throw Error(c.getShaderInfoLog(n)||`Hologram shader failed`);return n},u=c.createProgram();if(!u)throw Error(`Hologram program unavailable`);if(c.attachShader(u,l(c.VERTEX_SHADER,`attribute vec2 position;varying vec2 uv;void main(){uv=(position+1.0)*0.5;gl_Position=vec4(position,0.0,1.0);}`)),c.attachShader(u,l(c.FRAGMENT_SHADER,`precision highp float;
 varying vec2 uv;uniform float phase;uniform float energy;uniform float expansion;
 uniform sampler2D motionField;uniform float sourceBlend;uniform float videoTime;
 vec3 readField(float index,float azimuth,float radial){
   float column=mod(index,8.0),row=floor(index/8.0);
   vec2 at=vec2((column*256.0+azimuth*255.0+.5)/2048.0,
                (row*64.0+radial*63.0+.5)/896.0);
   return texture2D(motionField,at).rgb;
 }
 void main(){
   vec2 p=uv-vec2(.5);float angle=atan(p.y,p.x);float radius=length(p)/(1.0+expansion);
   // The silhouette undulates continuously. Three separate paths cross it at
   // different speeds; no bitmap or complete-ring rotation is involved.
   float contour=(.013+energy*.008)*sin(2.0*angle+phase*.91)
     +(.010+energy*.006)*sin(3.0*angle-phase*.64+.4)
     +.007*sin(5.0*angle+phase*.59+1.2)
     +.003*sin(7.0*angle-phase*.37+.8);
   float middle=.31+contour;
   float filament=0.0;float halo=0.0;float sparks=0.0;
   for(int strand=0;strand<3;strand++){
     float layer=float(strand);
     float path=middle+(layer-1.0)*.007
       +(.013+energy*.007)*sin(2.0*angle+phase*(.76+layer*.14)+layer*1.7)
       +(.009+energy*.004)*sin(3.0*angle-phase*(.57+layer*.11)+layer*2.1)
       +.005*sin(5.0*angle+phase*(.52+layer*.07)+layer)
       +.0035*sin(9.0*angle-phase*(.61+layer*.08)+layer*2.6)
       +.002*sin(13.0*angle+phase*(.42+layer*.04)+layer*1.3);
     float width=.0013+energy*.0005;
     float distanceToPath=abs(radius-path);
     float highlight=pow(max(0.0,cos(angle-phase*(.65+layer*.11)-layer*2.1)),36.0);
     float flux=.56+.16*sin(5.0*angle+phase*.91+layer*1.4)
       +.08*sin(13.0*angle-phase*.72+layer*2.3)+1.15*highlight;
     filament+=(1.0-smoothstep(width*.45,width*1.7,distanceToPath))*flux;
     halo+=(1.0-smoothstep(width*1.4,width*18.0,distanceToPath))*flux;
     sparks+=pow(max(0.0,cos(angle-phase*(.65+layer*.11)-layer*2.1)),180.0)
       *(1.0-smoothstep(.002,.016,distanceToPath));
   }
   float distanceToBand=abs(radius-middle);
   float body=(1.0-smoothstep(.012,.050,distanceToBand))
     *(.24+.07*sin(2.0*angle+phase*.58)+energy*.10);
   vec3 light=vec3(.016,.42,.98)*body
     +vec3(.018,.42,.96)*halo*.60
     +vec3(.13,.82,1.0)*filament*.95
     +vec3(.46,.91,1.0)*sparks*.85;
   float alpha=clamp(body*.8+halo*.31+filament*.63+sparks*.30,0.0,.94);
   float azimuth=fract((angle+3.14159265)/6.2831853);
   float radial=(63.0+(radius-.31)*210.0-35.0)/60.0;
   float sourceFrame=mod(videoTime*30.0,90.0)+15.0;
   float frameA=floor(sourceFrame),fraction=fract(sourceFrame);
   float frameB=mod(frameA+1.0,105.0);
   vec3 sampledField=mix(readField(frameA,azimuth,radial),
     readField(frameB,azimuth,radial),fraction);
   // The last half second folds into the first half second without a hard cut.
   float closure=smoothstep(90.0,105.0,sourceFrame);
   float startIndex=sourceFrame-90.0;
   float startA=floor(startIndex),startB=startA+1.0;
   vec3 fromStart=mix(readField(startA,azimuth,radial),
     readField(startB,azimuth,radial),fract(startIndex));
   sampledField=mix(sampledField,fromStart,closure);
   float sampled=sampledField.r;
   sampled*=step(0.0,radial)*(1.0-step(1.0,radial));
   float distanceToRails=min(abs(radial-sampledField.g),abs(radial-sampledField.b));
   float isolate=1.0-smoothstep(.045,.105,distanceToRails);
   float emission=pow(sampled,1.05)*isolate;
   float neighborInner=readField(frameA,azimuth,clamp(radial-.025,0.0,1.0)).r;
   float neighborOuter=readField(frameA,azimuth,clamp(radial+.025,0.0,1.0)).r;
   float ridge=clamp((sampled-.5*(neighborInner+neighborOuter))*3.0,0.0,1.0)*isolate;
   float railInner=1.0-smoothstep(.010,.035,abs(radial-sampledField.g));
   float railOuter=1.0-smoothstep(.010,.035,abs(radial-sampledField.b));
   float repair=max(railInner,railOuter)*(.74+.26*(1.0-smoothstep(.18,.55,sampled)));
   repair*=step(0.0,radial)*(1.0-step(1.0,radial));
   vec3 captured=vec3(.025,.40,.92)*emission*(1.05+energy*.18)
     +vec3(.28,.89,1.0)*pow(emission,2.1)*1.08
     +vec3(.27,.86,1.0)*ridge*.31+vec3(.09,.75,1.0)*repair*.92;
   float capturedAlpha=clamp(emission*.90+pow(emission,2.1)*.24+ridge*.11+repair*.88,0.0,.96);
   float particles=0.0;
   for(int particleIndex=0;particleIndex<3;particleIndex++){
     float identity=float(particleIndex);
     float orbit=phase*(.45+identity*.09)+identity*2.15;
     float along=pow(max(0.0,cos(angle-orbit)),520.0);
     float across=1.0-smoothstep(.006,.040,abs(radial-sampledField.g));
     particles+=along*across*(.22+energy*.65);
   }
   captured+=vec3(.18,.76,1.0)*particles*.7;
   capturedAlpha=clamp(capturedAlpha+particles*.30,0.0,.96);
   gl_FragColor=vec4(mix(min(light,1.0),captured,sourceBlend),
     mix(alpha,capturedAlpha,sourceBlend));
 }`)),c.linkProgram(u),!c.getProgramParameter(u,c.LINK_STATUS))throw Error(c.getProgramInfoLog(u)||`Hologram link failed`);c.useProgram(u);let d=c.createBuffer();c.bindBuffer(c.ARRAY_BUFFER,d),c.bufferData(c.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),c.STATIC_DRAW);let f=c.getAttribLocation(u,`position`);c.enableVertexAttribArray(f),c.vertexAttribPointer(f,2,c.FLOAT,!1,0,0);let p=c.getUniformLocation(u,`phase`),m=c.getUniformLocation(u,`energy`),h=c.getUniformLocation(u,`expansion`),g=c.getUniformLocation(u,`sourceBlend`),_=c.getUniformLocation(u,`videoTime`),v=c.createTexture();c.activeTexture(c.TEXTURE0),c.bindTexture(c.TEXTURE_2D,v),c.texParameteri(c.TEXTURE_2D,c.TEXTURE_MIN_FILTER,c.LINEAR),c.texParameteri(c.TEXTURE_2D,c.TEXTURE_MAG_FILTER,c.LINEAR),c.texParameteri(c.TEXTURE_2D,c.TEXTURE_WRAP_S,c.CLAMP_TO_EDGE),c.texParameteri(c.TEXTURE_2D,c.TEXTURE_WRAP_T,c.CLAMP_TO_EDGE),c.uniform1i(c.getUniformLocation(u,`motionField`),0),c.viewport(0,0,s,s);let y=!0,b=!1,x=0,S=0,C=0,w=performance.now(),T=0,E=0,D=.22,O=.018,k=0,A=0;(async()=>{let e=await fetch(`/ui/assets/orb-motion-field-DhbCDBoa.png`);if(!e.ok)throw Error(`Motion field ${e.status}`);let t=await createImageBitmap(await e.blob());try{if(!y)return;c.bindTexture(c.TEXTURE_2D,v),c.pixelStorei(c.UNPACK_FLIP_Y_WEBGL,1),c.texImage2D(c.TEXTURE_2D,0,c.RGB,c.RGB,c.UNSIGNED_BYTE,t),b=!0}finally{t.close()}})().catch(e=>console.warn(`Hologram motion field unavailable.`,e));let j=(e=0)=>{y&&(e?C=self.setTimeout(()=>{y&&(S=requestAnimationFrame(M))},e):S=requestAnimationFrame(M))},M=()=>{if(!y)return;let t=o(),n=performance.now();if(t.hidden){w=n,j(180);return}if(n-w<1e3/(t.fps||60)-1){j();return}let r=Math.min(.05,(n-w)/1e3);w=n;let i=Math.max(0,Math.min(1,t.audio));A+=(i-A)*Math.min(1,r*(i>A?8:2.3));let a=e(t.state,A);D+=(a.rate-D)*Math.min(1,r*3.2),O+=(a.energy-O)*Math.min(1,r*3.6),k+=(a.expansion-k)*Math.min(1,r*3),T+=r*D,E+=r*D,x+=r*(b?2.5:-3),x=Math.min(1,Math.max(0,x)),c.clearColor(0,0,0,0),c.clear(c.COLOR_BUFFER_BIT),c.uniform1f(p,T),c.uniform1f(m,O),c.uniform1f(h,k),c.uniform1f(g,x),c.uniform1f(_,E),c.drawArrays(c.TRIANGLE_STRIP,0,4),j()};return S=requestAnimationFrame(M),()=>{y=!1,self.clearTimeout(C),cancelAnimationFrame(S),c.deleteTexture(v),c.deleteBuffer(d),c.deleteProgram(u)}}function r(n,r,i,a,o){let s=t(n);if(!s)return;let c=Math.min(a,900/r),l=Math.min(900,Math.round(r*c)),u=l/600;n.width=n.height=l,s.setTransform(u,0,0,u,0,0);let d=Math.PI*2,f=Array.from({length:241},(e,t)=>{let n=t*d/240;return{u:n,c:Math.cos(n),s:Math.sin(n)}}),p=Array.from({length:3},()=>/* @__PURE__ */ new Float32Array(482)),m=/* @__PURE__ */ new Float32Array(482),h=!0,g=0,_=0,v=performance.now(),y=0,b=.22,x=.018,S=0,C=0,w=(e=0)=>{h&&(e?_=self.setTimeout(()=>{h&&(g=requestAnimationFrame(D))},e):g=requestAnimationFrame(D))},T=e=>{s.beginPath(),s.moveTo(e[0],e[1]);for(let t=2;t<e.length;t+=2)s.lineTo(e[t],e[t+1]);s.closePath()},E=(e,t,n)=>{let r=Math.round((t%d+d)%d/d*240),i=Math.round(n/d*240);s.beginPath();for(let t=-i;t<=i;t++){let n=(r+t+240)%240;t===-i?s.moveTo(e[n*2],e[n*2+1]):s.lineTo(e[n*2],e[n*2+1])}},D=()=>{if(!h)return;let t=o(),n=performance.now();if(t.hidden){v=n,w(180);return}let r=t.fps||60;if(n-v<1e3/r-1){w();return}let i=Math.min(.05,(n-v)/1e3);v=n;let a=Math.max(0,Math.min(1,t.audio));C+=(a-C)*Math.min(1,i*(a>C?8:2.3));let c=e(t.state,C);b+=(c.rate-b)*Math.min(1,i*3.4),x+=(c.energy-x)*Math.min(1,i*4.2),S+=(c.expansion-S)*Math.min(1,i*3),y+=i*b,s.clearRect(0,0,600,600);for(let e=0;e<=240;e++){let{u:t,c:n,s:r}=f[e],i=(186+((7.8+x*4.8)*Math.sin(2*t+y*.91)+(6+x*3.6)*Math.sin(3*t-y*.64+.4)+4.2*Math.sin(5*t+y*.59+1.2)+1.8*Math.sin(7*t-y*.37+.8)))*(1+S);m[e*2]=300+n*i,m[e*2+1]=300+r*i;for(let a=0;a<3;a++){let o=p[a],s=i+(a-1)*4.2+(7.8+x*4.2)*Math.sin(2*t+y*(.76+a*.14)+a*1.7)+(5.4+x*2.4)*Math.sin(3*t-y*(.57+a*.11)+a*2.1)+3*Math.sin(5*t+y*(.52+a*.07)+a)+2.1*Math.sin(9*t-y*(.61+a*.08)+a*2.6)+1.2*Math.sin(13*t+y*(.42+a*.04)+a*1.3);o[e*2]=300+n*s,o[e*2+1]=300+r*s}}s.save(),s.globalCompositeOperation=`screen`,s.lineJoin=`round`,s.lineCap=`round`,T(m),s.shadowColor=`#008dff`,s.shadowBlur=20,s.strokeStyle=`rgba(0,68,228,.14)`,s.lineWidth=51+x*4,s.stroke(),s.shadowBlur=10,s.strokeStyle=`rgba(0,124,255,.13)`,s.lineWidth=33+x*3,s.stroke();for(let e=0;e<3;e++){let t=p[e];T(t),s.shadowColor=`#0089ff`,s.shadowBlur=10+x*4,s.strokeStyle=e%2?`rgba(0,108,230,.44)`:`rgba(0,161,255,.45)`,s.lineWidth=3.6,s.stroke(),s.shadowBlur=0,s.strokeStyle=e%3==0?`rgba(148,241,255,.83)`:`rgba(28,197,255,.72)`,s.lineWidth=1.35,s.stroke()}for(let e=0;e<3;e++){let t=p[e],n=e*2.38+y*(.55+e*.04)+.25*Math.sin(y*.7+e*.8),r=e%3==0?.94:.58;E(t,n,.38+x*.06),s.shadowColor=`#13d9ff`,s.shadowBlur=15+x*8,s.strokeStyle=`rgba(6,191,255,${r})`,s.lineWidth=4.4,s.stroke(),s.shadowBlur=2,s.strokeStyle=`rgba(211,250,255,${r*.92})`,s.lineWidth=1.6,s.stroke()}s.restore(),w()};return g=requestAnimationFrame(D),()=>{h=!1,self.clearTimeout(_),cancelAnimationFrame(g)}}function i(e,n,r,i,a){let o=t(e);if(!o)return;let s,c=0,l=!0,u=performance.now();function d(e=0){e?c=self.setTimeout(()=>{l&&(s=requestAnimationFrame(g))},e):l&&(s=requestAnimationFrame(g))}let f=Math.min(600,Math.ceil(n*Math.min(i,1.25)))/600;e.width=Math.ceil(600*f),e.height=Math.ceil(600*f),o.setTransform(f,0,0,f,0,0);let p=0,m=[];for(let e=0;e<150;e++){let t=e/150*Math.PI*2,n=.85+e*17%23/23*.75+(e%5==0?.6:0),r=e%4==0?1.8:e%2==0?1.1:.65,i=.38+e*13%19/19*.48,a=1.2+e%7*.3;m.push({angle:t,lengthFactor:n,width:r,alphaBase:i,speed:a})}let h=[];for(let e=0;e<75;e++){let e=Math.random()*Math.PI*2,t=35+Math.random()**1.6*210;h.push({x:300+Math.cos(e)*t,y:300+Math.sin(e)*t,r:.6+Math.random()*1.4,alpha:.35+Math.random()*.65,pulseSpeed:1+Math.random()*3})}function g(){if(!o||!l)return;if(a().hidden||typeof HTMLCanvasElement<`u`&&e instanceof HTMLCanvasElement&&e.getClientRects().length===0){u=performance.now(),d(150);return}let t=performance.now();if(t-u<1e3/(a().fps||30)-1){d();return}let n=Math.min(3,Math.max(.5,(t-u)/(1e3/60)));u=t,o.clearRect(0,0,600,600);let r=a().state,i=a().audio,s=.68+.32*(.5+.5*Math.sin(p*1.8)),c=r===`SPEAKING`?.15+i*.15:0,g=Math.min(1.15,s+c);p+=(r===`SPEAKING`?.024:.014)*n,o.save(),o.save(),o.globalCompositeOperation=`screen`,o.translate(300,300),o.rotate(.55);let _=o.createRadialGradient(30,0,12,35,0,210);_.addColorStop(0,`rgba(190, 240, 255, ${.42*g})`),_.addColorStop(.25,`rgba(110, 210, 255, ${.26*g})`),_.addColorStop(.55,`rgba(35, 120, 200, ${.14*g})`),_.addColorStop(.85,`rgba(10, 45, 130, 0.04)`),_.addColorStop(1,`rgba(0, 0, 0, 0)`),o.beginPath(),o.ellipse(35,0,195,54,0,0,Math.PI*2),o.fillStyle=_,o.fill(),o.restore(),o.save(),o.globalCompositeOperation=`screen`,h.forEach(e=>{let t=.6+.4*Math.sin(p*e.pulseSpeed);o.beginPath(),o.arc(e.x,e.y,e.r,0,Math.PI*2),o.fillStyle=`rgba(225, 248, 255, ${e.alpha*t*g})`,o.shadowColor=`#00f0ff`,o.shadowBlur=0,o.fill()}),o.restore(),o.save(),o.globalCompositeOperation=`screen`;let v=o.createRadialGradient(300,300,2,300,300,48*3.3);v.addColorStop(0,`rgba(255, 255, 255, ${.98*g})`),v.addColorStop(.14,`rgba(210, 248, 255, ${.85*g})`),v.addColorStop(.36,`rgba(56, 189, 248, ${.48*g})`),v.addColorStop(.68,`rgba(2, 100, 230, ${.18*g})`),v.addColorStop(1,`rgba(0, 0, 0, 0)`),o.beginPath(),o.arc(300,300,48*3.3,0,Math.PI*2),o.fillStyle=v,o.fill();let y=48*1.05;m.forEach(e=>{let t=y*(1+e.lengthFactor*.68+Math.sin(p*e.speed+e.angle*4)*.1),n=e.alphaBase*(.75+.25*Math.sin(p*e.speed))*g,r=300+Math.cos(e.angle)*t,i=300+Math.sin(e.angle)*t;o.beginPath(),o.moveTo(300,300),o.lineTo(r,i),o.strokeStyle=`rgba(235, 252, 255, ${Math.min(1,n)})`,o.lineWidth=e.width,o.shadowColor=`#7dd3fc`,o.shadowBlur=0,o.stroke()}),o.beginPath(),o.arc(300,300,y,0,Math.PI*2),o.strokeStyle=`rgba(255, 255, 255, ${.85*g})`,o.lineWidth=2,o.shadowColor=`#38bdf8`,o.shadowBlur=14*g*f,o.stroke(),o.beginPath(),o.arc(300,300,52.900000000000006,0,Math.PI*2),o.strokeStyle=`rgba(125, 211, 252, ${.55*g})`,o.lineWidth=1,o.stroke();let b=o.createLinearGradient(69.60000000000002,300,530.4,300);b.addColorStop(0,`rgba(255, 255, 255, 0)`),b.addColorStop(.35,`rgba(125, 211, 252, ${.48*g})`),b.addColorStop(.5,`rgba(255, 255, 255, ${.98*g})`),b.addColorStop(.65,`rgba(125, 211, 252, ${.48*g})`),b.addColorStop(1,`rgba(255, 255, 255, 0)`),o.beginPath(),o.moveTo(69.60000000000002,300),o.lineTo(300,296.2),o.lineTo(530.4,300),o.lineTo(300,303.8),o.closePath(),o.fillStyle=b,o.fill(),o.beginPath(),o.moveTo(78.81600000000003,300),o.lineTo(521.184,300),o.strokeStyle=`rgba(255, 255, 255, ${g})`,o.lineWidth=2,o.shadowColor=`#00f0ff`,o.shadowBlur=18*g*f,o.stroke();let x=o.createLinearGradient(300,151.2,300,448.8);x.addColorStop(0,`rgba(255, 255, 255, 0)`),x.addColorStop(.35,`rgba(125, 211, 252, ${.42*g})`),x.addColorStop(.5,`rgba(255, 255, 255, ${.95*g})`),x.addColorStop(.65,`rgba(125, 211, 252, ${.42*g})`),x.addColorStop(1,`rgba(255, 255, 255, 0)`),o.beginPath(),o.moveTo(300,151.2),o.lineTo(297.2,300),o.lineTo(448.8,300),o.lineTo(302.8,300),o.closePath(),o.fillStyle=x,o.fill(),o.beginPath(),o.moveTo(300-148.8*.92,300),o.lineTo(436.896,300),o.strokeStyle=`rgba(255, 255, 255, ${g})`,o.lineWidth=1.5,o.shadowColor=`#00f0ff`,o.shadowBlur=15*g*f,o.stroke();let S=86.4,C=[[Math.SQRT1_2,Math.SQRT1_2],[-Math.SQRT1_2,Math.SQRT1_2],[-Math.SQRT1_2,-Math.SQRT1_2],[Math.SQRT1_2,-Math.SQRT1_2]];o.beginPath(),C.forEach(([e,t])=>{o.moveTo(300,300),o.lineTo(300+e*S,300+t*S)}),o.strokeStyle=`rgba(210, 248, 255, ${.68*g})`,o.lineWidth=1.2,o.shadowColor=`#38bdf8`,o.shadowBlur=10*f,o.stroke();let w=o.createRadialGradient(300,300,0,300,300,21);w.addColorStop(0,`rgba(255, 255, 255, ${g})`),w.addColorStop(.38,`rgba(255, 255, 255, ${.98*g})`),w.addColorStop(.72,`rgba(224, 247, 255, ${.88*g})`),w.addColorStop(1,`rgba(56, 189, 248, 0)`),o.beginPath(),o.arc(300,300,21,0,Math.PI*2),o.fillStyle=w,o.shadowColor=`#ffffff`,o.shadowBlur=25*g*f,o.fill(),o.beginPath(),o.moveTo(300,292.5),o.lineTo(307.5,300),o.lineTo(300,307.5),o.lineTo(292.5,300),o.closePath(),o.fillStyle=`rgba(255, 255, 255, ${g})`,o.fill(),o.restore(),o.restore(),d()}return s=requestAnimationFrame(g),()=>{l=!1,self.clearTimeout(c),cancelAnimationFrame(s)}}let a={state:`IDLE`,audio:0,hidden:!1,links:!0},o;self.onmessage=e=>{if(e.data.type===`input`)a=e.data.input;else if(e.data.type===`init`){let{canvas:t,kind:r,size:s,density:c,pixelRatio:l}=e.data;o?.(),o=(r===`orb`?n:i)(t,s,c,l,()=>a),self.postMessage({type:`ready`})}};