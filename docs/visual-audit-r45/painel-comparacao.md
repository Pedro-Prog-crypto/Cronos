# Painel direito: comparação com a imagem enviada

Comparação visual feita com a imagem do usuário de 13/11/2026 e capturas reais da interface no Chromium. A captura de desktop usa **leituras reais deste ambiente de teste** e a conexão da interface foi simulada para observar os componentes; ela não comprova voz ou provedores de IA no computador do usuário. As leituras variam a cada oito segundos.

| Elemento | Imagem enviada | Implementação R45 | Diferença observada |
| --- | --- | --- | --- |
| Silhueta | Moldura alta, cantos arredondados e vários recortes diagonais. | Máscara SVG com recortes superiores, cantos inferiores chanfrados e contorno duplo. | O desenho externo ainda é mais simples que a ilustração. |
| Fundo | Preto profundo com discretas camadas azul marinho. | Fundo quase preto e cards azul marinho escuro. | Próximo; a transparência da referência não é reproduzida literalmente. |
| LEDs | Pontos brancos/cianos intensos em segmentos específicos da borda. | Segmentos claros na moldura e três LEDs superiores com pulsação lenta. | Menor número de pontos de luz. |
| Cabeçalho | Ícone circular, título grande, subtítulo e estado Online. | Esses quatro elementos estão presentes. Online depende da conexão real com o núcleo. | O ícone geométrico e a tipografia têm desenho próprio. |
| Chip | Ilustração isométrica rica em camadas, circuitos e partículas. | SVG isométrico vetorial separado da interface, com camada superior, corpo, pinos, circuitos e pontos luminosos. | Menos profundidade e detalhes que a arte original. |
| Anel central | Anel grande com segmentos ciano, azul e violeta; 87% ilustrativo. | Anel segmentado em cores equivalentes, com percentual calculado de CPU, RAM, disco e temperatura quando disponível. Sem dados, mostra travessão. | O índice é uma estimativa de carga e temperatura, não um diagnóstico clínico de hardware. |
| Serviços | Cinco linhas com checks verdes. | Cinco linhas mostram check apenas quando há verificação suficiente; configuração de IA, gravação de memória e microfone sem teste mostram travessão. | A quantidade de checks varia com o estado real. |
| Grade | CPU/RAM/GPU e disco/rede/bateria em três colunas. | Mesma ordem; bateria não aparece neste ambiente sem bateria e rede ocupa seu espaço. | Uma linha pode ter cinco cards, por exigência de não mostrar bateria fictícia. |
| Anéis dos cards | Porcentagens em círculos luminosos dentro dos cards. | Círculos estão nos cards com porcentagem, tanto na vista ampliada quanto na compacta. | O traço do círculo é ligeiramente mais fino. |
| CPU | Ícone, frequência, anel e curva temporal. | Valor real do processador, frequência quando disponível e curva dos últimos ciclos. | A frequência máxima depende do sistema operacional. |
| RAM | Anel violeta, uso absoluto e curva. | Mesmos elementos com uso medido. | Violeta foi reduzido para manter o ciano dominante. |
| GPU | Anel e memória gráfica. | Leitura opcional via `nvidia-smi`; sem leitura, mostra “Indisponível”. | A imagem ilustra 37%; esta máquina não fornece leitura de GPU. |
| Disco | Barra, percentual circular e capacidade. | Esses dados vêm do sistema. | A unidade usada é GiB, exibida como GB para leitura rápida. |
| Rede | Download, upload e gráfico. | Taxas reais separadas em Mb/s, atualizadas periodicamente; o gráfico exige ao menos duas leituras. | A primeira leitura não permite calcular velocidade e aparece indisponível. |
| Bateria | Barra verde, anel, estado de carga. | Aparece somente quando o sistema informa bateria; a cor acompanha o estado. | Não aparece na captura desta máquina de teste. |
| Temperatura | Duas barras térmicas coloridas. | CPU/sistema e GPU recebem barras somente com sensor disponível. | Ambas indisponíveis nesta máquina de teste. |
| Ventoinha | Rotação numérica e ícone. | RPM real quando o sistema informa; ícone gira somente quando há medição. | RPM indisponível nesta máquina de teste. |
| Uso geral | Gráfico largo azul e violeta. | Histórico de CPU e RAM em duas curvas, preenchimento discreto e grade. | As curvas são medições, portanto não repetem o desenho da referência. |
| Botão de detalhes | Botão luminoso no rodapé. | Abre o módulo real de Monitoramento e recolhe a vista ampliada. | A navegação segue o fluxo existente do CRONOS. |
| Celular | A referência é um painel isolado, sem tela móvel. | Grade passa a duas colunas; painel rola na vertical e pode ser recolhido. | É uma adaptação responsiva, não uma reprodução em escala. |

O painel ampliado mantém os dados separados da arte. O chip é decorativo, mas anéis, curvas, status, botão e leituras recebem informações do código. A tela só pode ser comparada em proporção e desenho; valores numéricos e gráficos mudam com o computador.
