# Auditoria visual R50

O arquivo `holograma-voz.webm` mostra 15 segundos do renderizador real, em cinco
blocos de três segundos: repouso, ruído baixo, voz média, voz alta e resposta.
Os níveis de áudio desta gravação foram injetados no renderizador para tornar a
comparação repetível. O vídeo original enviado pelo usuário não foi incluído.

## Ajustes

- A textura de movimento foi extraída dos primeiros 3,5 segundos limpos do
  vídeo. O trecho posterior contém uma foto e textos sobre o centro do anel.
- A animação interpola quadros em WebGL e mantém duas trilhas contínuas para
  reduzir as interrupções vistas no contorno. O movimento nunca reinicia ao
  mudar entre repouso, escuta e fala.
- O repouso usa velocidade baixa. Na escuta, o movimento aumenta com o nível
  medido do microfone após um pequeno limiar de ruído. A fala usa o nível da
  reprodução de áudio quando o navegador o disponibiliza.
- `cinco-estados.jpg` facilita a comparação de um instante de cada estado.
  `desktop.png` e `celular.png` registram a interface compilada.

## Verificações

`npm run lint`, `npm run build`, `npm run test:orb-dynamics`,
`npm run test:orb-resolution` e `npm run test:long-capture` passaram.
Desktop (1920×1080) e celular (390×844) abriram a versão compilada no
Chromium sem erros de JavaScript.

O teste visual usou níveis simulados. A resposta de um microfone e da saída
de áudio do Windows precisa ser conferida no dispositivo do usuário.
