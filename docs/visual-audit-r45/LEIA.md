# Revisão visual do holograma — R45

As quatro pranchas comparam **20 quadros** do holograma com as imagens fornecidas pelo usuário: 8 em repouso, 6 escutando e 6 falando. A coluna esquerda mostra recortes das imagens `92312.png` e `92319.jpg`; a direita mostra capturas reais do canvas no Chromium. Os quadros foram capturados em intervalos de 400 ms.

- [Quadros 01–05](comparacao-01-a-05.jpg)
- [Quadros 06–10](comparacao-06-a-10.jpg)
- [Quadros 11–15](comparacao-11-a-15.jpg)
- [Quadros 16–20](comparacao-16-a-20.jpg)
- [Tela de desktop](tela-desktop.jpg)
- [Tela de celular](tela-celular.jpg)
- [Telemetria ampliada em desktop](telemetria-desktop.jpg)
- [Telemetria ampliada em celular](telemetria-celular.jpg)

Os filamentos usam 12 quadros recortados das imagens enviadas. O canvas muda de quadro continuamente e aplica uma deformação leve; a velocidade aumenta quando o estado real da voz muda. A transição entre quadros é curta para preservar a nitidez. O brilho mais forte aparece em pulsos, e o fundo azul fica em uma camada atrás das linhas. O teste visual simulou os estados no navegador; ele não prova o funcionamento de microfone ou alto-falantes no Windows.

O painel direito tem uma vista compacta e outra ampliada baseada na última imagem enviada. O fundo da vista ampliada é preto; bordas, LEDs e cards têm brilho ciano, azul, violeta e verde. Os indicadores usam o serviço `/system/metrics`; a leitura de GPU via `nvidia-smi` e a leitura de ventoinha via `psutil` são opcionais. Se o hardware não as disponibilizar, aparecem como “Indisponível”. Quando a conexão local está ausente, nenhum número é inventado. A porcentagem de saúde é um índice estimado calculado com as leituras disponíveis, não um diagnóstico do hardware.

[Comparação detalhada do painel com a imagem enviada](painel-comparacao.md).
