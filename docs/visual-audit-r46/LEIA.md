# Holograma contínuo — R46

[Assistir à gravação do holograma](holograma-continuo.webm) · [Tela de desktop](tela-desktop.jpg) · [Tela de celular](tela-celular.jpg)

Esta revisão usa a textura luminosa do primeiro quadro da imagem `92312.png` fornecida pelo usuário. Um shader WebGL desloca as coordenadas da textura em torno do círculo a cada atualização. Não há sequência de imagens, cortes ou troca de quadros no renderizador. O canvas mantém a mesma aparência nos estados parado, escutando e falando; velocidade e deformação mudam suavemente conforme o estado de voz e o nível de áudio recebidos do CRONOS. O modo normal solicita até 60 atualizações por segundo; o modo de economia solicita 24. Se WebGL não estiver disponível, há um desenho vetorial contínuo como alternativa.

As quatro pranchas mostram **20 comparações** entre a referência e capturas reais do renderizador, com 400 ms entre as capturas:

- [Momentos 01–05](comparacao-01-a-05.jpg)
- [Momentos 06–10](comparacao-06-a-10.jpg)
- [Momentos 11–15](comparacao-11-a-15.jpg)
- [Momentos 16–20](comparacao-16-a-20.jpg)

A gravação do canvas tem 3,77 segundos e 114 quadros capturados a 30 fps. Na medição de diferença de brilho entre quadros consecutivos, a mediana foi 0,734, o percentil 95 foi 0,961 e o maior valor foi 1,110. A mudança não apresenta o salto repetido da antiga troca de imagens. Os estados de voz foram simulados na comparação visual; este teste não verifica o microfone nem o alto-falante do computador Windows do usuário.
