# Cronos R36 — reservas reais e respostas

Esta atualização mantém o Studio, seus projetos e as integrações já cadastradas.

## O que mudou

- Cada novo pedido de criação no Studio tenta uma fila fixa: a IA de código escolhida e, se ela falhar, as outras IAs de código configuradas. Uma falha anterior não esvazia a fila da próxima tentativa. O andamento mostra a solicitação feita a cada integração e o resultado da verificação. Gemini continua reservado à revisão visual do site.
- O gerador recebe a instrução de omitir do site dados comerciais não confirmados e informar as pendências no resumo. Isso evita colocar “conteúdo pendente” na prévia, texto que a própria revisão recusava.
- Perguntas comuns procuram uma resposta em uma IA por vez, com as outras integrações configuradas como reservas. O conselho simultâneo de IAs continua disponível quando pedido explicitamente. Perguntas longas continuam sendo enviadas integralmente ao provedor; se a conta ou o modelo rejeitar o tamanho, a próxima integração disponível pode responder.
- Saudações têm limite curto para obter resposta. Se o navegador entregar uma transcrição final completa sem informar confiança, o Cronos pode usar esse texto sem esperar uma segunda transcrição na nuvem. Trechos de uma só palavra e transcrições com baixa confiança informada continuam sem substituir a gravação.

## Como conferir

Abra um projeto do Studio e peça uma nova criação. A tela de andamento mostra a fila e as integrações realmente tentadas. Se todas falharem por chave inválida, limite de uso ou falta de serviço, a última versão permanece salva e é preciso regularizar ao menos uma integração para criar com IA.

No Cronos, pergunte “Você está me escutando?” e depois uma pergunta longa. Uma resposta de presença recebida em texto não depende do conselho de IAs. A resposta de uma pergunta real depende da conexão e da conta do provedor que responder.

Os testes automatizados usam integrações e microfone simulados. Eles verificam a lógica de seleção, a preservação de perguntas longas e o pacote, mas não medem a velocidade ou o microfone do notebook do usuário nem comprovam que uma chave externa tem cota. Nenhuma atualização pode prometer tempo fixo para uma API externa ou tornar válida uma chave recusada pelo provedor.
