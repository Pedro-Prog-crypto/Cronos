# Controle de requisições Gemini

Foi encontrada uma falha no controle de pausa: o HTTP 429 suspendia tentativas
somente no processo atual. Fechar/reabrir o Kronos ou executar o diagnóstico em
outro processo perdia essa proteção. Agora a pausa é salva localmente por chave
e modelo (usando hash, sem salvar a chave) e verificada antes da requisição.
Isso evita novas tentativas durante a pausa; não recupera cota já consumida nem
garante renovação ao final do intervalo.

`Diagnosticar-Cronos.bat` agora apenas lê configuração, último erro e contagens
locais. Não gera texto nem afirma que a conexão está funcionando. Para uma geração
explicitamente solicitada, use `.venv\Scripts\python.exe -m cronos.diagnostics --generate`
na pasta do projeto. Essa opção continua consumindo uma requisição;
uma falha 404 pode consultar a lista de modelos sem gerar outra resposta.

Cada tentativa HTTP de geração é registrada em
`.cronos-local/gemini-requests.jsonl`: horário, origem, modelo, identificador
aleatório do turno, status, quantidade de caracteres de texto enviados e contagens
de tokens quando o Google as fornecer. Não contém chave, pergunta, personalidade,
resposta, imagem ou corpo bruto do erro. Não é um extrato de faturamento: não mede
o uso de outros aplicativos/contas e não reconstrói chamadas anteriores à atualização.
HTTP 0 significa falha de transporte sem resposta HTTP. O arquivo gira ao atingir
1 MiB, mantendo um arquivo anterior; contagens do diagnóstico abrangem esses dois
arquivos para o modelo atual. A origem pode ser conversa, diagnóstico, verificação
manual de módulo, visão, planejamento ou consulta a outros modelos.

As consultas periódicas de status, monitor, módulos e sincronização de memória
não chamam Gemini. Perguntas sem ferramentas precisam de uma geração. Ferramentas
podem exigir gerações adicionais para interpretar seus resultados, agrupadas pelo
mesmo identificador de turno. Um HTTP 503 pode ter uma segunda tentativa; ela
também aparece no registro. Não há repetição automática após HTTP 429. A voz Fish
e seu modelo permanecem separados desse controle.

Validação: testes com transporte simulado confirmam uma chamada seguida de
bloqueio após perder a memória do processo; diagnóstico local sem criar provedor;
metadados sem conteúdo privado; zero gerações nas consultas de abertura e uma
geração por pergunta simples. A renovação da cota real no Windows não foi testada.

Atualize o código na mesma pasta de instalação, preserve `.env` e vault e reabra
o Kronos. Não apague os arquivos de pausa para contornar o bloqueio: isso apenas
permite repetir uma chamada que pode ser novamente recusada.
