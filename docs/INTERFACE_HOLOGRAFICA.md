# Integração da interface holográfica (v0.4)

O pacote de interface fornecido pelo usuário agora é a janela principal. As
animações de núcleo, estrela e circuitos foram preservadas; respostas, gravações,
alertas e módulos usam o backend existente. As falas de exemplo e a simulação de
nível de áudio foram substituídas pelo Fish Audio e medição real de amplitude.
Não apresentamos clima, agenda, e-mails ou saúde de demonstração como integração
real. Componentes e imagens do pacote permanecem no fonte para uso futuro.

## Atualizar no Windows

1. Feche o Cronos. Preserve `.env`, `config/providers.json` e seu vault.
2. Baixe a branch `feat/cronos-test-ui` e extraia os arquivos.
3. Execute `Instalar-Cronos.bat`, depois `Iniciar-Cronos.bat`.

A interface já vem compilada em `cronos/ui`. Você não precisa instalar Node/npm.
O programa continua sendo uma janela Windows com API privada no loopback, sem
necessidade de navegador externo. A conexão é feita automaticamente pelo
inicializador desktop. Para desenvolvimento, veja [frontend/README.md](../frontend/README.md).

## Controles

- Núcleo, estrela ou botão VOZ: iniciar gravação; novamente para parar e
  transcrever. Revise a pergunta no painel e clique Enviar mensagem.
- CONVERSAR: texto, respostas e confirmações. Ouvir resposta usa Fish Audio.
  O botão de volume alterna respostas faladas automáticas; Parar fala interrompe
  reprodução ou solicitação de voz ainda pendente, sem apagar o texto.
- Símbolos: abrem os 12 módulos. Em telas pequenas, o menu de engrenagem oferece
  as mesmas funções; o núcleo continua animado.
- CONECTADO/CONECTAR: conexão e opção de falar novos alertas, quando Fish está
  configurado. Credenciais dos provedores continuam no `.env` do backend.
- Indicador superior: estado do radar. Clique para abrir Monitoramento. Ausência
  de conexão ou diagnóstico atrasado não é apresentada como sistema seguro.

As permissões do microfone são explícitas, e as gravações têm limite. Abrir por
voz com a janela fechada continua sendo responsabilidade do ouvinte local
opcional, configurável em Dispositivos; a interface não o liga sozinha.

## Segurança e desempenho

Todos os dados da interface vêm da API autenticada. Token da janela só fica em
RAM. O painel de módulos recebe o token por comunicação da mesma origem e da
janela esperada; as APIs continuam verificando bearer, Host, Origin e loopback.
Somente `/tests` aceita incorporação pela própria origem. A janela principal
continua proibindo incorporação externa. CSP mantém scripts somente da própria
origem, sem unsafe-inline/eval. Fontes, imagem de fundo e ícones são locais.

A geometria e os efeitos do Canvas permanecem. O agendamento cede tempo aos
controles e pausa o desenho oculto/coberto. Isso evita trabalho gráfico
invisível; não constitui benchmark no Windows nem garantia de fluidez em 4 GB.
O build não contém SDK/chaves Gemini ou Fish. Bibliotecas e fontes mantêm
licenças distribuídas em `cronos/ui/licenses`.

## Validação

- 102 testes Python passaram, incluindo rotas, assets e política de incorporação.
- TypeScript e build Vite passaram; instalação reproduzível com `npm ci`.
- Auditoria npm: zero vulnerabilidades conhecidas reportadas no momento da revisão.
- Chromium: Canvas alterou pixels ao longo do tempo, partículas SMIL existem,
  12 símbolos abriram funções, token desktop conectou, conversa e confirmações
  usaram API, TTS e seu analisador reproduziram áudio válido de teste, microfone
  simulado transcreveu sem envio automático, e layout móvel passou.
- O teste não fez chamadas a provedores/fontes externos no navegador. IA, Fish
  e dispositivos físicos/ações Windows continuam dependendo das suas chaves e
  validação local. O áudio de teste não certifica sua voz Fish real.
