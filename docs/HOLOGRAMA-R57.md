# Holograma R57: medição e correção

A referência visual veio dos cinco vídeos enviados. Os 9.920 quadros decodificados estão indexados em [`visual-audit-r57/all-video-frames.csv`](visual-audit-r57/all-video-frames.csv). A leitura fina das curvas usa os 236 quadros frontais consecutivos do vídeo v05, 127–362, alinhados pela grade externa: [`front-orb-every-frame.csv`](visual-audit-r57/front-orb-every-frame.csv). Os outros vídeos mostram sobretudo cards, enquadramentos afastados e painéis que encobrem o anel; há descrição deles em [`ANALISE-VIDEOS-REFERENCIA.md`](ANALISE-VIDEOS-REFERENCIA.md).

## O que aparece nos quadros frontais

| Estado legível | Quadros | LED ciano, pixels medianos | Linhas azuis fracas, pixels medianos | Cor RGB mediana do LED filmado | Espessura aparente mediana |
| --- | ---: | ---: | ---: | --- | ---: |
| FALANDO | 171 | 2.591 | 34.425 | 43, 178, 244 | 4 px |
| EM ESPERA | 7 | 337 | 19.455 | 36, 151, 240 | 2 px |
| OUVINDO | 55 | 766 | 22.767 | 40, 164, 235 | 3 px |

Estas medidas vêm de uma gravação 576 × 1024 de um monitor, com exposição, perspectiva, compressão e recompressão JPEG. A espessura inclui halo e não determina a largura CSS da curva. A cor filmada não é o RGB original do programa. O brilho varia muito durante FALANDO: por exemplo, o detector encontra 6.085 pixels LED no quadro 150, 7.346 no 180 e 543 no 217. Na transição para espera, o ciano cai antes do azul fraco desaparecer. A amostra de espera dura apenas sete quadros. Pequenos máximos luminosos indicam possíveis pontos móveis, mas também podem ser reflexos ou artefatos de filmagem; não foram contados como partículas físicas confirmadas.

A sequência visual no v05 é FALANDO 127–297, transição 298, EM ESPERA 299–305, transição 306–307 e OUVINDO 308–362. A forma continua se movendo nas três fases. O áudio tem correlação fraca com emissão ciana nesse trecho; expandir todo o anel proporcionalmente ao volume não reproduz a referência.

## Alterações no desenho

O anel é calculado no worker por curvas independentes, sem foto ou textura do vídeo. Dezesseis curvas azuis finas formam a camada de trás, com espaços irregulares. Seis curvas na frente variam em espessura; três recebem trechos ciano mais fortes. Brilho localizado e quatro pontos percorrem as próprias curvas. A iluminação da fala usa uma sequência suavizada de intensidades retirada de amostras do trecho frontal. A camada azul permanece nas pausas e na escuta. A troca de estado altera energia e luz gradualmente, sem reiniciar a fase nem espalhar as curvas para fora do anel. Um limite radial mantém os pontos entre 135 e 245 unidades do centro lógico; o teste geométrico percorre 30 unidades de fase em quatro curvas extremas.

O fundo ganhou um gradiente azul mais próximo do monitor visto no vídeo. O LED tem núcleo ciano e halo azul localizado, sem clarear todo o interior. A cor de PENSANDO e do controle de voz segue os estados já implementados na interface; a captura automatizada verifica esses estados visuais, mas não demonstra um ciclo completo com microfone físico.

## Desempenho e verificação

O canvas começa em até 1080 × 1080 pixels. Se nove quadros continuados levam mais de 43 ms cada, reduz o bitmap por etapas: 900, 720 e 600. As curvas mantêm as mesmas posições e proporções. Em Chromium por software neste ambiente, o canvas a 1080 aproximava-se de 10 quadros/s; após a redução, uma amostra de três segundos mediu 27,3 quadros/s a 600. O cálculo das curvas levou em média cerca de 2 ms/quadro; a apresentação do canvas era o gargalo. Em uma máquina rápida, o canvas pode permanecer em 1080. A redução melhora fluidez, mas diminui a nitidez em máquinas lentas. Não há medição no notebook Windows do usuário.

`npm run lint`, os testes de movimento e geometria, a compilação e a inspeção em navegador da interface passaram. As capturas dos três estados e do layout estão em [`visual-audit-r57/`](visual-audit-r57/). Esta revisão responde aos defeitos observados, mas uma filmagem do original não permite certificar igualdade de cada pixel, partícula ou quadro do algoritmo desconhecido.
