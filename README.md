# Cronos — assistente Windows (v0.5)

Programa Windows com backend independente da interface. A versão anterior
foi analisada como referência de arquitetura; sua interface, imagens, avatar e
prompts rígidos não foram incorporados. A interface holográfica fornecida pelo usuário agora é a janela principal, com
animações e controles conectados ao backend. A bancada anterior continua em `/tests`.
Veja [a integração e atualização Windows](docs/INTERFACE_HOLOGRAFICA.md).

Leia [a análise do pacote antigo](docs/ANALISE_LEGADO.md), o
[contrato da API](docs/API.md) e o [inventário completo](docs/legacy-inventory.json).

## Instalação Windows

1. Extraia o ZIP inteiro numa pasta gravável.
2. Abra `Instalar-Cronos.bat`. Ele instala backend, janela desktop, busca, imagens e dependências do ouvinte local.
3. Configure `.env` no Bloco de Notas, sem compartilhar suas chaves.
4. Abra `Iniciar-Cronos.vbs`. Ele abre uma janela própria sem prompt. O `.bat` continua disponível como alternativa.

Python 3.11+ e Microsoft Edge WebView2 Runtime são necessários. O aplicativo
continua dependendo de Python; ainda não é um instalador `.exe` independente.
O inicializador escolhe uma porta livre no loopback, gera um token temporário
se necessário e conecta a janela automaticamente. Fechá-la encerra seu backend.
O microfone na janela desktop ainda precisa de validação no Windows; o upload
de áudio pode ser usado como alternativa. O ouvinte em segundo plano só é ativado explicitamente no módulo Dispositivos; permanece separado da conversa.

Ao atualizar, preserve `.env`, `config/providers.json` e o vault. Instale novamente
as dependências pelo BAT. A memória da primeira versão é importada automaticamente,
sem apagar os JSON e Markdown originais.

Comandos equivalentes na pasta que contém `pyproject.toml`:

```bat
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[desktop,search,wake]"
.\.venv\Scripts\python.exe -m cronos.desktop
```

Em CMD, crie `.env` com `copy .env.example .env`. Em PowerShell, use
`Copy-Item .env.example .env`. Não substitua um `.env` que já contém suas chaves.

## Personalidade e raciocínio

Edite `modelos/personalidades/cronos.md`, relido a cada mensagem. A personalidade
não fica presa ao provedor. Não há bordões obrigatórios, limite de dez frases,
uma linha por tarefa ou troca de voz por palavras-chave. O modelo escolhe o
plano com base no pedido e nas ferramentas realmente disponíveis.

A qualidade depende do modelo usado e das informações recuperadas. A arquitetura
não cria inteligência ilimitada nem contorna limites das APIs. Opiniões de
várias IAs são análises independentes, não prova de verdade por votação.

## Obsidian

Configure `CRONOS_VAULT` com o caminho de um vault existente ou novo, por exemplo
`C:/Users/SEU_USUARIO/Documents/Cronos`. Se Documentos estiver no OneDrive, use o
caminho real. Abra essa pasta no Obsidian; nenhum plugin REST é necessário.

- `Conversas/`: histórico legível por conversa.
- `Temas/`: notas criadas conforme surgem assuntos, com aliases e links de origem.
- `Mapa de Conhecimento.md`: índice dos temas realmente registrados.
- `.cronos/memory.sqlite3`: histórico e fila transacional de exportação Markdown.

Não há descarte automático de memórias antigas nem truncamento do conteúdo salvo.
Os orçamentos `CRONOS_CONTEXT_MESSAGES`, `CRONOS_CONTEXT_CHARS`,
`CRONOS_MEMORY_CHARS` e `CRONOS_MEMORY_RESULTS` limitam o contexto enviado ao
modelo, sem apagar dados. O limite prático de armazenamento é o disco disponível.
`CRONOS_OUTPUT_TOKENS` e `CRONOS_PROVIDER_TIMEOUT` ajustam saída e timeout dos
provedores nativos; sem limite de saída configurado, valem os limites do modelo.

A busca FTS5 usa conteúdo e títulos de todos os Markdown públicos do vault, sem
sensibilidade a acentos. Edições feitas no Obsidian são reindexadas. É busca
textual com ranking, não busca semântica por embeddings. Aliases são propostos
pelo modelo e podem exigir correção humana; homônimos continuam ambíguos.

Notas existentes são reaproveitadas pelo título/alias, preservando seu texto.
As novas seções são identificadas como resumos de IA não verificados. Exportações
pendentes são recuperadas após reinício ou por `/memory/sync`, com marcadores
para evitar duplicação. Use apenas uma instância/worker por vault. Evite editar
uma mesma nota enquanto ela está sendo exportada; não existe bloqueio distribuído
com o editor Obsidian. Links simbólicos são rejeitados para proteger o escopo.

Na nuvem, o vault não é automaticamente o vault do Windows. Para usar seus arquivos
locais e controlar o computador, rode o backend na mesma máquina. Sincronização
entre máquinas não está implementada.

## Provedores

Gemini é o padrão (`GEMINI_API_KEY`, `GEMINI_MODEL`). Ollama pode ser escolhido com
`CRONOS_PROVIDER=ollama`, `OLLAMA_MODEL` e `OLLAMA_URL`. O modelo local precisa estar
instalado e cabe na RAM/GPU; o Cronos não baixa modelos automaticamente.

Para acrescentar provedores, copie `config/providers.example.json` para
`config/providers.json`. Configure IDs únicos, tipo (`openai`, `anthropic`,
`gemini` ou `ollama`), modelo, endpoint e nome da variável da chave. `max_output_tokens` e
`timeout_seconds` permitem ajustar limites operacionais por provedor. O manifesto
não contém chaves. Escolha o ID em `CRONOS_PROVIDER` e reinicie. Há exemplos para
OpenAI, Groq, OpenRouter, Claude e Mistral; verifique modelos e cotas da sua conta.
Não há limite fixo de quantidade de provedores registrados. Nem todo endpoint
compatível suporta JSON: o adaptador precisa desse suporte ou de uma resposta
JSON válida seguindo as instruções.

`consult_models` consulta os provedores indicados depois de sua confirmação.
Os resultados permanecem identificados por provedor e incluem falhas; o modelo
principal analisa diferenças sem votação por semelhança de palavras. Não há troca
silenciosa de provedor ou de modelo pago. Nenhuma API paga é tratada como gratuita.

Se a IA falhar, execute `Diagnosticar-Cronos.bat`. Ele consulta configuração,
último erro e contagens locais sem gerar texto nem consumir uma requisição Gemini.
Para entender o registro e solicitar um teste real, veja [controle de consumo](docs/CONSUMO_GEMINI.md).
Gemini agora usa a rota Live encontrada no original: [instalação e configuração](docs/GEMINI_ORIGINAL.md).
Localização das notas e filtros da espiral: [memória seletiva](docs/MEMORIA_SELETIVA.md).
Interromper com ESC e melhorias de captura: [microfone e perguntas](docs/ESC_E_MICROFONE.md).

## Voz

Configure `FISH_API_KEY`, `FISH_REFERENCE_ID` (opcional: sem ID, voz padrão),
`FISH_MODEL`, `FISH_SPEED` e `FISH_LATENCY`. O modelo de síntese não é o ID da voz.
Não há modelo de síntese padrão; `s2-pro` pode ser selecionado explicitamente com `FISH_MODEL=s2-pro`. Disponibilidade e preço dependem da
conta. Não há fallback automático que esconda falhas ou mude sua voz.

Há síntese MP3, transcrição e endpoint de áudio em streaming. A interface
básica usa o MP3 completo; a interface definitiva pode consumir o streaming.
A API permite selecionar referência e velocidade por solicitação. Ela não
seleciona uma “voz sombria” com base em palavras do assunto. Gemini Live, interrupção de fala, STT offline de conversa e síntese local permanecem adaptações futuras. O novo ouvinte de abertura é local e separado da conversa; não foi transplantado do código antigo.

## Ferramentas e integrações

`GET /tools` lista apenas ferramentas carregadas nesta máquina, com esquemas.
A conversa pode buscar/ler notas, listar/ler arquivos, criar/mover arquivos,
extrair ZIPs, pesquisar na web e consultar IAs. Em Windows há ferramentas para
abrir pastas, navegador, Notepad, calculadora, Explorador e Obsidian. Também pode iniciar um `.exe`
existente na pasta autorizada, após confirmação humana do arquivo e argumentos;
processo iniciado não significa tarefa concluída.

Configure `CRONOS_FILES_ROOT` com a pasta autorizada; o padrão é Downloads.
Leitura/listagem têm paginação para continuar conteúdos longos. Arquivos
internos de configuração e credenciais não são fornecidos ao modelo. Criação
não sobrescreve arquivos. Movimentação e extração não substituem destinos.
As operações que alteram arquivos ficam pendentes até confirmação humana.
O modelo não pode se autorizar passando `confirmed=true`.

Resultados de ferramentas são registrados antes da próxima chamada de IA,
inclusive se ela falhar depois. O limite configurável `CRONOS_TOOL_ROUNDS` evita
loops; não remove resultados já executados. Confirmações expiram em cinco minutos,
são específicas da sessão e não sobrevivem ao reinício do processo.

A busca usa DDGS com backend DuckDuckGo. Para nuvem com rede restrita, o domínio
`html.duckduckgo.com` precisa estar permitido. Dependências instaladas não provam
acesso ao serviço. O primeiro instalador já instala o extra `search`.

Plugins novos podem ser instalados com um entry point `cronos.tools`; veja
[examples/plugin.py](examples/plugin.py). No pacote do plugin:

```toml
[project.entry-points."cronos.tools"]
meu-plugin = "meu_pacote:build_tools"
```

Ative explicitamente `CRONOS_ENABLE_PLUGINS=1`. A função recebe `(settings,
memory)` e retorna objetos `Tool`. Plugins são código local com acesso ao
processo, não uma sandbox. Colisões/erros são reportados por `/tools`. Não há
importação automática de scripts baixados nem do pacote antigo.

## Migrar o Cronos anterior

O ZIP enviado não inclui `api_keys.json`, `fish_audio.json`, `storage.json` ou
`long_term.json`. Se eles estiverem na instalação antiga do seu Windows, o
migrador pode reutilizá-los. Primeiro, confira a prévia na pasta do projeto novo:

```bat
.\.venv\Scripts\python.exe -m cronos.migrate "C:/CAMINHO/CRONOS_ANTIGO"
```

Para aplicar, adicione `--apply`; para escolher um vault de destino explicitamente,
adicione `--vault "C:/CAMINHO/VAULT"`. Credenciais existentes não são substituídas.
A opção `--vault` altera o caminho de destino explicitamente. Os fatos antigos
viram relatos importados, com origem identificada, sem truncar seu conteúdo.
A mesma importação não se repete. Arquivos originais são preservados.
A migração não executa código antigo nem importa a interface/prompts antigos.
Não consegue recuperar entradas que já foram apagadas/truncadas pelo programa antigo.

## Desenvolvimento e validação

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,search]'
.venv/bin/python -m pytest -q
.venv/bin/python -m uvicorn cronos.app:app --host 127.0.0.1 --port 8000
```

A interface de testes é servida na raiz do backend. Informe `CRONOS_API_TOKEN`
quando iniciar manualmente; a janela desktop configura sua conexão automaticamente.
Tokens da interface não são persistidos no navegador. Use uma única instância.
Não exponha à internet sem TLS e autenticação apropriada: a instalação atual é
pessoal, e o token permite acessar todo o vault/histórico autorizado.

Testes cobrem memória grande, migração, arquivos manuais, aliases, falhas de
exportação, orquestração, permissões, falhas das APIs e contratos de áudio.
Chamadas de provedores são simuladas para não usar credenciais nem gerar cobranças.
Validação real exige suas contas e o Windows. Foto explícita da câmera, captura de tela para revisão e ouvinte de abertura possuem implementação nova com testes simulados. Controle geral por cliques, WhatsApp, jogos, lembretes, dashboard remoto e processamento Office/PDF continuam fora do escopo implementado.

## Segurança e privacidade

Veja [a auditoria e seus limites](docs/SEGURANCA.md). Executáveis e plugins ficam desligados por padrão. `CRONOS_PRIVACY_MODE=local` restringe o assistente a modelos Ollama em loopback e desativa serviços externos, inclusive Fish Audio. A interface continua sendo a janela do programa Windows; a API local serve à comunicação interna.

Com 4 GB de RAM, prefira modelos externos: você pode cadastrar vários provedores e trocar o modelo, mantendo a mesma personalidade e memória. Consultar vários modelos não funde seus parâmetros nem garante melhor resposta. O roteamento automático por tarefa é uma evolução futura; hoje a seleção é configurável e a consulta adicional exige confirmação. Assinaturas de chats não substituem credenciais de APIs oficiais.

## Radar de diagnóstico

A janela de testes agora mostra um radar e alertas do backend. Verifica RAM,
espaço para salvar memória, disponibilidade e alteração da personalidade,
exportações pendentes e configuração de acesso. Falhas em conversa/voz e várias
tentativas bloqueadas também geram aviso. O radar indica o diagnóstico em execução,
não uma varredura de invasores. Funciona enquanto o Cronos está aberto e não
substitui antivírus. A janela oferece a opção de falar novos alertas pelo Fish
Audio, com possível consumo de créditos. Nenhuma chamada de IA é feita para o
monitoramento periódico. Veja [o contrato para sua futura interface](docs/API.md#radar-e-alertas).

## Central dos 12 módulos e integração Windows

A bancada expõe os 12 módulos da imagem do usuário. Veja [funções, instalação do comando de voz e roteiro de validação real](docs/MODULOS_WINDOWS.md). Segurança inclui auditoria periódica de leitura e ações restritas com confirmação. Planejamento salva objetivos e etapas em SQLite; não executa os passos automaticamente. Visão analisa uma imagem explicitamente autorizada e não mantém a câmera ligada. O iniciador local reconhece “abrir Cronos” mesmo com a janela fechada, desde que o ouvinte esteja ativo. Prepare e ative pelo módulo Dispositivos; o início com Windows é opcional e removível.

Interface e memória atualizadas: [Olho de Deus e Obsidian](docs/OLHO_DE_DEUS_OBSIDIAN.md).

O teste de compatibilidade legado com `s2.1-pro-free` retornou HTTP 400 no notebook. A disponibilidade desse identificador não foi comprovada; não há troca automática de modelo. `Testar-Voz-Isolada.bat` agora apresenta o motivo sanitizado da resposta para diagnóstico.

Configuração real de voz recuperada: siga [Voz original](docs/VOZ_ORIGINAL.md).

Microfone e início da voz: [correções e atualização](docs/MICROFONE_E_LATENCIA.md).
Escuta contínua, memória e comandos do mapa: [atualização](docs/ESCUTA_CONTINUA.md).

Painéis desktop e controles disponíveis: [documentação dos 12 painéis](docs/PAINEIS.md).

### Música na interface web

Abra `Iniciar-Cronos-Web.bat` (Brave ou navegador padrão). O player só é criado
quando solicitado. Exemplos: “Kronos, colocar música Evidências”, “colocar músicas
parecidas de MC Hariel”, “pausar música”, “continuar música”, “próxima música” e
“parar música”. O player interno reproduz os fluxos públicos de áudio/vídeo da fonte, sem iframe nem janela externa. O navegador pode exigir um clique
inicial para permitir áudio. Conteúdo indisponível ou que exige login/assinatura não é reproduzido por este player; escolha outro resultado.

A pesquisa consulta os resultados públicos do YouTube e usa yt-dlp como alternativa de metadados; mudanças no site,
consentimento ou bloqueios de rede podem impedir essa busca. Nesse caso, o painel
oferece busca dentro do painel e aceita colar um link para tocar aqui; não abre janela externa automaticamente.
Opcionalmente, `YOUTUBE_API_KEY` no `.env` usa a API oficial de pesquisa com sua
cota; não é necessário mudar as chaves de Gemini ou Fish. “Músicas parecidas”
busca mixes do artista, sem prometer uma recomendação personalizada.

“Tocar frequência 432 Hz” ou “528 Hz” gera um tom puro local (20–2000 Hz), com
volume ajustável; para música nessas frequências, peça “colocar música relaxante
432 Hz”. Pausar/continuar/parar também controlam o tom. ESC na janela principal
fecha o player e cancela buscas pendentes. O modo de privacidade local bloqueia
música online, mas permite tons locais. Comandos de música não viram notas de
conhecimento no Obsidian.

### Prospecção de clientes no Brasil

No painel **Internet**, abra **Prospecção de clientes · Brasil**, ou diga
“Kronos, procurar restaurantes sem site em Manaus, AM”. Também aceita outras
cidades brasileiras, como Brasília, DF ou Rio de Janeiro, RJ. Informe o estado
para diferenciar municípios com nomes iguais. Se a fonte só fornece o ponto
central da cidade, a pesquisa usa um raio de 15 km e informa essa limitação.

A fonte padrão é OpenStreetMap/Nominatim/Overpass, sem chave de API. Os resultados
são uma amostra, dependem do cadastro público e não representam todos os negócios
da cidade. Há filtros por categoria, capacidade registrada (porte), dificuldade
do projeto, presença de site e avaliações disponíveis. OSM não fornece notas de
clientes; dados desconhecidos aparecem como desconhecidos. Para avaliações do
Google, configure opcionalmente `GOOGLE_PLACES_API_KEY` no `.env` e selecione
**Google Places**: exige uma API habilitada, cota e pode gerar cobrança. A busca
por voz/IA usa OSM por padrão, sem ativar a fonte paga automaticamente.

**Cruzar fontes sobre o site** consulta o cadastro e duas buscas na web, usando o
extra `search` já incluído pelo instalador Windows. Candidatos a site podem ser
homônimos e devem ser conferidos. “Nenhum site próprio encontrado” nunca comprova
inexistência nem interesse em contratar: confirme com o responsável antes de
oferecer trabalho. O programa não envia mensagens ou propostas automaticamente.
Também não declara que um restaurante é bom apenas por uma nota pública.

Cada resultado sugere um projeto inicial e explica a dificuldade, o que confirmar
com o cliente e o que deixar para outra fase. **Pensar neste projeto com o Kronos**
envia os dados públicos para a IA já configurada, para discutir escopo, tecnologias,
código e testes. A orientação de personalidade agora prioriza parceria de
programação, opiniões justificadas e ensino prático, sem promessas de competência
infalível ou testes que não foram executados.

As consultas são feitas sob demanda, uma por vez, com até 40 registros exibidos
(até 20 no Google) e cache por 30 minutos. O cache de no máximo oito pesquisas fica
em RAM, não é gravado no Obsidian. É possível exportar os resultados filtrados em
JSON. Permissão de busca desativada ou modo local bloqueia as consultas online.

### Explicações de estudo e cards por voz

“Kronos, explique Santo Tomás de Aquino em cards” mostra a resposta em seções na
tela. Os cards continuam nas perguntas seguintes da conversa até “ocultar os
cards” ou ESC. “Mostrar os cards” exibe a última resposta; a transcrição da fala
não aparece como card de explicação. A orientação de estudo acrescenta contexto,
exemplos do cotidiano, perguntas abertas e aplicação a situações novas, sem
inventar suas respostas. Uma pergunta por vez, quando a conversa for interativa.
O modelo ainda pode errar: instrução de personalidade não garante a qualidade de
cada aula, fidelidade histórica ou resultado em uma prova.

Música e clipes têm player interno com fila, pausa, continuação, anterior/próxima,
volume e posição. Aceita “Chronos, coloque minha música preferida, que é Nada pra
Fazer” e “quero ver o clipe Nada pra Fazer”; informe o artista se houver homônimos.
A IA também tem a ferramenta `music_search`, cujos resultados são entregues ao
player. A reprodução acontece nos elementos nativos de áudio/vídeo da interface: disponibilidade da fonte, compatibilidade de formatos e permissões de autoplay ainda se aplicam.
Nenhuma janela externa é aberta como substituto automático. A alternativa
`yt-dlp` consulta vídeos públicos e resolve URLs temporárias de mídia, sem baixar arquivos ou usar cookies.
Para instalar a nova dependência, execute novamente `Instalar-Cronos.bat`.

Quando a fonte Overpass principal de restaurantes falha, a pesquisa tenta duas
instâncias alternativas, com tempo e tamanho de resposta limitados. Se todas
falharem, informa a indisponibilidade, sem resultados inventados. Isso não torna
as fontes externas permanentemente disponíveis.


O comando “Chronos, abre a música Nada pra Fazer” abre a barra própria do Kronos.
“Abre o clipe Nada pra Fazer” inclui vídeo, limitado a 480p/30 fps. Quando a fonte
entrega áudio e imagem separados, a interface sincroniza ambos; pausa, busca de
posição e ESC atingem os dois. Não há link de abertura externa como fallback.
As URLs de mídia ficam em RAM por até quatro minutos e não vão para o histórico.
O instalador prepara o runtime JavaScript necessário ao resolvedor: reutiliza
Node 20+ existente ou baixa uma versão portátil oficial, verificando SHA-256,
na pasta privada `.cronos-local/media-runtime`. Essa preparação pode exigir
internet na instalação. Não é necessário instalar FFmpeg para a reprodução;
o teste de desenvolvimento `frontend/scripts/check-music.py` usa FFmpeg apenas
para gerar um vídeo de teste temporário.
