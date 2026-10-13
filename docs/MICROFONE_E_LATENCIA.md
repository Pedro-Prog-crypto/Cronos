# Microfone e início da voz

Correções após o relato de cliques sem indicação, animações travando e atraso da
voz. Nenhuma chave, ID de voz ou modelo Fish/Gemini foi alterado.

## Comportamento atual

Atualização posterior: [escuta contínua e mapa](ESCUTA_CONTINUA.md). O microfone
agora abre automaticamente e permanece habilitado entre frases até desligamento
manual; `aria-pressed` indica essa habilitação, mesmo durante a resposta.

- O botão existente indica a abertura antes da resolução de getUserMedia. Borda
  ciano intensa significa gravando; borda âmbar pulsante indica trabalho em
  andamento. O título do botão diferencia abertura, transcrição, espera pelo
  Gemini e preparação da voz. aria-pressed reflete gravação real, não simulada.
- Ao começar a gravar, composer e cards anteriores ficam ocultos imediatamente.
  Conversas faladas não exibem caixas automáticas de pergunta/transcrição/resposta.
  Comandos mostrar texto ou mostrar resposta exibem o último turno guardado na
  interface; perguntas por texto continuam usando os cards. Histórico permanece.
- Núcleo e estrela desenham em OffscreenCanvas, cada qual com seu worker. A thread
  da interface recebe apenas estado, amplitude e visibilidade; o áudio e as chaves
  não são enviados aos workers. Fios, brilho e movimentos existentes permanecem.
- Existe fallback para o mesmo desenho na thread principal em WebView2 sem suporte
  ou em falha do worker. Isso preserva funcionamento, mas perde o benefício de
  separar desenho e controles. Workers e timers são encerrados no unmount.
- A voz divide o texto real em um primeiro trecho de até 220 caracteres e demais
  trechos de até 360, preferindo frases/palavras. Usa o mesmo endpoint/configuração.
  Toca assim que o primeiro áudio chega e prepara apenas um próximo trecho durante
  a reprodução. Não sintetiza a resposta inteira antes de começar a falar.
- Ordem e texto completo são preservados; há no máximo um trecho em antecipação.
  Parar cancela a fila e evita que um áudio pendente volte a tocar. Podem ocorrer
  pequenas pausas entre trechos conforme a velocidade do provedor.

A mudança não elimina o tempo de geração do Gemini: a resposta estruturada ainda
é concluída antes da síntese. Não foi adivinhado outro modelo nem feita uma troca
silenciosa de plano ou voz para obter velocidade.

## Evidência

TypeScript/build e 127 testes Python passaram. Browser verificou dois workers
ativos, canvas mudando, abertura/ativação do microfone, ausência de caixas durante
fala, início do primeiro áudio antes da conclusão atrasada do seguinte, sequência
completa, comando explícito de mostrar resposta, cancelamento da continuação e
ocultação dos cards anteriores ao ativar o microfone. Verificou também desenho
com Worker/OffscreenCanvas desativados. Entrada e provedores foram simulados. A validação inicial reproduziu WAV Fish
recebido anteriormente; o teste reutilizável usa tom sintético apenas como fixture
de áudio, sem chamadas Fish/Gemini nem troca da voz de produção.

Em Chromium 1366x768 com CPU desacelerada em 4x, a thread principal usou cerca de
1,3–1,7 segundos de tarefas numa janela de três segundos com as animações ativas.
Esse resultado não mede consumo total dos workers, RAM ou desempenho físico do
Samsung Flash F30. Latência real de Gemini/Fish e microfone no Windows continuam
pendentes de validação no computador do usuário.

Atualização exige o build completo, incluindo o novo arquivo scene.worker-*.js.
Preserve .env e vault, feche a janela anterior, atualize a mesma pasta usada para
abrir o programa e execute Iniciar-Cronos.bat novamente. Não precisa reimportar a
voz que já está funcionando.

Teste de navegador reutilizável: frontend/scripts/check-voice-flow.py. Requer
Playwright e Chromium para desenvolvimento; execute pelo Python do ambiente de
testes. CRONOS_TEST_CHROMIUM pode indicar o executável. Não é necessário instalar
essas ferramentas para usar o Kronos no Windows.
