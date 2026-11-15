# Cronos R52 — interface e holograma dos vídeos

A tela principal segue a composição medida nos cinco vídeos em `docs/ANALISE-VIDEOS-REFERENCIA.md`: fundo quadriculado azul, holograma de centro vazio, estado de voz acima do anel e botão de voz abaixo. Os painéis laterais aparecem quando os cards são abertos ou a apresentação está ativa. A visão geral recolhe os painéis para não cobrir os cards.

## Movimento

`tools/extract_front_orb.py` extrai 212 quadros consecutivos da filmagem frontal, com alinhamento de câmera, e constrói `orb-front-field.png`. O processo preserva as linhas azul e ciano e as lacunas captadas, removendo grade, legendas e ruído mais evidente. O renderizador interpola os quadros a 30 fps e faz uma transição no fim do trecho. A intensidade e a velocidade respondem aos estados EM ESPERA, OUVINDO e FALANDO e ao nível de áudio. Se o dispositivo não aceitar a textura WebGL de 3840 px, há filamentos vetoriais de reserva.

A sequência original de filmagem é finita e tem artefatos de câmera. Portanto, o ciclo visual e a reação ao áudio não são uma cópia quadro a quadro de uma animação fonte ilimitada. A etapa de fala acompanha o início dos blocos realmente enviados à síntese de voz; não há sincronização por fonema.

## Cards e funções

O card ativo ocupa o centro. Os anteriores passam para miniaturas abaixo; ao terminar, a visão geral reúne os cards. Em celulares, a visão geral usa duas colunas com rolagem para manter os textos legíveis. Botões de anterior, próximo, visão geral e fechar continuam acessíveis. Os cards de resposta usam o texto real gerado pelo Cronos; os atalhos da página inicial abrem módulos existentes.

Processamento e telemetria consultam `/system/metrics`. Memória abre o painel de memória. Clima, calendário, e-mail e notícias mostram a ausência de fontes conectadas e encaminham para as ferramentas apropriadas; não exibem valores fictícios da prancha. A interface não configura essas integrações automaticamente.

## Verificação

`npm run lint`, `npm run build`, `npm run test:orb-dynamics`, `npm run test:reference-deck`, `python tools/check_reference_dashboard.py` e `python tools/check_hologram_motion_r52.py` passaram. A checagem no Chromium cobre movimento nos três estados, repouso, foco, miniaturas, visão geral, acesso à memória e larguras de 1440, 1024 e 390 px. Os 20 testes locais de atualização e instalador passaram. As capturas estão em `docs/visual-audit-r52/`. A verificação usa o estado desconectado; a fala com provedor remoto e a instalação Windows dependem do ambiente do usuário.
