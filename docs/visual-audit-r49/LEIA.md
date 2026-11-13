# Holograma com movimento extraído do vídeo — R49

[Gravação dos três estados](holograma-estados.webm) · [Quadros](tres-estados.jpg) · [Tela desktop](tela-desktop.png) · [Tela de celular](tela-celular.png)

O anel agora usa um campo de luz polar extraído de sete segundos do vídeo enviado pelo usuário. O campo registra a posição e a intensidade do contorno a 30 amostras por segundo. O shader interpola duas amostras consecutivas em cada desenho, aplica brilho azul e mantém o preenchimento central como camada separada. O trecho termina com uma transição de meio segundo para o começo, sem corte abrupto. O vídeo original, sua legenda, marca e painéis não foram incluídos no projeto.

O primeiro teste com três curvas calculadas em código era mais liso e regular do que o vídeo. Vinte pares de quadros foram comparados localmente; essa diferença levou à troca do método. O campo atual segue a forma captada no trecho extraído. A filmagem do monitor tem resolução e compressão limitadas; a reconstrução não é uma cópia de pixels em alta definição. Há suavização espacial e temporal para reduzir artefatos da câmera. O modo sem WebGL usa o desenho vetorial de reserva.

O estado real de voz continua vindo do CRONOS. Escuta e fala alteram gradualmente a velocidade e o brilho do mesmo anel; a troca de estado não reinicia o tempo. A gravação acima **simula** esses estados para verificar a animação e não comprova que o microfone ou o alto-falante do Windows funcionam.

Verificações executadas: `npm run lint`, `npm run test:orb-resolution`, `npm run build`, abertura da interface de produção em Chromium desktop e celular sem erro JavaScript, gravação de nove segundos dos três estados e gravação adicional de quinze segundos no estado parado. A última gerou 224 quadros analisados a 15 fps; a diferença média entre quadros vizinhos teve mediana de 7,99 e máximo de 22,19 em RGB de 0 a 255. A primeira e a última amostras tiveram diferença média de 26,50, confirmando que não ficou parado durante a gravação.
