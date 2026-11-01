"""10,000 controlled recovery simulations; these are NOT live API/Windows tests."""
import argparse
import asyncio
from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

from cronos.config import Settings
from cronos import evolution
from cronos.providers import ProviderError
from cronos.reply_stream import deliver_intro,intro_sink
from cronos.transcription import first_valid_transcription

NAMES=['slow_answer_without_reserve','primary_429_reserve_answers','reserve_429_primary_survives',
       'reserve_answers_cancels_loser','intro_keeps_one_speaker','user_cancel_cleans_both',
       'auth_denial_is_reported','two_asr_fail_local_recovers','asr_primary_survives_bad_reserve','screen_reserve_single_tool_proposal']


async def case(index,base):
    mode=index%10;reply=f'Resposta real de teste {index}.';calls=[];closed=[];spoken=[]
    released=asyncio.Event();reserve_started=asyncio.Event()
    settings=replace(base,provider='solo' if mode==0 else 'primary',ollama_model=str(mode))
    class Primary:
        async def reply(self,*args):
            calls.append('primary')
            try:
                if mode==1:raise ProviderError('rate_limit',429)
                if mode==6:raise ProviderError('authentication_denied',401)
                if mode in {2,8}:await released.wait()
                elif mode in {3,5,9}:await asyncio.sleep(10)
                elif mode==4:
                    await deliver_intro(reply+' ');await asyncio.sleep(.003)
                else:await asyncio.sleep(.003)
                return {'reply':reply+' Fim.','topics':[],'tool_calls':[]}
            finally:closed.append('primary')
    class Reserve:
        async def reply(self,*args):
            calls.append('reserve');reserve_started.set()
            try:
                if mode==9:assert args[1][-1]['image']=={'mime_type':'image/jpeg','data':str(index)}
                if mode==2:
                    released.set();raise ProviderError('rate_limit',429)
                if mode==5:await asyncio.sleep(10)
                return {'reply':reply,'topics':[],'tool_calls':[{'name':'no_execution_here','arguments':{'case':index}}] if mode==9 else []}
            finally:closed.append('reserve')
    def factory(_):return Reserve()
    async def hear(text):spoken.append(text)
    token=intro_sink.set(hear)
    try:
        if mode in {7,8}:
            async def primary():
                if mode==7:return ''
                await released.wait();return reply
            async def reserve():
                released.set();raise ValueError('unrecognized')
            async def local():return reply
            result=await first_valid_transcription(primary,reserve,hedge_after=.0005,local=local if mode==7 else None)
            assert result==reply
            return 'answer_returned'
        with patch('cronos.conversation_transport.conversation_provider',factory):
            messages=[{'role':'user','content':str(index),**({'image':{'mime_type':'image/jpeg','data':str(index)}} if mode==9 else {})}]
            task=asyncio.create_task(evolution.ResilientProvider(settings,Primary()).reply('',messages))
            if mode==5:
                await reserve_started.wait();task.cancel()
                try:await task
                except asyncio.CancelledError:pass
                else:raise AssertionError('Cancelled turn returned an answer')
                assert sorted(closed)==['primary','reserve']
                return 'explicit_cancel_handled'
            if mode==6:
                try:await task
                except ProviderError as exc:assert exc.http_status==401
                else:raise AssertionError('Authentication failure claimed success')
                assert calls==['primary'];return 'auth_denial_reported'
            result=await task
            assert result['reply'].startswith(reply)
            assert len(calls)==len(closed)
            if mode==0:assert calls==['primary'] and not result.get('fallback_used')
            if mode==2:assert len(calls)==2 and not result.get('fallback_used')
            if mode in {1,3,9}:assert result['fallback_used'] and result['provider_used']=='reserve'
            if mode==4:assert calls==['primary'] and [part.strip() for part in spoken]==[reply]
            if mode==9:assert result['tool_calls']==[{'name':'no_execution_here','arguments':{'case':index}}]
            return 'answer_returned'
    finally:intro_sink.reset(token)


async def run(count,base):
    counts=Counter();outcomes=Counter();errors=[]
    # Sequential scoped provider factories keep each schedule isolated. Delays
    # vary turn identifiers and controlled ordering, without external quota use.
    for index in range(count):
        try:
            outcome=await asyncio.wait_for(case(index,base),1)
            counts[NAMES[index%10]]+=1;outcomes[outcome]+=1
        except Exception as exc:
            errors.append({'case':index,'scenario':NAMES[index%10],'error_type':type(exc).__name__,'detail':str(exc)[:160]})
        if (index+1)%1000==0:print(f'{index+1}/{count}: {len(errors)} unexpected failures',flush=True)
    return counts,outcomes,errors


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--count',type=int,default=10000);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    started=time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='cronos-recovery-stress-') as folder:
        base=replace(Settings.from_env(),provider_timeout=.4,vault=Path(folder)/'vault',providers_file=Path(folder)/'providers.json')
        with patch.object(evolution,'FIRST_REPLY_TIMEOUT_SECONDS',.0005),patch.object(evolution,'read',lambda s:{'routing':{'enabled':s.provider!='solo','fallbacks':['reserve']}}),patch.object(evolution,'provider_catalog',lambda s:[{'id':'reserve','configured':True}]):
            counts,outcomes,errors=asyncio.run(run(args.count,base))
    result={'simulations':args.count,'passed':args.count-len(errors),'unexpected_failures':len(errors),
            'scenario_counts':dict(counts),'expected_outcomes':dict(outcomes),'seconds':round(time.perf_counter()-started,3),
            'errors':errors,'scope':'Controlled provider/ASR scheduling, failures, cancellation and single-winner tool proposals. No live paid integrations, physical microphone, Windows speech or image rendering.'}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))
    raise SystemExit(bool(errors))


if __name__=='__main__':main()
