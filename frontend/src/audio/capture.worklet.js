// Local PCM/VAD with a short pre-roll; no encoder, network, or secrets here.
import {createSpeechDetector} from './speechDetector.js';
class CronosCapture extends AudioWorkletProcessor {
  constructor(){super();this.blocked=false;this.waiting=false;this.keyword=false;this.keywordChunks=[];this.keywordFrames=0;this.chunks=[];this.pre=[];this.active=false;this.silent=0;this.frames=0;this.voiced=0;this.speechRun=0;this.voiceLevel=0;this.voiceReference=0;this.energyMean=0;this.energyVariance=0;this.vad=null;this.vadFrame=new Int16Array(320);this.vadOffset=0;this.vadSpeech=false;this.sensitivity=70;this.gain=2;this.port.onmessage=e=>{
    if(e.data.vadBinary){createSpeechDetector(e.data.vadBinary).then(vad=>{this.vad=vad;this.port.postMessage({vadReady:true});}).catch(()=>this.port.postMessage({vadError:true}));return;}
    if(e.data.waiting!==undefined&&e.data.waiting!==this.waiting){this.waiting=e.data.waiting;if(this.waiting)this.clear();}
    if(e.data.arm){let frames=0;const tail=[];for(let i=(this.active?this.chunks:this.pre).length-1;i>=0&&frames<sampleRate*1.5;i--){const part=(this.active?this.chunks:this.pre)[i];tail.unshift(part);frames+=part.length;}this.waiting=false;this.chunks=tail;this.pre=[];this.frames=frames;this.silent=0;this.voiced=Math.max(Math.min(this.voiced,frames),sampleRate*.12);this.active=true;this.port.postMessage({active:true});}
    const previous=this.sensitivity;this.sensitivity=e.data.sensitivity??this.sensitivity;if(previous!==this.sensitivity)this.vad?.mode(this.sensitivity>=80?1:this.sensitivity>=40?2:3);
    this.gain=e.data.gain??this.gain;if(e.data.keyword!==undefined&&e.data.keyword!==this.keyword){this.keyword=e.data.keyword;this.keywordChunks=[];this.keywordFrames=0;if(this.keyword&&this.pre.length){const parts=this.pre.slice(-Math.ceil(sampleRate/128)),size=parts.reduce((n,p)=>n+p.length,0),output=new Int16Array(size);let offset=0;for(const part of parts){output.set(part,offset);offset+=part.length;}this.port.postMessage({keywordPre:output},[output.buffer]);}}this.blocked=e.data.blocked??this.blocked;if(this.blocked)this.clear();
  };}
  clear(){if(this.active)this.port.postMessage({active:false});this.chunks=[];this.pre=[];this.active=false;this.silent=0;this.frames=0;this.voiced=0;this.speechRun=0;this.voiceLevel=0;this.voiceReference=0;this.energyMean=0;this.energyVariance=0;this.vadOffset=0;this.vadSpeech=false;}
  process(inputs){
    const data=inputs[0]?.[0];if(!data)return true;
    if(this.keyword){
      const copy=new Int16Array(data.length);for(let i=0;i<data.length;i++)copy[i]=Math.max(-1,Math.min(1,data[i]))*32767;
      this.keywordChunks.push(copy);this.keywordFrames+=copy.length;
      if(this.keywordFrames>=sampleRate*.1){const output=new Int16Array(this.keywordFrames);let offset=0;for(const part of this.keywordChunks){output.set(part,offset);offset+=part.length;}this.port.postMessage({keyword:output},[output.buffer]);this.keywordChunks=[];this.keywordFrames=0;}
    }
    if(this.blocked||!this.vad)return true;
    let peak=0,sum=0;for(const sample of data){peak=Math.max(peak,Math.abs(sample));sum+=sample*sample;}
    const safeGain=Math.min(this.gain,peak>0?.95/peak:this.gain);
    const copy=new Int16Array(data.length);for(let i=0;i<data.length;i++){const value=Math.max(-1,Math.min(1,data[i]*safeGain));copy[i]=value<0?value*32768:value*32767;}
    for(const value of copy){this.vadFrame[this.vadOffset++]=value;if(this.vadOffset===320){this.vadSpeech=this.vad.process(this.vadFrame);this.vadOffset=0;}}
    const rms=Math.sqrt(sum/data.length);
    const delta=rms-this.energyMean;this.energyMean=this.energyMean?this.energyMean*.9+rms*.1:rms;this.energyVariance=this.energyVariance*.9+delta*delta*.1;
    this.voiceReference*=.999;
    // Quiet, modulated speech remains valid when the speaker lowers their
    // voice. Weak stationary background must not inherit the previous word.
    const modulated=Math.sqrt(this.energyVariance)>this.energyMean*.25;
    const speech=this.vadSpeech&&rms>.0001&&(rms>this.voiceReference*.18||modulated);
    if(speech){this.voiceLevel=this.voiceLevel?this.voiceLevel*.98+rms*.02:rms;this.voiceReference=Math.max(this.voiceReference,this.voiceLevel);}
    this.speechRun=speech?this.speechRun+data.length:0;
    if(this.waiting){this.pre.push(copy);while(this.pre.length>Math.ceil(sampleRate*1.5/data.length))this.pre.shift();return true;}
    if(!this.active){this.pre.push(copy);while(this.pre.length>Math.ceil(sampleRate*.35/data.length))this.pre.shift();if(!speech)return true;this.active=true;this.port.postMessage({active:true});this.chunks=this.pre;this.pre=[];this.frames=this.chunks.reduce((n,c)=>n+c.length,0);}
    else{this.chunks.push(copy);this.frames+=copy.length;}
    // Isolated clicks and short noise detections cannot renew the phrase forever.
    this.silent=this.speechRun>=sampleRate*.12?0:this.silent+data.length;
    if(speech)this.voiced+=data.length;
    if(this.silent>sampleRate*.75||this.frames>sampleRate*58){if(this.voiced>=sampleRate*.12){const kept=Math.min(this.frames,this.frames-this.silent+Math.ceil(sampleRate*.25));const output=new Int16Array(kept);let offset=0;for(const chunk of this.chunks){const count=Math.min(chunk.length,kept-offset);if(count<=0)break;output.set(chunk.subarray(0,count),offset);offset+=count;}this.port.postMessage({samples:output,rate:sampleRate},[output.buffer]);}this.clear();}
    return true;
  }
}
registerProcessor('cronos-capture',CronosCapture);
