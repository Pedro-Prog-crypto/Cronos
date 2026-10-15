# Olho de Deus original no Cronos

Diga **Cronos, abrir Olho de Deus** ou clique no globo. A interface original ocupa toda a área do Cronos, sem recorte circular. O **X no canto superior direito** fecha e devolve a interface principal; ESC também fecha. **F4 liga/desliga o microfone do Cronos**, inclusive com foco no mapa. Alt+F4 mantém o comportamento do Windows. O botão de voz da interface embutida controla o microfone do Cronos; não inicia uma sessão paga separada de voz OpenAI.

A primeira abertura mostra o seletor original de experiências. “EXPLORE MANUALLY” começa sem ativar várias camadas. As áreas DATA LAYERS, CCTV, STREET LEVEL, CONTEXT e demais controles são as do aplicativo original, não painéis fictícios desenhados sobre um globo básico.

O pacote preserva as fontes de aeronaves, navios, satélites, clima, câmeras públicas e transporte que o projeto original disponibiliza. **Cobertura e disponibilidade variam por região/provedor.** Posição de aeronave não comprova horário de partida; dados de transporte dependem das redes publicadas. Não há promessa de todas as câmeras, ônibus ou voos do mundo. Falhas de fonte, ausência de chave ou dados indisponíveis continuam sendo informados pelo projeto.

O mapa básico pode operar sem chaves comerciais. Reconstruções Google 3D e outras camadas exigem as credenciais próprias indicadas em **POWER UP / Provider Settings**, sujeito a acesso, cobrança e termos do provedor. Fontes e ícones são empacotados localmente. Scripts externos de redes sociais não são executados no documento embutido; conteúdos opcionais que dependem desses scripts podem ficar indisponíveis. Chaves de servidor permanecem no servidor; chaves Google Maps/Cesium destinadas ao navegador precisam das restrições recomendadas pelo respectivo provedor. Não envie chaves pela conversa.

## Recursos e instalação

Os dados usam um serviço Node local, iniciado somente ao abrir o mapa. Node 24+ instalado é reaproveitado. No Windows, se faltar, o adaptador pode baixar o runtime portátil oficial Node 24.14.0, conferir SHA-256 e guardá-lo em `.cronos-local/eye/runtime`. Essa primeira preparação depende de internet e pode demorar. Não abre terminal ou instala serviços do Windows. Ao fechar o mapa, o processo de dados é encerrado; uma proteção também o encerra após ausência de heartbeat.

As configurações particulares e caches ficam em `.cronos-local/eye`. Não compartilhe essa pasta. As fontes não recebem chaves Gemini/Fish, token do Cronos ou o ambiente completo do servidor. O Python autentica o proxy e o serviço Node exige outra credencial interna. Requisições de imagens/EventSource usam um cookie HttpOnly restrito a `/api`, invalidado ao fechar.

Durante o mapa, o núcleo e a cena principal são desmontados para não desenhar por trás. A vista original embutida limita a renderização a 20 FPS e resolução de desenho até 1×; o controle original de renderização ociosa é preservado. Isso reduz trabalho, mas não garante fluidez de todas as camadas num notebook de 4 GB. Evite ativar todas simultaneamente.

A atualização usa artefatos completos em `cronos/eye-ui` e `cronos/eye-server`; não precisa de npm/node_modules na máquina do usuário. O fonte adaptado e as licenças estão em `vendor/gods-eye`. Para reconstruir, use as dependências congeladas do projeto original, `vite build --config cronos-build.config.js` nessa pasta e depois `python scripts/build_eye.py` na raiz. Mudanças desse pacote exigem instalação completa se a cópia anterior não tiver espaço ou os requisitos necessários.

## Validação

Três frentes: (1) arquivos originais e inicialização real do serviço empacotado; (2) Chromium com tela inteira, F4 dentro/fora do iframe, X, fechamento do processo e reabertura; (3) regressão de autenticação, privacidade e restante do Cronos. Testes de navegador simulam indisponibilidade de fontes externas. Não certificam dados ao vivo nem o desempenho físico do notebook Windows. Veja `DATA_SOURCES.md` para atribuições e fontes do projeto original.
