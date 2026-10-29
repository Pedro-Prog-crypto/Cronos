# Respostas e cronômetro — 29/10/2026

A conversa que já possui texto transcrito agora recebe texto do Gemini por streaming. Antes, a configuração Live podia gerar áudio do Gemini que era descartado, aguardar sua transcrição e só então sintetizar a voz escolhida do Cronos. A nova rota envia a primeira frase validada para a voz durante a geração. O transporte Live continua disponível para entrada de áudio nativo e recuperação compatível antes de qualquer trecho falado.

Saudações completas, incluindo “E aí, Kronos, de boa? Como é que você tá, mano?”, usam a personalidade configurada com contexto menor, sem catálogo de ferramentas nem captura de tela. Cumprimentos seguidos de uma pergunta de conteúdo continuam usando o fluxo completo. Nenhuma resposta fixa substitui o modelo.

A sincronização do mapa de memória não ocupa mais a fila global de conversa. O índice salva cada nota em uma transação curta, e exportações concorrentes recebem exclusão mútua. A conversa aguarda até 150 ms pela atualização de notas externas e depois consulta o índice disponível. Uma atualização em andamento é reutilizada; sincronização explícita e atualização periódica continuam disponíveis. Saudações não reindexam todo o vault.

Chamadas sem uma primeira resposta útil têm um limite de silêncio de oito segundos por tentativa e podem usar as reservas configuradas. Depois da primeira frase, a explicação mantém o orçamento de geração configurado. Não se troca de IA depois que uma fala começou. Falhas de conexão são classificadas como recuperáveis. A recuperação HTTP 503 e os registros de cota continuam funcionando. Nenhuma chave nova é cadastrada automaticamente.

## Cronometrar no aplicativo

O contador aparece acima dos botões inferiores. Ele mostra transcrição, preparação da resposta, preparação da voz e o tempo até a voz começar. Clique nele para abrir **Processamento → Tempo de cada pergunta**. São guardados os últimos 200 registros locais, com os 20 mais recentes exibidos no painel. Há estados de espera, início, conclusão, falha e cancelamento; falhas não contam como respostas instantâneas. Esse registro contém tempos e identificadores, sem o texto da conversa.

Para perguntas por voz, o total até começar a falar inclui a detecção de silêncio e a transcrição. O intervalo de detecção é medido, inclusive no envio manual pelo avião de papel. Eventos atrasados não sobrescrevem os tempos de perguntas mais novas.

## Verificação

`tools/check_conversation_latency_browser.py` exercita a interface compilada, servidor HTTP real, leitor SSE real, AudioWorklet, gravação sintética, transcrição controlada e reprodução WAV no Chromium. Verifica início antes do fim da geração, histórico, cancelamento, recuperação após falha e contabilização da transcrição. Os serviços externos são substituídos por respostas controladas. O resultado não mede o desempenho real de Gemini/Fish nem certifica o microfone físico ou a reprodução no Windows.

`tools/check_image_wall_browser.py` verifica a manutenção do mural de fotos, movimento, carregamento, renovação e fechamento durante a fala. Imagens externas são controladas nesse teste.

A meta é começar a responder em até cinco segundos, preferencialmente antes. Não há garantia universal desse tempo para qualquer pergunta: conexão, cotas, reconhecimento de voz, busca e geração externa podem ultrapassá-lo. O contador mede o resultado real, sem cancelar uma explicação ativa ao chegar a cinco segundos.

## Instalar

Baixe o pacote completo pelo GitHub, extraia em uma pasta permanente e execute `ABRIR-CRONOS.bat`. Para trazer memórias e integrações da instalação antiga, execute primeiro `MIGRAR-DADOS-DA-VERSAO-ANTIGA.bat` na nova pasta. Confira seus dados antes de apagar a origem. O pacote contém o programa completo; credenciais e memórias particulares são copiadas localmente, sem publicação no GitHub.

## Resultado da revisão

655 testes Python passaram em 85,07 segundos, sem falhas. Houve um aviso de depreciação na dependência de testes HTTP. TypeScript e compilação passaram. Os oito cenários de conversa e doze cenários do mural passaram no Chromium. No cenário controlado de texto, o início de áudio foi medido em 280 ms; esse número não mede as APIs reais. Detalhes em `VERIFICACAO-VELOCIDADE-2026-10-29.json`.
