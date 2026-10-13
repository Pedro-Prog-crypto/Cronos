# Cards holográficos

Implementação baseada nas quatro imagens enviadas pelo usuário: compacto de
cantos arredondados, vertical recortado, resposta em camadas e faixa horizontal
com ícone. Paleta ciano/rosa, fundo escuro translúcido, bordas luminosas, rastros
laterais e camada posterior com perspectiva. É uma aproximação renderizada em
CSS, não uma promessa de igualdade pixel a pixel ou geometria 3D volumétrica.

## Comportamento

- Pergunta por texto na faixa horizontal; resposta nos cards laterais.
  Em conversas faladas, cards ficam ocultos até o comando mostrar texto/resposta.
- Altura automática e largura conforme quantidade de texto e formato. Não há
  alça ou botão de redimensionamento. A área externa rola quando necessário.
- Títulos Markdown e listas/parágrafos reconhecidos distribuem o texto real em
  cards. Não há nova chamada à IA para montar cards; resumos de memória não são
  usados como substitutos da resposta. Limite de oito elementos por resposta:
  conteúdo restante é reunido no último, sem truncamento.
- Distribuição variada, estável durante leitura; não muda de posição a cada
  atualização do áudio. A cena mostra o turno atual, e o histórico continua
  persistido pelo backend. A cópia redundante crescente de mensagens em React
  foi removida junto com a antiga caixa de conversa.
- O ícone de Entendimento de linguagem ou comando abrir painel abre o card de
  pergunta por texto. Ele fecha ao enviar. Perguntas faladas não abrem composer.
- Escape ou comando abrir memória limpa os cards da cena; não apaga histórico.
- As aprovações de ferramentas continuam disponíveis, no mesmo estilo visual.
- Painéis dos módulos receberam o tema ciano/rosa; ações existentes foram
  preservadas, sem novos controles de configuração, token ou redimensionamento.

## Verificação

TypeScript e build passaram; 127 testes Python passaram. Browser verificou
resposta curta, resposta longa com trecho final preservado, três tópicos em
formatos distintos, doze tópicos reunidos em oito cards sem perda do último,
entrada por texto, largura em 390px, escape de HTML e ausência da caixa antiga.
Outro teste verificou transcrição/IA simuladas, resposta automática, reprodução
de WAV recebido anteriormente, comandos locais e mapa/liberação ao fechar.
Esses testes não comprovam microfone físico, API ao vivo ou fluidez no Windows.

A captura entregue é do build real com resposta de Sócrates fornecida pelo teste,
não uma imagem gerada nem prova de resposta do Gemini nesta tarefa. Efeitos de
entrada terminam em menos de um segundo. Nenhum loop de partículas foi acrescentado
aos cards; o medidor de áudio continua fora das renderizações React.

Com três cards visíveis, medição local Chromium 1920x1080 sem desaceleração
observou 88 quadros em três segundos e intervalo mediano de 33,3 ms no núcleo.
Não é medição do Samsung Flash F30.
