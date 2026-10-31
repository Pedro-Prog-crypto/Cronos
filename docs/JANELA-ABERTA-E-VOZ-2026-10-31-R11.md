# Conversa com a janela aberta — R11

Esta revisão trata da pergunta enviada pelo microfone com o aplicativo já aberto. O acionamento por voz com o aplicativo fechado não é o foco desta correção.

## Causas encontradas e mudanças

- O callback de erro de voz fechava o painel aberto e abria os cards. Um simples aviso de dispositivo de saída também era encaminhado para esse callback, provocando a mesma troca de tela mesmo com áudio disponível. Avisos agora têm um caminho próprio; erros conservam o painel atual.
- A saída padrão exigia uma chamada opcional a `AudioContext.setSinkId`. Algumas versões de WebView expõem essa função sem implementá-la adequadamente. Um contexto novo já usa a saída padrão e não precisa dessa chamada. A seleção de um dispositivo salvo tem espera limitada; um dispositivo desaparecido permite usar a saída padrão com aviso.
- A ativação de Web Audio e o início da reprodução podiam ficar pendentes. Eles agora têm limites próprios, diferentes do tempo de geração da resposta. A espera para terminar um trecho também é limitada de acordo com sua duração, sem impor um corte global de quinze segundos à explicação inteira.
- Se a voz online falhar antes de começar, o Cronos procura uma voz local em português instalada no navegador/Windows e lê **a resposta recebida da IA**, incluindo a continuação. Se a síntese online permanecer sem iniciar por dez segundos e houver voz local, passa para essa reserva. A síntese atrasada não começa outra leitura depois. O timbre da reserva pode ser diferente da voz online escolhida.
- A reserva não inventa uma resposta quando a IA não respondeu, não desativa o volume zero e não reinicia uma fala que já começou. Se não houver voz local, o erro continua explícito; é necessário conferir a saída e as integrações no notebook. O diagnóstico identifica reprodução local como `device`, sem alegar retorno do Fish Audio.
- O aviso de erro tem X e a opção **Ler resposta**. Abrir os cards exige esse clique; a conclusão tardia da IA não apaga uma falha de voz anterior.
- O reconhecimento de pedidos de abrir imagens/arquivos e reposicionar cards foi restringido a pedidos diretos. Relatos, perguntas e negações que apenas mencionem essas ações não devem abrir uma janela. Reclamar que não consegue ver a tela também não é comando para parar o compartilhamento.

## Instalação e conferência

1. Extraia o pacote completo em uma pasta própria.
2. Se suas memórias e chaves estiverem em outra instalação, execute `MIGRAR-DADOS-DA-VERSAO-ANTIGA.bat` uma vez para copiá-las. O pacote público não inclui dados privados.
3. Execute `ABRIR-CRONOS.bat`. Faça uma pergunta pelo microfone com a janela aberta.
4. O painel **Entendimento de linguagem → Entrega da última pergunta** mantém o diagnóstico do caminho de áudio, reconhecimento, IA, síntese e reprodução. **TESTAR IA E VOZ** continua disponível para testar as integrações cadastradas no notebook.

## Limites da verificação

As verificações locais usam a interface compilada, HTTP e reprodução WAV/PCM em Chromium, com microfone sintético, IA/ASR/Fish controlados e uma voz de dispositivo simulada nos cenários de reserva. Dez mil variações de frases verificam o encaminhamento de comandos que abrem janelas; não são dez mil conversas reais nem dez mil testes de alto-falante.

Não foi validado o microfone/alto-falante físico do notebook Windows nem a disponibilidade das APIs da conta. O ambiente de desenvolvimento bloqueou anteriormente o acesso ao Google e ao Fish no proxy, antes de atingir os serviços. Isso não demonstra bloqueio no notebook e impede prometer que toda pergunta real terá voz. Os resultados executados estão em `VERIFICACAO-2026-10-31-R11.json`.

Resultado final local: **686 testes Python passaram em 88,71 segundos, sem falhas** (um aviso de depreciação da dependência de testes). **21 cenários de navegador passaram**, mais três cenários de saída WAV/PCM/volume. TypeScript e compilação passaram. Foram aprovadas 10.000 variações distintas de encaminhamento de comandos e nove regressões específicas de cards/tela. As chamadas de IA, reconhecimento e síntese foram controladas; estes números não certificam disponibilidade das APIs reais ou som físico no Windows.
