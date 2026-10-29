"""Text-first conversation transport; keep Live available for native mic audio."""
import asyncio
from dataclasses import replace

from cronos.providers import Gemini, ProviderError
from cronos.reply_stream import ready_intro, ready_reply, deliver_intro, deliver, intro_sink, reply_sink

FIRST_TEXT_TIMEOUT = 8.0


async def receive_conversation(client, url, headers, payload):
    try:
        return await _receive_conversation(client, url, headers, payload)
    except TimeoutError:
        raise ProviderError('A conexão de texto ficou sem resposta; tentando a próxima integração configurada.', 504) from None


async def _receive_conversation(client, url, headers, payload):
    """Deliver useful speech prefixes directly from Gemini's text SSE stream."""
    from cronos.structured_stream import receive, progress_sink
    introduced = delivered = False
    async with asyncio.timeout(FIRST_TEXT_TIMEOUT) as first_text:
        async def progress(characters, snapshot):
            nonlocal introduced, delivered
            if characters:
                # An active answer has its normal generation budget, not a
                # five-second cut-off. Heartbeats alone do not count as progress.
                first_text.reschedule(None)
            raw = snapshot()
            if not introduced:
                prefix = ready_intro(raw)
                if prefix:
                    await deliver_intro(prefix)
                    introduced = True
            if not delivered:
                answer = ready_reply(raw)
                if answer:
                    await deliver(answer)
                    delivered = True
        token = progress_sink.set(progress)
        try:
            return await receive(client, url, headers, payload)
        finally:
            progress_sink.reset(token)


class TextFirstGemini:
    """Avoid synthesizing discarded Gemini audio before synthesizing Cronos's voice."""
    def __init__(self, settings):
        self.settings = settings

    async def reply(self, system, messages):
        if any(message.get('audio_pcm') is not None for message in messages):
            return await Gemini(self.settings).reply(system, messages)
        delivered = False
        original_intro, original_reply = intro_sink.get(), reply_sink.get()
        async def observe_intro(value):
            nonlocal delivered
            delivered = True
            await original_intro(value)
        async def observe_reply(value):
            nonlocal delivered
            delivered = True
            await original_reply(value)
        intro_token = intro_sink.set(observe_intro) if original_intro else None
        reply_token = reply_sink.set(observe_reply) if original_reply else None
        try:
            return await Gemini(replace(self.settings, gemini_transport='rest')).reply(system, messages)
        except ProviderError as exc:
            # A working Live-only key remains usable. Never change a response
            # after any part of it has already reached the speaker.
            if delivered or self.settings.gemini_transport != 'live' or not (exc.retryable or exc.http_status == 404):
                raise
        finally:
            if intro_token is not None: intro_sink.reset(intro_token)
            if reply_token is not None: reply_sink.reset(reply_token)
        return await Gemini(self.settings).reply(system, messages)


def conversation_provider(settings):
    from cronos.providers import make_provider
    return TextFirstGemini(settings) if settings.provider == 'gemini' else make_provider(settings)
