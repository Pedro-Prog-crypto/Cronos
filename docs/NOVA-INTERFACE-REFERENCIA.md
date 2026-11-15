# Cronos R55 — interface e holograma dos vídeos

A tela inicial usa o fundo quadriculado azul, holograma de centro vazio e o pequeno botão azul do microfone abaixo. Menus, barras de funções e cartões ficam ocultos até serem pedidos. O estado de voz aparece durante a escuta ou fala. Os painéis laterais aparecem quando os cards são abertos; a visão geral recolhe os painéis para não cobrir os cards. A composição foi comparada com os cinco vídeos descritos em `docs/ANALISE-VIDEOS-REFERENCIA.md`.

## Movimento

`tools/extract_front_orb.py` extrai quadros da filmagem frontal, com alinhamento de câmera, e constrói `orb-front-field.png`. A R55 separa traços ciano de primeiro plano, fios azuis discretos e pontos luminosos captados no vídeo. Um núcleo radial mais estreito reduz a espessura aparente sem fechar todas as falhas reais do traçado. Os 155 quadros de fala e os 45 de escuta formam ciclos separados. Em repouso, a escuta alimenta o anel mais calmo; ao falar, a sequência luminosa de fala entra gradualmente. A intensidade e a velocidade também respondem ao áudio. O canvas chega a 1080 × 1080 pixels no desktop e é limitado a 30 quadros por segundo nessa resolução. Se o dispositivo não aceitar a textura WebGL de 4080 px, há filamentos vetoriais de reserva.

O fundo recebeu zonas de luz menos uniformes e o botão de voz uma linha horizontal discreta. Durante processamento ou transcrição, o indicador mostra **PENSANDO** em amarelo e o botão assume contorno amarelo. A escuta mantém o contorno azul.

A sequência original de filmagem é finita e tem artefatos de câmera. Portanto, o ciclo visual e a reação ao áudio não são uma cópia quadro a quadro de uma animação fonte ilimitada. A etapa de fala acompanha o início dos blocos realmente enviados à síntese de voz; não há sincronização por fonema. Uma prévia em vídeo do navegador permite avaliar o movimento, além das imagens estáticas.

## Cards e funções

Comandos como “abra sistema”, “abra clima”, “abra agenda”, “abra e-mail”, “abra tecnologia”, “abra memória” e “feche painel” abrem e fecham as funções. O botão azul aciona o microfone; F4 continua disponível. O card ativo ocupa o centro. Os anteriores passam para miniaturas abaixo; a visão geral reúne os cards. Em celulares, a visão geral usa duas colunas com rolagem. Os cards de resposta usam o texto real gerado pelo Cronos; os comandos da página inicial abrem módulos existentes.

Processamento e telemetria consultam `/system/metrics`. Memória abre o painel de memória. Clima, calendário, e-mail e notícias mostram a ausência de fontes conectadas e encaminham para as ferramentas apropriadas; não exibem valores fictícios da prancha. As três fotografias de tecnologia, IA e política são marcadas como ilustrativas quando as fontes ainda não estão conectadas. A interface não configura essas integrações automaticamente.

## Verificação

`npm run lint`, `npm run build`, `npm run test:orb-resolution`, `npm run test:orb-dynamics`, `python tools/check_reference_dashboard.py` e `python tools/check_hologram_motion_r55.py` verificam a interface. A checagem no Chromium cobre o movimento nos três estados, a aparência de **PENSANDO**, o canvas de 1080 pixels, os cards e larguras de 1440, 1024 e 390 px. As capturas estão em `docs/visual-audit-r55/`. A verificação usa o estado desconectado e simula o roteamento dos comandos; o reconhecimento com microfone físico, a fala com provedor remoto e a instalação Windows dependem do ambiente do usuário.
