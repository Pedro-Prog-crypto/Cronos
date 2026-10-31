# Conferir a entrega na instalação real — R10

O usuário confirmou que o problema ocorre com a janela aberta e seu microfone em uso. Esta revisão distingue uma saudação de ativação local de uma resposta obtida da IA. Ela não declara que as APIs da conta do usuário responderam: a tentativa de acesso real no ambiente de desenvolvimento foi bloqueada pelo proxy antes de chegar ao Google e ao Fish Audio (ProxyError/403). Isso não comprova bloqueio no notebook.

## Mudanças

- Cada pergunta recebe um identificador que acompanha áudio recebido, reconhecimento, entrega do texto à conversa, pedido à IA, resposta recebida, pedido de síntese, áudio retornado e início da reprodução. Os registros são confirmações de etapas reais, não progresso estimado.
- O registro guarda somente etapas, tempos, quantidades de bytes/caracteres, provedor e categorias de erro. Não armazena áudio, perguntas, respostas, chaves ou cabeçalhos de autenticação. Há até quarenta solicitações em memória; o painel mostra as dez mais recentes. Reiniciar o servidor descarta os registros.
- No painel **Entendimento de linguagem**, **TESTAR IA E VOZ** faz uma pergunta aritmética nova pela integração configurada. Uma saudação pronta não passa: a resposta precisa corresponder ao cálculo. O texto recebido segue para o Fish Audio e o áudio retornado fica disponível no reprodutor. O teste não escreve uma conversa na memória pessoal nem executa ferramentas.
- Esse teste tem orçamento de 25 segundos para IA e síntese. A conversa normal conserva os limites de recuperação separados, evitando voltar a cortar uma pergunta válida para cumprir uma meta artificial. A meta visível de início da voz foi atualizada para 25 segundos; não é garantia de disponibilidade dos serviços externos.
- O microfone é suspenso durante a reprodução do teste para não reconhecer o próprio áudio e é restaurado ao terminar.
- **COPIAR DIAGNÓSTICO** permite compartilhar o relatório sem compartilhar as chaves. Se o WebView não liberar a área de transferência, o relatório aparece em um campo selecionável para copiar manualmente.
- A janela informa ao ouvinte local quando seu microfone já está ativo. Nessa situação, o ouvinte continua podendo restaurar a janela, mas não reproduz outra saudação sobre a pergunta. Um ouvinte antigo ativo é atualizado; uma janela que não usa o microfone não desativa a saudação. O aviso expira automaticamente se a janela parar de informar seu estado.

## Como conferir no notebook

1. Instale o pacote completo atualizado. Se for usar outra pasta, copie as memórias e integrações com `MIGRAR-DADOS-DA-VERSAO-ANTIGA.bat` e depois execute `ABRIR-CRONOS.bat`.
2. Abra **Entendimento de linguagem → TESTAR IA E VOZ**. O teste usará as integrações cadastradas e oferecerá o áudio da resposta. Ouvir a saudação de ativação, por si só, não conta como sucesso.
3. Faça uma pergunta pelo microfone e volte a **Entrega da última pergunta**. Confira a última etapa confirmada. Sem `Áudio chegou ao servidor`, a entrada não foi confirmada pelo backend. Sem `Pergunta reconhecida`, a conversa ainda não recebeu texto utilizável. Uma resposta recebida sem áudio aponta para a etapa de síntese; áudio recebido sem reprodução aponta para o player/dispositivo.
4. Se falhar, use **COPIAR DIAGNÓSTICO** e compartilhe somente esse relatório. Não envie `.env`, chaves ou o vault para diagnosticar a conexão.

## Verificação

Os testes locais exercitam os mesmos endpoints e a mesma interface compilada, com serviços externos controlados. Eles verificam a correlação da captura até o áudio, rejeição da saudação como resposta de teste, limites dos registros, ausência de dados privados, proteção contra saudação concorrente e cópia em WebView sem clipboard. Os testes controlados não substituem o teste real na conta do usuário e no dispositivo físico do Windows.

Resultado local: 681 testes Python passaram em 86,90 segundos, sem falhas; houve um aviso de depreciação da dependência HTTP de testes. TypeScript e compilação passaram. Os dezessete cenários de navegador passaram com serviços controlados, incluindo reprodução do teste e cópia sem clipboard. As APIs reais permaneceram inacessíveis a partir deste ambiente, inclusive após uma nova tentativa de rede autorizada. Consulte `VERIFICACAO-2026-10-30-R10.json`.

A recepção de uma gravação sem sinal de voz é registrada separadamente: ela confirma os bytes recebidos e uma falha de validação, sem alegar que o arquivo nunca chegou ou chamar a IA com uma pergunta inventada.
