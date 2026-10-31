# Reconhecer antes de responder — R9

A revisão anterior usava limites curtos demais para reconhecimento: cinco segundos no primeiro serviço quando havia reserva, seis na reserva e doze no navegador. Um serviço que precisava de mais tempo podia ser interrompido sem devolver a pergunta. A síntese também tinha um limite de oito segundos. A meta de começar rápido não deve virar cancelamento de uma resposta válida.

## Mudança no reconhecimento

O reconhecimento principal começa imediatamente. Se não terminar em dois segundos e houver Gemini configurado no modo online, a alternativa começa com a mesma gravação **sem cancelar o primeiro reconhecimento**. O primeiro texto não vazio e válido é usado uma única vez para iniciar a conversa. Se a alternativa falhar, o principal pode continuar e concluir. Quando um deles vence, as tarefas restantes são canceladas e seus recursos são liberados.

O principal e a alternativa têm até trinta segundos por operação, com quarenta segundos para a recuperação completa no servidor e cinquenta e cinco no navegador, incluindo envio e recebimento. São tetos para falhas, não esperas obrigatórias: um reconhecimento saudável que termina imediatamente é entregue imediatamente e não chama a reserva. A gravação continua disponível no botão Reenviar gravação se nenhum serviço conseguir reconhecer.

Depois do reconhecimento, o texto segue para a IA e a resposta segue para a síntese. A síntese completa tem até trinta segundos no servidor e quarenta no navegador, incluindo até duas tentativas recuperáveis. Esses limites substituem os cortes de oito/dez segundos que podiam impedir a voz de sair. Não alteram a duração de uma explicação já em reprodução.

O modo local continua sem enviar áudio aos serviços online. A função usa somente integrações já configuradas. Isso não garante disponibilidade, crédito ou precisão dos serviços reais; os erros não são transformados em perguntas inventadas.

## Verificação

Há testes de concorrência que verificam: principal rápido não chama reserva; reserva que falha não cancela o principal; reconhecimento válido da reserva vence uma única vez; cancelamento libera ambos os serviços. Os testes anteriores de gravação preservada e passagem da pergunta reconhecida à resposta continuam disponíveis.

O teste do Chromium inclui espera real controlada de **13,2 segundos no reconhecimento**, seguida de envio da pergunta e reprodução de resposta, sem falha no antigo limite de doze segundos. Também inclui **9,2 segundos na síntese**, que termina com áudio em vez de falhar no antigo limite de oito segundos. As esperas são simuladas nos serviços, mas o relógio, a interface compilada, a captura sintética, o servidor HTTP e a reprodução WAV são exercitados. Isso não certifica microfone físico ou velocidade das APIs reais.

## Instalar

Baixe o pacote completo, extraia, copie suas memórias e integrações usando `MIGRAR-DADOS-DA-VERSAO-ANTIGA.bat` e abra `ABRIR-CRONOS.bat`. Mantenha a origem até conferir seus dados. Arquivos privados não são publicados no GitHub.

Resultado final: 674 testes Python passaram em 87,12 segundos, sem falhas; houve um aviso de depreciação da dependência de testes HTTP. Os quatorze cenários de navegador passaram. TypeScript e compilação passaram. Os resultados estão em `VERIFICACAO-2026-10-30-R9.json`.
