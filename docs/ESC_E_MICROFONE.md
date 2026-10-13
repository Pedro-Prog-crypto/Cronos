# ESC, captura e perguntas

ESC interrompe a fala corrente, cancela os trechos de áudio em preparação e a
solicitação de conversa pendente. Uma resposta atrasada não pode reiniciar a voz.
O microfone permanece habilitado; a captura/transcrição em curso é descartada.
ESC também é encaminhado quando o foco está dentro do mapa ou da bancada de
módulos. Ações já executadas e notas já gravadas não são desfeitas pela tecla.

O backend observa a desconexão do pedido e cancela a geração pendente, liberando
a fila de conversa. Isso não garante devolução de cota de uma chamada que já foi
enviada ao provedor. Gemini Live, modelos, chaves e modelo/voz Fish foram mantidos.

A captura PCM usa limiar adaptado ao ruído, detecção mais sensível para voz baixa,
350 ms de pré-gravação e rejeição de estalos muito curtos. A espera de silêncio
passou de 1,4 s para cerca de 0,75 s. Há uma pequena proteção de 250 ms depois da
voz para reduzir eco, em vez dos 650 ms anteriores. Pausas maiores que 0,75 s
podem terminar uma frase; velocidade e tolerância a pausas têm esse compromisso.
O fallback MediaRecorder usa o mesmo intervalo de silêncio. Continua sendo usado
o microfone padrão do Windows com pedido de canal mono e processamento de eco,
ruído e ganho automático do navegador, quando suportados pelo dispositivo.

O modelo Vosk existente é preparado em segundo plano na abertura e reutilizado;
não foi baixado um modelo maior nem trocada a API de voz. Transcrições vazias ou
com baixa confiança média pedem repetição em vez de enviar uma frase duvidosa à
IA. Isso não certifica reconhecimento perfeito, principalmente de nomes próprios.

Uma pergunta relevante concluída, como “Quem foi Sócrates?”, agora cria um
Markdown em `Memorias` mesmo se o modelo omitir a lista `topics`. Quando fornece
temas, eles continuam indo para `Temas` com ligações. O fallback guarda pergunta
e resposta, sem inventar uma classificação temática. Chamadas de presença e
saudações continuam fora da memória de conhecimento.

O tempo para iniciar uma resposta ainda inclui detecção de fim da frase,
transcrição, geração Gemini e síntese do primeiro trecho Fish. Reduzir o silêncio
não torna toda essa sequência instantânea. A medição local de backend continua
disponível em `Onde-Estao-Memorias.bat`.

Validação: testes de PCM com voz baixa, ruído, estalos, pausa curta e descarte;
testes de cancelamento de geração, reconhecimento incerto e memória sem topics;
teste de navegador com voz/entrada simuladas verifica ESC durante fala, resposta
atrasada, próxima pergunta e foco no mapa. No mesmo teste, workers de animação
permanecem ativos e o fallback de desenho funciona. Microfone físico, nomes
próprios, latência dos provedores e fluidez no Flash F30 ainda precisam de
validação no aparelho.

Atualize os arquivos na mesma instalação, incluindo `cronos/ui` completo, preserve
`.env` e `vault`, feche a janela anterior e abra `Iniciar-Cronos.vbs`.
