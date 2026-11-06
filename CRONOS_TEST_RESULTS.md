# CRONOS RESTORE — matriz de testes

**Escopo:** Linux da execução Codex, testes automatizados e amostras sintéticas. `PASSOU` abaixo significa apenas a condição indicada na coluna de evidência. Adaptador simulado não comprova acesso a uma API externa. O Windows/WebView2 e o microfone do usuário não estão acessíveis neste ambiente.

| Nº | Caso | Resultado | Evidência / limite |
| ---: | --- | --- | --- |
| 1 | Inicialização do aplicativo | PASSOU | FastAPI inicia via TestClient e serve interface; inicialização Windows não executada. |
| 2 | Inicialização sem internet | PASSOU | Testes de modo local isolam provedores externos. |
| 3 | Recuperação após falha de rede | PASSOU | Fallback simulado em testes de resposta e Studio. |
| 4 | Pergunta curta por texto | PASSOU | Rota `/chat` com provedor de teste. |
| 5 | Pergunta longa por texto | PASSOU | Texto de cerca de 100 mil caracteres chega sem corte ao provedor de teste; janela real do modelo precisa ser medida. |
| 6 | Conversa curta por voz | PASSOU | WAV sintético chega ao provedor de teste e resposta é salva; microfone físico não testado. |
| 7 | Conversa longa por voz | PASSOU | WAV sintético de 180 s chega à rota; worklet simulado entrega 75 s manualmente e 180 s automaticamente. ASR externo não testado. |
| 8 | Pausa durante a fala | NÃO EXECUTADO | Pausas naturais e ruído exigem ensaio no microfone do usuário. |
| 9 | Interrupção do assistente | PASSOU | Testes do assistente em segundo plano simulam cancelamento e liberação de tarefas. |
| 10 | Síntese de resposta longa | BLOQUEADO POR DEPENDÊNCIA | Voz Fish real depende de conta e saída de áudio Windows. |
| 11 | Cancelamento de geração | PASSOU | Testes de cancelamento do Studio e da resposta. |
| 12 | Falha do provedor principal | PASSOU | Adaptador simulado falha sem apagar projeto ou pergunta. |
| 13 | Fallback | PASSOU | Testes cobrem segunda e terceira integração simuladas. |
| 14 | Limite 429 | PASSOU | Respostas HTTP simuladas são classificadas; cota real do usuário continua bloqueada. |
| 15 | Token inválido | PASSOU | Testes de autenticação da API e HTTP 401 simulado. |
| 16 | Timeout | PASSOU | Testes de prazo e avanço do pool; prazos de ASR curto/longo verificados. |
| 17 | Recuperação após erro | PASSOU | Studio preserva versão/recursos e permite retomar em testes locais. |
| 18 | Criação de pizzaria | BLOQUEADO POR DEPENDÊNCIA | Nenhuma IA de código autenticada e com cota foi disponibilizada ao ambiente; não foi substituída por template. |
| 19 | Criação de barbearia | BLOQUEADO POR DEPENDÊNCIA | Mesmo bloqueio de geração real. |
| 20 | Edição de componentes | PASSOU | Testes do Studio usam adaptador controlado e confirmam versões; IA externa não provada. |
| 21 | Inclusão de imagens | PASSOU | Rotas e validação local de recursos testadas; geração externa de imagens não provada. |
| 22 | Build do site | PASSOU | Validação e build de projetos locais de teste; geração real pelo modelo bloqueada. |
| 23 | Abertura da prévia | PASSOU | Testes verificam ticket e isolamento da prévia local; navegador Windows não testado. |
| 24 | Exportação | PASSOU | Arquivos e runtime exportado testados localmente. |
| 25 | Reabertura de projeto salvo | PASSOU | Persistência e histórico do Studio exercitados em testes. |
| 26 | Funcionamento após reinicialização | PASSOU | Reinício da API preserva histórico/projetos; reinício Windows não executado. |
| 27 | Consumo de memória | NÃO EXECUTADO | É necessária medição no HP G42 durante 3 min de áudio e Studio. |
| 28 | Estabilidade da interface | NÃO EXECUTADO | Build/lint passaram, mas flicker e travamentos do WebView2 precisam de execução Windows. |
| 29 | Preservação das configurações | PASSOU | Testes verificam que Studio não altera chaves/voz/personalidade; mudanças locais preexistentes não foram revertidas. |
| 30 | Proteção de credenciais | PASSOU | Testes de logs/erros não ecoam respostas privadas; pacote público exclui `.env` e vault. |

Comandos executados nesta operação: `.venv/bin/python -m pytest -q`, `npm run lint`, `npm run build`, `npm run test:long-capture`, `npm run test:study-images`. Resultados numéricos finais devem ser confrontados com a execução da branch entregue; nenhuma linha acima afirma que Fish/Gemini/OpenAI externos ou o dispositivo Windows passaram.

**Adendo R40:** o pacote completo agora contém o código-fonte público, a interface compilada e um migrador local dos dados anteriores. A suíte completa passou com **810 testes**. Testes exercem a seleção de `Cronos-Dados`, a migração de `.env`/vault e a preservação da origem. A execução do BAT e do seletor no Windows permanece sem ensaio físico nesta máquina Linux.

**Adendo R41:** a suíte completa passou com **818 testes**. Ela inclui perguntas de 15 linhas, falhas simuladas na memória sem apagar a resposta, Studio usando somente Gemini e seleção/pesquisa das fontes de estudo. `npm run lint` e `npm run build` passaram. No Chromium, o leitor foi conferido em 1920, 1366 e 740 pixels; uma imagem servida pela rota autenticada abriu via Blob e a leitura maximizada ampliou o painel. Chave/cota Gemini e WebView2 no HP G42 não foram testados aqui.
