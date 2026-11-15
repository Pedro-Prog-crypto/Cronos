# Holograma R56 desenhado por código

O anel agora é calculado em `frontend/src/animation/proceduralOrb.ts`. Ele não carrega imagens ou quadros do vídeo. Dezesseis curvas azuis finas e discretas formam os detalhes de fundo; seis curvas ciano independentes criam os trechos da frente. Três delas recebem núcleos LED mais fortes, enquanto outras ficam mais afastadas. Cada curva compartilha uma deformação lenta com as outras, mas tem deslocamento e fase próprios. O brilho percorre as curvas, e quatro pontos luminosos se movem sobre elas. A fase continua quando o estado muda entre repouso, escuta e fala.

O vídeo serve de referência para a forma, as camadas e as cores. A aparência não depende de sobrepor a filmagem. O canvas chega a 1080 × 1080 pixels no desktop e limita a animação a 30 quadros por segundo nessa resolução. O centro permanece vazio e o botão de voz continua independente do desenho.

A inspeção em Chromium verifica a tela inicial, os cards, os estados de movimento, o tamanho do canvas e a ausência de pedidos pela textura antiga. As capturas estão em `docs/visual-audit-r56/`. O microfone físico e o instalador Windows ainda dependem de teste no computador do usuário.
