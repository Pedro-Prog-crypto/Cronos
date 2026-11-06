# CRONOS RESTORE — desempenho

Não houve acesso ao notebook HP G42, ao microfone físico, à rede da conta do usuário nem a provedores autenticados neste ambiente. Portanto **p50, p95, tempo até primeiro token e tempo até primeira fala reais permanecem não medidos**. Não há alegação de resposta em 2–5 segundos.

| Medida verificável | Antes | Agora | Evidência |
| --- | ---: | ---: | --- |
| Tamanho máximo de WAV na conversa direta | 2 MiB | 10 MiB | Limites da rota e do middleware; WAV sintético de 180 s percorre a rota em teste. |
| Fala contínua antes do corte automático | 58 s | 180 s | Teste que executa o worklet. |
| Áudio recuperado pelo botão Enviar | Últimos 30 s | Até 180 s | Teste do worklet com 75 s. |
| Sessão de transcrição parcial local | 65 s | 190 s | Limite do WebSocket no código; dispositivo real não testado. |
| Prazo máximo de ASR longo no servidor | 40 s total, 30 s por provedor | Até 120 s total, até 115 s por provedor | Teste de cálculo; fala curta permanece com 40/30 s. |

O Cronos já registra `audio_received`, `recognition_requested/response`, `answer_requested/received`, `voice_requested/received` e `playback_started` por turno, sem guardar conteúdo da pergunta. `cronos/conversation_metrics.py` guarda as métricas locais do cliente; o Studio agora registra `elapsed_ms` por tentativa de provedor. Para saber onde o HP G42 perde tempo, é necessário executar perguntas reais e comparar essas etapas. Prazos maiores para *entradas longas* evitam cortes prematuros, mas não aceleram provedores externos.
