# Cronos

Primeira base do assistente: API Python/FastAPI, Gemini ou Ollama, personalidade
Markdown, memória compatível com Obsidian e voz pelo Fish Audio. A interface é
separada e consome o contrato em [docs/API.md](docs/API.md).

## Programa Windows

O objetivo do Cronos é um aplicativo desktop. A interface do navegador é uma
bancada de testes; agora ela também abre em uma janela própria pelo WebView2.

Extraia o ZIP inteiro, abra `Instalar-Cronos.bat` e configure `.env` no Bloco de
Notas. Depois abra `Iniciar-Cronos.bat`: ele inicia o backend local, escolhe uma
porta livre e abre a janela Cronos sem iniciar seu navegador. Se o token não
estiver configurado, ele gera um token temporário para essa execução e conecta
a janela automaticamente. As chaves dos provedores continuam necessárias.

O instalador preserva `.env` existente. Ao atualizar a partir de outro ZIP,
mantenha seu `.env` e o vault; não publique esses arquivos. O renderizador exige
Microsoft Edge WebView2 Runtime. Se não estiver disponível, instale-o pela
Microsoft. A captura de microfone na janela ainda precisa de validação no
Windows; a transcrição por arquivo continua disponível.

Esta versão desktop usa Python e scripts de inicialização; ainda não é um
instalador `.exe` independente. Fechar a janela encerra o backend dessa execução.

Se a conversa falhar, abra `Diagnosticar-Cronos.bat`. Ele faz uma chamada mínima
ao provedor e mostra o diagnóstico sem imprimir chaves ou salvar conversas.
A chamada pode consumir cota. Erros do Gemini agora distinguem chave rejeitada,
API desativada, acesso negado, modelo indisponível, cota e conexão. A configuração
presente na interface não comprova que a chave foi aceita. Após editar `.env`,
feche e reabra o Cronos para carregar as alterações.

Comandos equivalentes, executados na pasta do projeto:

```bat
.\.venv\Scripts\python.exe -m pip install -e ".[desktop]"
.\.venv\Scripts\python.exe -m cronos.desktop
```

## Desenvolvimento / interface no navegador

Instale Python 3.11+ e execute no PowerShell, na pasta do repositório:

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Edite `.env` localmente: preencha `GEMINI_API_KEY`, `FISH_API_KEY` e o ID da sua
voz em `FISH_REFERENCE_ID`. O modelo de síntese é separado do ID da voz.
`FISH_MODEL=s2-pro` é suportado pelo SDK fixado; confirme disponibilidade na sua
conta. `GEMINI_MODEL=gemini-2.5-flash` também é editável. Nunca publique `.env`.

Gere um token, coloque o resultado em `CRONOS_API_TOKEN` e não o compartilhe:

```powershell
.\.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Configure `CRONOS_VAULT=C:/Users/SEU_USUARIO/Documents/Cronos` no `.env` e abra
essa pasta como vault no Obsidian. Se Documentos estiver no OneDrive, use seu
caminho real. Inicie o backend e rode os testes:

```powershell
.\.venv\Scripts\python -m uvicorn cronos.app:app --env-file .env --host 127.0.0.1 --port 8000
.\.venv\Scripts\python -m pytest -q
```

Use um único worker para preservar a ordem das gravações. A autenticação atual
atende uma instalação pessoal com um único usuário: o token permite acessar
todo o histórico. Não exponha à internet sem TLS e autenticação adequada.
Sua interface deverá configurar o token localmente, sem incluí-lo no código
distribuído. Configure a origin exata em `CRONOS_CORS_ORIGINS`.

## Interface de testes

Com o servidor iniciado, abra o endereço local da porta 8000 no navegador
da mesma máquina. A interface é servida pelo próprio backend, sem instalar
Node ou iniciar outro servidor. Informe o `CRONOS_API_TOKEN` no campo Conexão
e clique em Verificar conexão. O token permanece apenas na página; não é
salvo no armazenamento do navegador.

- Envie mensagens, confira os temas e caminhos das notas e guarde o ID para
  carregar o histórico depois. Nova conversa mantém os arquivos anteriores.
- Use Resposta no painel de voz, gere o MP3 e reproduza pelo player.
- Envie um arquivo ou grave pelo microfone para transcrever; revise o texto
  antes de enviá-lo ao Cronos. A gravação para automaticamente em 60 segundos.

Microfone exige permissão e um contexto seguro (localhost ou HTTPS).
Configuração presente não significa que a chave/cota foi validada: teste cada
função. Não há modo de demonstração que simule sucesso na interface. Sem chaves,
as chamadas reais mostram o erro retornado pelo backend.

## Nuvem / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
.venv/bin/python -m uvicorn cronos.app:app --host 127.0.0.1 --port 8000
```

As variáveis podem ser injetadas pelo ambiente. Na nuvem, o vault não é o vault
do seu Windows. Para escrever diretamente no Obsidian, rode o backend no
Windows; sincronização entre máquinas ainda não está implementada.

## Personalidade e memória

Edite `modelos/personalidades/cronos.md`, relido a cada mensagem. A memória usa:

- `Conversas/<UUID>.md`: histórico com a origem de cada fala.
- `Temas/<nome>-<identificador>.md`: resumos separados por tema e links para a
  conversa original, criados apenas quando os assuntos aparecem.
- `.cronos/<UUID>.json`: estado persistente do histórico.

O modelo identifica até cinco temas por mensagem. Títulos iguais, sem diferença
de caixa, atualizam a mesma nota; sinônimos ainda podem gerar notas separadas.
A recuperação usa palavras dos títulos, até três notas e as últimas vinte
mensagens da sessão. Não há busca semântica nem memória ilimitada neste estágio.
Os resumos são identificados como conteúdo de IA não verificado.

## Ollama opcional

Instale Ollama e obtenha um modelo compatível com sua RAM/GPU, por exemplo
`ollama pull gemma3:4b`. Configure `CRONOS_PROVIDER=ollama` e
`OLLAMA_MODEL=gemma3:4b`. O backend precisa acessar o endereço do Ollama; o
endereço padrão só funciona na mesma máquina. Não exponha Ollama publicamente.
Novos provedores são registrados em `cronos/providers.py`, sem limite fixo;
cada um exige um adaptador e testes.

## Agente Windows inicial

```powershell
.\.venv\Scripts\python -m cronos.windows_agent downloads
.\.venv\Scripts\python -m cronos.windows_agent search "Sócrates"
.\.venv\Scripts\python -m cronos.windows_agent extract "$HOME\Downloads\arquivo.zip" --destination "$HOME\Downloads\arquivo-extraido"
```

A extração pede confirmação, exige destino novo e rejeita caminhos perigosos,
links e arquivos acima dos limites. O agente é uma ferramenta local por terminal;
a conexão com conversa e interface ainda será implementada. Execução de
downloads e controle geral do desktop não estão disponíveis nesta base.

## Validação

Os testes verificam memória, autenticação, falhas de provedores, contratos de
áudio e extração de ZIPs. Usam serviços simulados e não fazem chamadas pagas.
Depois de configurar as chaves, valide `/chat`, `/voice/speech` e
`/voice/transcribe` com os serviços reais. Custos e limites dependem da conta.
Captura de microfone, reprodução e streaming na interface ainda não existem.
