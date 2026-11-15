# Cronos R53 — interface e holograma dos vídeos

A tela inicial usa o fundo quadriculado azul, holograma de centro vazio e o pequeno botão azul do microfone abaixo. Menus, barras de funções e cartões ficam ocultos até serem pedidos. O estado de voz aparece durante a escuta ou fala. Os painéis laterais aparecem quando os cards são abertos; a visão geral recolhe os painéis para não cobrir os cards. A composição foi comparada com os cinco vídeos descritos em `docs/ANALISE-VIDEOS-REFERENCIA.md`.

## Movimento

`tools/extract_front_orb.py` extrai 212 quadros consecutivos da filmagem frontal, com alinhamento de câmera, e constrói `orb-front-field.png`. A filtragem temporal reduz falhas repentinas nas linhas sem preencher lacunas próprias do estilo. O renderizador usa um ritmo reduzido e tons azul e ciano próximos da referência. A intensidade e a velocidade respondem aos estados EM ESPERA, OUVINDO e FALANDO e ao nível de áudio. Se o dispositivo não aceitar a textura WebGL de 3840 px, há filamentos vetoriais de reserva.

A sequência original de filmagem é finita e tem artefatos de câmera. Portanto, o ciclo visual e a reação ao áudio não são uma cópia quadro a quadro de uma animação fonte ilimitada. A etapa de fala acompanha o início dos blocos realmente enviados à síntese de voz; não há sincronização por fonema.

## Cards e funções

Comandos como “abra sistema”, “abra clima”, “abra agenda”, “abra e-mail”, “abra tecnologia”, “abra memória” e “feche painel” abrem e fecham as funções. O botão azul aciona o microfone; F4 continua disponível. O card ativo ocupa o centro. Os anteriores passam para miniaturas abaixo; a visão geral reúne os cards. Em celulares, a visão geral usa duas colunas com rolagem. Os cards de resposta usam o texto real gerado pelo Cronos; os comandos da página inicial abrem módulos existentes.

Processamento e telemetria consultam `/system/metrics`. Memória abre o painel de memória. Clima, calendário, e-mail e notícias mostram a ausência de fontes conectadas e encaminham para as ferramentas apropriadas; não exibem valores fictícios da prancha. As três fotografias de tecnologia, IA e política são marcadas como ilustrativas quando as fontes ainda não estão conectadas. A interface não configura essas integrações automaticamente.

## Verificação

`npm run lint`, `npm run build`, `npm run test:home-voice`, `npm run test:orb-dynamics`, `npm run test:reference-deck`, `python tools/check_reference_dashboard.py` e `python tools/check_hologram_motion_r53.py` verificam a interface. A checagem no Chromium cobre movimento nos três estados, repouso, foco, miniaturas, visão geral, acesso a funções e larguras de 1440, 1024 e 390 px. As capturas estão em `docs/visual-audit-r53/`. A verificação usa o estado desconectado e simula o roteamento dos comandos; o reconhecimento com microfone físico, a fala com provedor remoto e a instalação Windows dependem do ambiente do usuário.
