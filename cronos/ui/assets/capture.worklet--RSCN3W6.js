// Local PCM/VAD with a short pre-roll; no encoder, network, or secrets here.
class CronosCapture extends AudioWorkletProcessor {
  constructor(){super();this.blocked=false;this.keyword=false;this.keywordChunks=[];this.keywordFrames=0;this.chunks=[];this.pre=[];this.active=false;this.silent=0;this.frames=0;this.voiced=0;this.noise=.0005;this.calibration=0;this.minimum=Infinity;this.sensitivity=70;this.gain=2;this.port.onmessage=e=>{this.sensitivity=e.data.sensitivity??this.sensitivity;this.gain=e.data.gain??this.gain;if(e.data.keyword!==undefined&&e.data.keyword!==this.keyword){this.keyword=e.data.keyword;this.keywordChunks=[];this.keywordFrames=0;}this.blocked=e.data.blocked??this.blocked;if(this.blocked)this.clear();};}
  clear(){if(this.active)this.port.postMessage({active:false});this.chunks=[];this.pre=[];this.active=false;this.silent=0;this.frames=0;this.voiced=0;}
  process(inputs){
    const data=inputs[0]?.[0];if(!data)return true;
    if(this.keyword){
      const copy=new Int16Array(data.length);for(let i=0;i<data.length;i++)copy[i]=Math.max(-1,Math.min(1,data[i]))*32767;
      this.keywordChunks.push(copy);this.keywordFrames+=copy.length;
      if(this.keywordFrames>=sampleRate*.1){const output=new Int16Array(this.keywordFrames);let offset=0;for(const part of this.keywordChunks){output.set(part,offset);offset+=part.length;}this.port.postMessage({keyword:output},[output.buffer]);this.keywordChunks=[];this.keywordFrames=0;}
    }
    if(this.blocked)return true;
    let sum=0,peak=0;for(const sample of data){sum+=sample*sample;peak=Math.max(peak,Math.abs(sample));}
    const rms=Math.sqrt(sum/data.length);
    const calibrating=this.calibration<sampleRate*.15;
    if(calibrating){this.minimum=Math.min(this.minimum,rms);this.noise=Math.max(.0005,Math.min(.005,this.minimum));this.calibration+=data.length;}
    const sensitivity=Math.max(0,Math.min(100,this.sensitivity))/100;
    const floor=.004-sensitivity*.003;
    const multiplier=(this.active?1.7:3)-sensitivity*.9;
    const threshold=Math.max(floor,Math.min(.014,this.noise*multiplier));
    const speech=!calibrating&&rms>threshold;
    if(!this.active&&!speech&&!calibrating)this.noise=this.noise*.98+Math.min(rms,.005)*.02;
    const safeGain=Math.min(this.gain,peak>0?.95/peak:this.gain);
    const copy=new Int16Array(data.length);for(let i=0;i<data.length;i++){const value=Math.max(-1,Math.min(1,data[i]*safeGain));copy[i]=value<0?value*32768:value*32767;}
    if(!this.active){this.pre.push(copy);while(this.pre.length>Math.ceil(sampleRate*.35/data.length))this.pre.shift();if(!speech)return true;this.active=true;this.port.postMessage({active:true});this.chunks=this.pre;this.pre=[];this.frames=this.chunks.reduce((n,c)=>n+c.length,0);}
    else{this.chunks.push(copy);this.frames+=copy.length;}
    this.silent=speech?0:this.silent+data.length;
    if(speech)this.voiced+=data.length;
    if(this.silent>sampleRate*.75||this.frames>sampleRate*58){if(this.voiced>=sampleRate*.12){const kept=Math.min(this.frames,this.frames-this.silent+Math.ceil(sampleRate*.15));const output=new Int16Array(kept);let offset=0;for(const chunk of this.chunks){const count=Math.min(chunk.length,kept-offset);if(count<=0)break;output.set(chunk.subarray(0,count),offset);offset+=count;}this.port.postMessage({samples:output,rate:sampleRate},[output.buffer]);}this.clear();}
    return true;
  }
}
registerProcessor('cronos-capture',CronosCapture);
