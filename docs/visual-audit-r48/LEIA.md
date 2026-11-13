# Movimento do holograma — R48

[Vídeo dos três estados](holograma-estados.webm) · [Quadros dos estados](tres-estados.jpg) · [Amostras em 30 segundos](30-segundos.jpg) · [Desktop](tela-desktop.jpg) · [Celular](tela-celular.jpg)

O renderizador mantém a textura da imagem fornecida pelo usuário. Um campo contínuo desloca seus filamentos radial e tangencialmente. O deslocamento depende do ângulo, do tempo e da posição radial, de modo que camadas próximas mudam em fases diferentes. Duas ondas circulam em ritmos diferentes e uma oscilação menor acrescenta movimento interno. Não há rotação global da textura, troca de imagens nem reinício do tempo ao mudar de estado.

O estado da voz altera gradualmente velocidade e amplitude. O nível de áudio passa por um envelope com resposta rápida na subida e retorno mais lento na descida. Mesmo com volume zero, o movimento base continua. Os três estados no vídeo foram **simulados** para examinar a animação; a gravação não verifica o microfone nem o alto-falante do Windows.

## Verificações

- Vídeo capturado do canvas no Chromium: 9 segundos, 269 quadros a 30 fps, com parado, escutando e falando em sequência.
- Captura adicional de 30 segundos, com uma amostra por segundo: diferença de brilho entre amostras consecutivas de 3,62 a 16,49 pontos, mediana 9,39. A primeira e a última diferiram 13,6 pontos; não houve retorno ao quadro inicial nesse período.
- Nas amostras de 30 segundos, o centro da caixa do anel luminoso variou até cerca de 4 pixels em uma imagem de 300 × 300 pixels. O centro matemático do campo permanece fixo.
- As páginas de produção abriram em desktop e celular sem erros de JavaScript. O modo vetorial sem WebGL também foi renderizado e apresentou movimento.

As pranchas seguintes comparam 20 capturas do renderizador à sequência de referência. Os instantes não correspondem exatamente ao tempo de cada imagem fornecida pelo usuário; servem para avaliar formato e evolução do movimento:

- [Momentos 01–05](comparacao-01-a-05.jpg)
- [Momentos 06–10](comparacao-06-a-10.jpg)
- [Momentos 11–15](comparacao-11-a-15.jpg)
- [Momentos 16–20](comparacao-16-a-20.jpg)
