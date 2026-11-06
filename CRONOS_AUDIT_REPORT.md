# CRONOS RESTORE — diagnóstico inicial

Esta auditoria usa o código da branch `fix/cronos-restore-2026-11-05` e os sintomas relatados pelo usuário. Ela não examina nem publica `.env`, vault ou chaves.

## Mapa real

| Área | Caminhos | Papel |
| --- | --- | --- |
| Entrada e API | `ABRIR-CRONOS.bat`, `Instalar-Cronos.bat`, `cronos/desktop.py`, `cronos/app.py` | Inicialização Windows, FastAPI, rotas de chat, áudio e estado. |
| Interface | `frontend/src/App.tsx`, `frontend/src/hooks/useCronosVoice.ts`, `frontend/src/audio/capture.worklet.js`, `cronos/ui/` | React/Vite, captura/VAD, envio e reprodução; `cronos/ui` contém o build servido. |
| IA | `cronos/engine.py`, `cronos/providers.py`, `cronos/integrations.py`, `cronos/evolution.py`, `cronos/council.py` | Contexto, Gemini/Live, Ollama, adaptadores configuráveis e rotas alternativas. |
| Voz | `cronos/transcription.py`, `cronos/live_transcription.py`, `cronos/recognition.py`, `cronos/media_streams.py`, `cronos/device_voice.py` | Fish/Gemini/Vosk, transcrição parcial, áudio e voz de reserva. |
| Studio | `cronos/studio/service.py`, `provider_pool.py`, `store.py`, `validation.py`, `routes.py`, `frontend/src/components/SiteStudio.tsx` | Geração, tentativas de provedores, revisões, validação, prévia e exportação. |
| Dados e diagnóstico | `cronos/memory.py`, `cronos/studio/store.py`, `cronos/conversation_metrics.py`, `cronos/delivery.py`, `cronos/diagnostics.py` | SQLite/vault, versões de projetos, métricas por turno sem conteúdo privado. |
| Configuração e testes | `pyproject.toml`, `frontend/package.json`, `.env.example`, `tests/` | Dependências, build e testes automatizados. |

## Defeitos e bloqueios observados

| Gravidade | Arquivo | Evidência e causa | Correção proposta / prova | Risco |
| --- | --- | --- | --- | --- |
| Alta | `cronos/app.py`, `cronos/security.py`, rota `/chat/audio/stream` | **Confirmado no código:** ambos rejeitam WAV acima de 2 MiB, embora `/voice/transcribe` aceite 10 MiB. A 16 kHz/16-bit, 2 MiB representam cerca de 65 s. | Alinhar os dois limites e testar áudio sintético longo sem usar microfone privado. | Provedor externo pode impor limite menor; documentar. |
| Alta | `frontend/src/audio/capture.worklet.js`, `frontend/src/hooks/useCronosVoice.ts` | **Confirmado no código:** a fala automática encerra aos 58 s e o envio manual só recupera os últimos 30 s, cortando uma fala longa silenciosamente. | Preservar gravação contínua dentro de um limite explícito, manter botão Enviar e testar o fluxo. | Memória do notebook e limite da transcrição externa. |
| Alta | `cronos/integrations.py` | **Confirmado no código:** adaptadores OpenAI compatíveis enviam `response_format` no chat, mas a negociação de parâmetro rejeitado só acontece no Studio estruturado. Um HTTP 400 por JSON mode impede uma resposta normal. | Negociar somente rejeições explícitas em ambos os fluxos, sem mascarar outros 400; teste HTTP simulado. | Uma API pode rejeitar outro parâmetro incompatível. |
| Alta | `cronos/studio/provider_pool.py`, configuração de provedores | **Observado no erro enviado pelo usuário:** 401 (chave rejeitada), 429 (cota) e revisão de código recusada. O pool registra tentativas e preserva revisões; esses retornos externos não são corrigidos por compilação local. | Validar seleção/fallback e apresentar o motivo real; teste com adaptadores simulados. Renovação de chave/cota depende da conta do usuário. | Sem integração de código operacional, geração real permanece bloqueada. |
| Média | `cronos/app.py`, `cronos/evolution.py`, `cronos/conversation_metrics.py` | **Hipótese a medir no Windows:** atraso pode vir de ASR, espera do modelo, TTS ou reprodução. Já existem eventos e métricas, mas não há medição desta máquina do usuário. | Medir etapas reais antes de atribuir causa; não prometer latência fixa. | Rede, hardware e provedores fora do ambiente de testes. |

O repositório já tinha uma alteração local em `releases/ABRIR-CRONOS-COM-MEUS-DADOS.zip`. Ela foi preservada fora desta correção. Antes da operação, há testes de chat, Studio, fallbacks, voz e empacotamento. Nenhuma falha de serviço externo será marcada como resolvida apenas por mocks.
