# Notas de conhecimento e tempo de resposta

Gemini Live, SDK, modelos, chave, integração Fish e personalidade permanecem
como estavam na versão que voltou a falar. Esta atualização muda a política de
memória, o índice local e a confirmação operacional de presença.

`Onde-Estao-Memorias.bat` mostra o caminho real de `CRONOS_VAULT`, sem chamar IA.
Se o `.env` mantém `CRONOS_VAULT=./vault`, a pasta é `vault` dentro da instalação:

- `Temas`: um Markdown por assunto, atualizado sem duplicar aliases conhecidos.
- `Memorias`: registros de informações significativas discutidas.
- `Conversas`: histórico para continuidade; não aparece na espiral nem no índice
  de conhecimento. O histórico SQLite continua preservado.

Abra essa pasta principal como vault no Obsidian. A localização exata no Windows
depende da pasta onde o projeto foi instalado ou do caminho definido no `.env`.
O banco interno SQLite fica em `vault/.cronos/memory.sqlite3`; as notas que o
Obsidian usa são os Markdown públicos, não esse arquivo interno.

Saudações, chamadas de presença, testes de áudio e controles da interface não
criam notas de conhecimento, mesmo se a IA sugerir um tema indevido. Perguntas
sobre pessoas, filosofia, notícias, matemática, programação, geografia, pecuária
e outros assuntos relevantes continuam criando temas. Não há lista fechada de
áreas permitidas. Uma saudação seguida de uma pergunta real não é descartada.
Sem temas significativos, não é mais criado um Markdown em `Memorias`.

O grafo exclui o histórico e o índice administrativo `Mapa de Conhecimento.md`.
Notas antigas de chamadas/saudações reconhecidas nos diretórios gerados são
ocultadas do grafo, mas não apagadas do disco. O usuário pode revisar esses
arquivos pelo Obsidian; esta atualização não remove conteúdo existente.

“Cronos, na escuta?” agora recebe confirmação operacional direta pela voz Fish
configurada. Não precisa de geração Gemini nem passa pela gravação de temas.
Não é um novo prompt de personalidade nem uma resposta pronta para perguntas
de conteúdo; essas continuam usando a IA.

Para reduzir trabalho local, arquivos de `Conversas` deixam de ser percorridos
e indexados na busca de conhecimento. No ensaio local com vinte notas e seis
arquivos grandes de histórico, a indexação inicial levou 98,3 ms antes e 5,4 ms
depois. Isso mede somente esse ensaio de indexação, não a latência total de IA,
Fish ou o desempenho do Flash F30.

O backend mede busca de memória, geração, gravação e total, sem salvar o texto,
e guarda apenas os números em `.cronos-local/last-conversation-timing.json`.
`Onde-Estao-Memorias.bat` também mostra essa medição após uma conversa. Ela não
inclui captura/transcrição do microfone ou síntese/reprodução Fish. Permite
investigar a demora sem alterar novamente as integrações que estão funcionando.
