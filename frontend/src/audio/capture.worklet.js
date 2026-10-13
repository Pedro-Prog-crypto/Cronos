// Local PCM/VAD with a short pre-roll; no encoder, network, or secrets here.
class CronosCapture extends AudioWorkletProcessor {
  constructor(){super();this.blocked=false;this.chunks=[];this.pre=[];this.active=false;this.silent=0;this.frames=0;this.voiced=0;this.noise=.0005;this.calibration=0;this.minimum=Infinity;this.port.onmessage=e=>{this.blocked=e.data.blocked;if(this.blocked)this.clear();};}
  clear(){if(this.active)this.port.postMessage({active:false});this.chunks=[];this.pre=[];this.active=false;this.silent=0;this.frames=0;this.voiced=0;}
  process(inputs){
    const data=inputs[0]?.[0];if(!data||this.blocked)return true;
    let sum=0;for(const sample of data)sum+=sample*sample;
    const rms=Math.sqrt(sum/data.length);
    const calibrating=this.calibration<sampleRate*.15;
    if(calibrating){this.minimum=Math.min(this.minimum,rms);this.noise=Math.max(.0005,Math.min(.005,this.minimum));this.calibration+=data.length;}
    const threshold=Math.max(.003,Math.min(.014,this.noise*(this.active?1.8:2.8)));
    const speech=!calibrating&&rms>threshold;
    if(!this.active&&!speech&&!calibrating)this.noise=this.noise*.98+Math.min(rms,.005)*.02;
    const copy=new Int16Array(data.length);for(let i=0;i<data.length;i++){const value=Math.max(-1,Math.min(1,data[i]));copy[i]=value<0?value*32768:value*32767;}
    if(!this.active){this.pre.push(copy);while(this.pre.length>Math.ceil(sampleRate*.35/data.length))this.pre.shift();if(!speech)return true;this.active=true;this.port.postMessage({active:true});this.chunks=this.pre;this.pre=[];this.frames=this.chunks.reduce((n,c)=>n+c.length,0);}
    else{this.chunks.push(copy);this.frames+=copy.length;}
    this.silent=speech?0:this.silent+data.length;
    if(speech)this.voiced+=data.length;
    if(this.silent>sampleRate*.75||this.frames>sampleRate*58){if(this.voiced>=sampleRate*.12){const output=new Int16Array(this.frames);let offset=0;for(const chunk of this.chunks){output.set(chunk,offset);offset+=chunk.length;}this.port.postMessage({samples:output,rate:sampleRate},[output.buffer]);}this.clear();}
    return true;
  }
}
registerProcessor('cronos-capture',CronosCapture);
