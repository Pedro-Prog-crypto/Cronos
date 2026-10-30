# Entrega da pergunta e da resposta — R8

Esta revisão acompanha o caminho gravação → transcrição → conversa → síntese → reprodução, em vez de apenas reduzir prazos. Não foi possível observar a instalação do usuário; os defeitos encontrados no código e os testes controlados não comprovam a causa específica de cada falha no notebook.

## O que mudou

- O modo de áudio direto mantinha o indicador “Transcrevendo” até a conversa inteira terminar. Agora ele sai desse estado quando entrega o áudio à conversa. Uma transcrição real recebida confirma o reconhecimento; o marcador “Pergunta por voz” não é tratado como pergunta reconhecida.
- O reconhecimento normal e a recuperação do áudio nativo usam a mesma rotina. Quando o Fish falha ou retorna texto vazio, a mesma gravação pode ser transcrita pelo Gemini já configurado. O orçamento do primeiro reconhecimento é cinco segundos quando há essa alternativa; a alternativa tem seis segundos. Não há uso de conta nova, chave embutida, histórico como substituto da fala ou resposta inventada para preencher uma transcrição vazia.
- O Gemini recebe o áudio efetivo e instruções para somente transcrever. Respostas vazias, inválidas ou cortadas por limite de saída são rejeitadas; não viram perguntas fabricadas. Modos locais não enviam áudio para serviços online.
- Se o reconhecimento continuar falhando, o botão **Reenviar gravação** tenta novamente a mesma gravação, sem exigir que o senhor repita a pergunta. Há apenas uma gravação temporária na memória do aplicativo; ela é substituída por uma nova gravação e liberada após o reconhecimento confirmado. Fechar o aplicativo a descarta. Esse recurso não grava cópias permanentes no disco.
- Se o áudio nativo já forneceu a pergunta e a geração da resposta falhar, a recuperação reutiliza esse texto, sem passar o áudio por reconhecimento novamente. O campo de nova tentativa conserva a pergunta real, em vez do marcador “Pergunta por voz”.
- Uma pergunta já transcrita que encontre outra solicitação em andamento fica guardada no campo, com aviso. Antes esse caminho podia retornar sem dar uma explicação ao usuário.
- O estado interno de montagem do microfone é restaurado ao remontar a interface, evitando descartar os resultados em ciclos de remontagem do React.

## Verificação

O teste no Chromium usa a interface compilada, AudioWorklet, gravação sintética, API local real, SSE e áudio WAV. Serviços de IA, reconhecimento e síntese são controlados. São doze cenários; os novos conferem reenvio dos mesmos bytes após falha, entrega do texto reconhecido à IA, entrega da resposta à síntese e saída correta do estado de transcrição no áudio nativo. A fala começa antes de a resposta e os metadados terminarem de chegar.

Os testes de backend verificam recuperação com o mesmo áudio, reconhecimento principal vazio, alternativa inválida ou incompleta e bloqueio de envio online no modo local. Os testes não certificam precisão de transcrição real, disponibilidade de cota ou desempenho no microfone físico do Windows. Os prazos de recuperação não são uma garantia universal de resposta em cinco segundos.

## Atualizar

Baixe o pacote completo, extraia para uma pasta permanente e use `MIGRAR-DADOS-DA-VERSAO-ANTIGA.bat` para trazer memórias e integrações. Depois execute `ABRIR-CRONOS.bat`. Mantenha a pasta de origem até conferir seus dados. As chaves privadas e memórias são copiadas localmente; não são publicadas no GitHub.

Resultado final: 670 testes Python passaram em 93,86 segundos, sem falhas. Houve um aviso de depreciação na dependência de testes HTTP. TypeScript, compilação e os doze cenários de conversa no Chromium passaram. O relatório está em `VERIFICACAO-2026-10-29-R8.json`.
