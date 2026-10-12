# Contrato do backend Cronos — v0.2

A interface definitiva é independente deste backend. A interface básica em `/`
permanece uma bancada de testes, e não foi copiada da interface do ZIP antigo.
Todas as rotas de dados exigem `Authorization: Bearer <CRONOS_API_TOKEN>`.
`GET /health` é público e confirma apenas o processo. Esquema: `/openapi.json`.

Configure `CRONOS_CORS_ORIGINS` com origins exatas se sua interface usar outra
origin. O backend deve ficar no loopback para a instalação pessoal. O token
permite acessar todas as conversas/notas autorizadas; não há separação por usuário.

## Chat

`POST /chat`, JSON:

```json
{"message":"O que conversamos sobre Sócrates?","session_id":null}
```

Resposta:

```json
{
  "session_id":"UUID",
  "reply":"Resposta sintetizada pelo modelo",
  "topics":["Sócrates"],
  "notes":["Temas/sócrates-identificador.md"],
  "tool_results":[],
  "warnings":[]
}
```

Reutilize o ID para continuar. Limite de mensagem: 16.000 caracteres. O modelo
pode pedir ferramentas, cujos resultados entram no contexto antes da resposta.
Nenhuma resposta é transmitida em streaming de texto nesta versão.
`warnings` pode informar exportações Markdown pendentes: a conversa já foi salva
no banco e a exportação pode ser repetida. Não reenvie a conversa por causa disso.

`GET /conversations/{session_id}` retorna `messages` (`role`, `content`) e os
últimos 30 `tool_results`. O histórico inteiro permanece armazenado.

## Ferramentas e confirmação humana

`GET /tools` retorna catálogo com nome, descrição, JSON Schema e
`requires_confirmation`. `plugin_errors` informa plugins não carregados.
Somente ferramentas disponíveis na plataforma aparecem; Windows tem ferramentas
de desktop que não são anunciadas em Linux.

Uma ação pendente aparece em `tool_results`:

```json
{
  "name":"files_create",
  "status":"pending_confirmation",
  "approval_id":"UUID",
  "session_id":"UUID",
  "arguments":{"path":"nota.md","content":"Conteúdo"},
  "expires_in_seconds":300
}
```

Mostre os argumentos e botões Confirmar/Cancelar ao usuário. Depois da decisão
humana, envie `POST /tools/approvals/{approval_id}`:

```json
{"session_id":"UUID da mesma conversa","accepted":true}
```

A confirmação é específica da conversa, válida por cinco minutos e de uso único.
Não sobrevive ao reinício. O modelo não recebe uma ferramenta para se confirmar.
Não envie `accepted=true` automaticamente. A resposta traz `status` completed,
failed ou cancelled. Após a confirmação, o usuário pode continuar a conversa;
não ocorre outra chamada automática de IA. O resultado entra no contexto seguinte.
Estados de log resolvidos/expirados não devem gerar novos botões de execução.

Se o provedor falhar depois de ferramentas, o erro `detail` será um objeto com
`message`, `session_id` e `tool_results`. Preserve esse ID e mostre os resultados
antes de tentar novamente, para não repetir operações sem necessidade.

Ferramentas de arquivos se restringem a `CRONOS_FILES_ROOT`. Leitura e listagem
fornecem offsets para continuar. Criação não sobrescreve; movimentação/extrair ZIP
não substituem destinos. No Windows, `desktop_run_executable` pode iniciar um `.exe` na pasta autorizada
após confirmação humana dos argumentos. A API não oferece execução arbitrária
de shell. O resultado informa processo iniciado, não tarefa concluída.

## Memória do Obsidian

- `POST /memory/search`: JSON `{"query":"nome da minha mãe","limit":8}`; retorna
  `notes` com `path`, `title` e `excerpt`. Busca por conteúdo, títulos e aliases.
- `GET /memory/note?path=Temas/nota.md`: retorna caminho e conteúdo Markdown.
  Caminhos internos, traversal e links simbólicos são rejeitados.
- `GET /memory/status`: contagens de mensagens, notas indexadas e exportações pendentes.
- `POST /memory/sync`: repete exportações e reindexa edições externas, sem duplicar
  seções já exportadas. Retorna contagens e warnings.

A base mantém histórico completo e uma fila transacional. O Markdown é uma
projeção legível; não apague `.cronos/memory.sqlite3` supondo que não importa.
Não há sincronização automática entre nuvem e Windows. Use um backend por vault.

## Provedores

`GET /providers`: lista IDs, tipos, modelos e presença de configuração, sem
chaves. Presença não comprova autenticação ou disponibilidade. `CRONOS_PROVIDER`
seleciona o provedor principal; alterações de ambiente exigem reinício.

`GET /providers/{provider_id}/models` consulta os modelos anunciados pela API
do provedor, sem gerar texto ou trocar automaticamente o modelo. A lista não
comprova cota disponível; no Gemini são filtrados os modelos de geração.

O manifesto `config/providers.json` registra adaptadores compatíveis sem limite
fixo de quantidade. Exemplos em `config/providers.example.json`. O conselho é a
ferramenta `consult_models`, cujo envio precisa de confirmação e pode gerar custos.
Os resultados são separados por provedor para permitir análise crítica.

## Voz Fish Audio

`POST /voice/speech`, JSON:

```json
{"text":"Olá, sou o Cronos.","reference_id":null,"speed":1.0}
```

Retorna MP3 com `Content-Type: audio/mpeg`. Até 50.000 caracteres por chamada;
a API do provedor pode impor outros limites. `reference_id` é opcional: usa a
configuração do backend ou a voz padrão do Fish. Velocidade: 0,5 a 2,0.

`POST /voice/stream`: mesma entrada, retorna chunks MP3 enquanto são produzidos.
Use um cliente que aceite leitura incremental; a interface básica usa síntese
completa. Autorização continua necessária. Não use uma URL pública com token na
query. Falhas antes do primeiro chunk retornam JSON; depois do início, a conexão
pode ser interrompida e o cliente deve informar falha de áudio. Não há repetição
automática que possa sintetizar duas vezes ou duplicar cobrança.

`POST /voice/transcribe`: áudio diretamente no corpo binário, sem multipart.
Limite: 10 MiB. Retorna `{"text":"transcrição"}`. Formatos aceitos dependem do
Fish Audio. Transcrição não envia automaticamente o texto à conversa.

Fluxo sugerido: gravar, transcrever, deixar o usuário revisar, enviar a `/chat`,
sintetizar a resposta e reproduzir. O texto continua disponível se a voz falhar.
Não há ainda protocolo Gemini Live, wake word ou interrupção de fala.

## Status e erros

`GET /status`: provedor e presença de configurações de IA/voz/personalidade.
`fish_configured` indica chave; `custom_voice_configured` indica ID personalizado.

- `401`: token inválido/ausente.
- `404`: nota não encontrada ou caminho inválido.
- `409`: confirmação inválida, de outra conversa, expirada ou já utilizada.
- `413`: áudio acima do limite.
- `422`: entrada inválida.
- `503`: configuração ausente ou falha no provedor de conversa.
- `502`: erro do Fish Audio.
- `500`: erro no acesso à memória/personalidade.

Erros usam `detail`, string ou objeto no caso de falha após ferramentas. Mensagens
não incluem chaves ou o corpo bruto de erros do provedor. Não interprete
`/health`, presença de credenciais ou testes simulados como validação real de IA.

## Radar e alertas

`GET /monitor?after=0` exige autenticação. Retorna `state` (`monitoring` ou
`attention`), `checked_at` UTC, `interval_seconds`, `cursor`, `alerts` ativos,
`events` posteriores ao cursor informado, `resources`, `components` e `scope`.
Cada alerta tem `id`, `code`, `severity` (`warning`/`critical`), `message`,
`suggestion`, `time`, `status` e `acknowledged`. Eventos de recuperação usam
`status=resolved`, `severity=info`. Os estados dos componentes indicam apenas a
última operação real observada, não disponibilidade garantida.

`POST /monitor/alerts/{id}/ack` registra ciência, sem corpo; não remove o alerta
nem corrige sua causa. Retorna 404 se o alerta não estiver mais ativo. A próxima
operação bem-sucedida encerra o aviso de falha correspondente.

Diagnóstico periódico de 15 segundos, sem chamadas a provedores: personalidade
(hash relativo ao início da execução, leitura limitada), exportações pendentes,
espaço do disco do vault (<250 MiB) e RAM do sistema (>=90%). Há avisos de token
curto, plugins e executáveis habilitados. Cinco acessos negados em 60 segundos
produzem alerta sem afirmar que houve invasão. Falhas de conversa/voz/sync são
observadas na resposta HTTP, sem registrar prompts, tokens, IPs ou erros brutos.

A interface consulta a cada cinco segundos, mostra alterações sem modificar a
conversa e pode falar novos alertas se o usuário habilitar Fish Audio. Não fala
alertas do próprio serviço de voz, não repete chamadas de síntese que falharam e
mantém avisos escritos se reprodução/síntese falhar. Fala pode consumir créditos;
modo local não usa Fish. O navegador pode restringir reprodução automática.
A animação respeita a preferência de reduzir movimentos e pausa se o diagnóstico
ficar atrasado ou a conexão falhar. Falhas de autenticação param o polling até
verificar novamente a conexão.

O serviço monitora enquanto o processo está aberto. Não protege o Windows inteiro,
não verifica Defender/firewall em tempo real, não monitora câmera/microfone nem
reconhece perigos físicos. Não há notificações nativas com o programa fechado.
Eventos ficam somente na RAM (últimos 200) e reiniciar perde esse histórico; os
alertas periódicos são recalculados. A mudança de personalidade precisa ser
conferida pelo usuário e, após validada, reinício estabelece uma nova referência.
Uma nova interface pode consumir estes endpoints sem usar o radar de teste.

A ferramenta de leitura `system_diagnostics` permite ao modelo consultar o estado,
alertas ativos, recursos e escopo reais durante uma conversa. Não realiza varredura
extra nem retorna o histórico inteiro de eventos. Em modo online, esse diagnóstico
genérico entra no contexto enviado ao provedor quando a ferramenta é utilizada.
