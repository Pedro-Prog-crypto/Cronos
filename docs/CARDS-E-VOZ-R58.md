# Cards e voz R58

A tela inicial continua só com o holograma e o botão de voz. A iluminação azul do fundo foi reduzida para uma região próxima do anel; o restante do HUD permanece escuro. Durante a captura, a transcrição provisória aparece no alto à esquerda. O botão circular da onda mantém o mesmo ícone; um botão de envio com avião aparece à sua direita quando há fala capturada e pronta para enviar.

## Notícias do dia

O comando “Cronos, notícias do dia” usa a ferramenta `web_news` existente. Ela busca manchetes recentes, preserva URL, fonte, data e, quando fornecida pela busca, imagem. A busca envia seus resultados à interface antes de a resposta do modelo terminar. Nenhum texto de notícia é criado para preencher o card: se a busca falhar, a interface informa que não há manchetes verificadas. Os cards aparecem em sequência no centro, os anteriores se reduzem para a faixa inferior e, ao fim da fala, passam à visão geral. A pessoa também pode avançar manualmente. A fonte abre apenas quando o botão “Abrir fonte” é acionado.

A disposição segue a análise do vídeo v01: foco central; histórico progressivo embaixo; visão geral após a apresentação. Os cards principais passaram a ter larguras e alturas próprias para briefing, clima, agenda, e-mail e notícias, como as proporções diferentes observadas na gravação. Há imagens e textos diferentes a cada dia, por isso a duração de cada notícia acompanha os trechos de áudio disponíveis, sem repetir os tempos fixos da gravação. Quando a resposta é lida em poucos trechos, os cards restantes aparecem juntos ao fim. O texto integral da resposta fica no painel lateral, com rolagem e botão de fechar. Em telas estreitas ele muda para uma faixa compacta inferior.

O ícone de alfinete fixa um card. Comandos como “mantenha card 1 e card 2”, “mantenha este card” e “desfixe card 2” atuam sobre o deck aberto. Cards fixados continuam visíveis no histórico compacto e recebem uma borda destacada. O comando precisa identificar um card existente; o Cronos avisa quando não encontra o alvo.

## Tempo de resposta e transcrição

Na consulta explícita de notícias, a busca tinha teto de 8 segundos e o modelo mais 15, sequencialmente. Os tetos agora são 5 e 4 segundos. Se o modelo exceder o limite, o Cronos usa apenas manchetes e links realmente devolvidos pela busca. Para falas de até 12 segundos, o teto do reconhecimento caiu de 40 para 25 segundos; falas longas preservam prazo maior. A pausa automática de uma frase curta foi reduzida de 1,4 para 1,05 segundo. O botão de envio permite encerrar a frase sem esperar a detecção de silêncio. Esses valores limitam demoras; não garantem resposta em um número fixo de segundos, pois rede, reconhecimento e síntese de voz ainda dependem dos serviços configurados.

Nas perguntas gerais, se o provedor principal não produzir a primeira saída, uma reserva já configurada pode começar após 4 segundos em vez de 8. Uma resposta que já começou continua no provedor escolhido; a reserva não executa ferramentas nem grava memória se perder a corrida.

O reconhecimento provisório já começa durante a captura por navegador ou serviço local de fala, quando disponível. Agora a interface mostra a área de transcrição desde o início da fala, inclusive durante a confirmação final. A transcrição provisória pode mudar antes de ser confirmada. Sem reconhecedor progressivo disponível, a área mostra “Ouvindo…” até a transcrição do áudio gravado chegar.

## Verificações

A interface passou na compilação TypeScript, nos testes de navegação, comandos dos cards, notícias, captura de tela desktop/tablet/mobile e em 39 testes de backend de notícias e recuperação da transcrição. Os testes do atualizador verificam preservação dos arquivos de dados. A prévia dos cards foi inspecionada em Chromium. A busca, as chaves pessoais, o microfone físico e o tempo real de voz ainda precisam ser verificados na instalação Windows do usuário; esta análise não afirma igualdade pixel a pixel com uma gravação de monitor.
