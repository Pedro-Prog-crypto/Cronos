# Cronos R37 — transcrição durante a fala

O microfone passa a produzir texto parcial enquanto capta a voz. Quando a fala termina, a transcrição final confirmada segue como texto para a resposta; o áudio não precisa ser transcrito novamente nesse caminho.

O navegador continua sendo a primeira opção para legendas ao vivo. Se o WebView não entregar palavras em 1,5 segundo, o Cronos tenta um fluxo local de PCM com o modelo português Vosk já instalado. O áudio é enviado em blocos para o próprio servidor do Cronos no computador, e a tela recebe as hipóteses parciais. A conexão exige a sessão local, aceita somente a origem autorizada e tem limites de duração e volume. Também funciona no caminho de gravação usado quando AudioWorklet não está disponível.

O ditado longo agora aproveita a transcrição final de cada trecho. Antes, ela era descartada e cada gravação seguia para outra transcrição após o envio. O botão Enviar continua finalizando a captura; a detecção automática de silêncio continua disponível.

Se navegador e modelo local não concluírem uma transcrição válida, a gravação preservada ainda pode passar pelo reconhecimento anterior ou ser reenviada. O modelo português local precisa estar instalado para essa segunda opção ao vivo; a atualização de código não baixa o modelo sem aviso nem garante reconhecimento para todo ruído ou microfone. Os testes desta revisão simulam o dispositivo e o reconhecimento. Confirme o resultado com o microfone do notebook após instalar.
