# Interface holográfica do Cronos

Base: ZIP `cronos---interface-holográfica-e-assistente-de-voz.zip` fornecido pelo usuário.
Os componentes visuais foram incorporados preservando núcleo, estrela, circuitos,
filamentos, partículas, brilhos, logo e fundo. Componentes de cards continuam
no fonte para integração futura; dados de demonstração não são exibidos como
agenda, saúde, clima ou e-mails reais.

## Desenvolvimento

Node 22.12+ (ou Node 24) e npm. No diretório `frontend`:

```
npm ci --ignore-scripts
npm run lint
npm run build
```

O build grava `../cronos/ui`, incluindo fontes e licenças locais. Esses arquivos
são versionados e incluídos no pacote Python; o usuário Windows não precisa de
Node para executar o programa. Rode `npm run build` novamente depois de editar o
frontend e reinicie o backend se ele foi aberto antes do primeiro build.

`npm run dev` usa loopback e proxy para o backend na porta 8003. O fluxo Windows
usa o build servido pelo próprio FastAPI na mesma origem, dentro do WebView2.

## Integração

- `/`: interface holográfica. `/tests`: bancada de módulos, preservada.
- A janela chama `window.cronosConnect(token)`; token fica em RAM, nunca em URL,
  localStorage, arquivo compilado ou manifesto. Conexão manual disponível.
- Conversa chama `/chat`; ações pendentes exigem confirmação humana e não são
  autorizadas pelo modelo. Nova conversa não apaga memória anterior.
- Microfone usa MediaRecorder → `/voice/transcribe`; abre o texto para revisão.
  Não envia transcrição automaticamente à IA. Limites: 60 segundos/10 MiB.
- Fala usa `/voice/speech` do Fish Audio. A amplitude real do áudio alimenta
  as animações; não há fallback fingindo que houve fala.
- Os 12 símbolos abrem módulos reais; Linguagem abre a conversa. Um painel da
  mesma origem incorpora a bancada e recebe token via ponte limitada à origem
  e janela esperadas. Fechá-lo libera microfone e para áudio do painel.
- Monitor acompanha `/monitor`; avisos falados opcionais em Conexão local,
  separados das respostas faladas. Pode consumir créditos e não repete alertas.
- Canvas preserva desenho/efeitos e cede intervalos ao navegador para não
  monopolizar os controles. Pausa quando oculto ou coberto pelo painel de módulo.
  Não prometemos 60 FPS nem desempenho medido no notebook Samsung de 4 GB.

Fontes antes referenciadas no Google Fonts agora são empacotadas localmente,
com suas licenças. Não há SDK Gemini, chave de provedor nem chamadas diretas a
provedores no navegador. Os serviços continuam no backend.

## v0.5

Sem HUD/formulário manual de conexão. A ponte pywebviewready resolve a conexão automaticamente. `/world/view` é um contexto gráfico separado criado apenas durante uso do mapa. Consulte docs/OLHO_DE_DEUS_OBSIDIAN.md para o escopo geográfico e limites. O build inclui recursos Cesium locais e licenças; não inicie o projeto upstream nem importe suas credenciais.
