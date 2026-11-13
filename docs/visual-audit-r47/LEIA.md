# Holograma com deformação local — R47

[Vídeo de 9 segundos: parado, escutando e falando](holograma-estados.webm) · [Quadros dos três estados](estados-lado-a-lado.jpg) · [Desktop](tela-desktop.jpg) · [Celular](tela-celular.jpg)

O renderizador continua usando a textura luminosa da imagem enviada pelo usuário. O shader WebGL deforma localmente a posição dos filamentos e o brilho, sem avançar um quadro de imagem por vez nem girar a textura inteira. Na alternativa vetorial, os pontos de luz também se deslocam dentro de trechos curtos dos filamentos, sem dar uma volta contínua no anel.

O vídeo foi capturado do canvas no Chromium a 30 quadros por segundo, com **268 quadros reais**. Ele mostra três segundos parado, três escutando e três falando. Os estados e o nível de áudio foram simulados para verificar a animação; esta gravação não testa o microfone nem o alto-falante do Windows. O navegador não registrou erros de JavaScript nas telas de desktop ou celular.

Na análise de um quadro por segundo, a melhor rotação necessária para alinhar cada amostra ao primeiro quadro ficou em cerca de **1°** durante oito segundos. Na versão R46, a imagem avançava cerca de 10° por segundo. Esta medição verifica a ausência do giro global; o movimento visível agora vem das deformações locais, que aumentam na escuta e na fala.

As pranchas abaixo comparam **20 momentos** da nova animação com os quadros de referência:

- [Momentos 01–05](comparacao-01-a-05.jpg)
- [Momentos 06–10](comparacao-06-a-10.jpg)
- [Momentos 11–15](comparacao-11-a-15.jpg)
- [Momentos 16–20](comparacao-16-a-20.jpg)
