import asyncio
import pytest
from fastapi import HTTPException
from cronos.app import chat_until_disconnect

def test_disconnect_cancels_pending_generation_instead_of_saving_late_reply():
    async def run():
        started=asyncio.Event();disconnected=asyncio.Event();cancelled=asyncio.Event()
        class Request:
            async def is_disconnected(self):return disconnected.is_set()
        class Engine:
            async def chat(self,*args):
                started.set()
                try:await asyncio.Future()
                finally:cancelled.set()
        task=asyncio.create_task(chat_until_disconnect(Engine(),'session','question',Request()))
        await started.wait();disconnected.set()
        with pytest.raises(HTTPException) as error:await asyncio.wait_for(task,1)
        assert error.value.status_code==499 and cancelled.is_set()
    asyncio.run(run())
