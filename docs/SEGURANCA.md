# Revisão de segurança do Cronos

Revisão estática do ZIP legado (109 arquivos, 72 Python) e testes do novo backend. O programa antigo não foi executado. Este trabalho não examina o Windows do usuário, seus pacotes instalados ou tráfego real. Segurança absoluta não é possível.

## O autor original tem acesso?

Não encontrei evidência de um destino de envio de dados especificamente controlado pelo autor no código examinado. Ter publicado o projeto no GitHub não concede acesso ao seu computador. Essa conclusão não certifica ausência de malware em dependências, executáveis ou instalações modificadas. Os serviços de IA recebem dados quando chamados, conforme suas políticas.

## Riscos encontrados no legado

| Evidência | Consequência |
|---|---|
| `dashboard/server.py`, listeners `0.0.0.0:8000/8001`; iniciado por `main.py` | Dashboard pode ficar acessível pela rede. |
| `_ensure_network_access` no dashboard | Tenta abrir regras de entrada para portas e Python e mudar perfil de rede; pode solicitar elevação. |
| Geração de certificado com fallback HTTP | Em caso de falha, autenticação e comandos podem circular sem TLS. |
| PIN de pareamento; tokens persistentes; token em URLs | Precisa proteção contra tentativas, expiração e revogação; URLs podem vazar em registros. Limpar dispositivos não equivale a revogar todos os tokens. |
| `cronos_web.py`, endpoints locais sem autenticação bearer | Outro processo local pode ler estado ou alterar configuração. Validação de Origin sozinha não autentica. |
| Importação dinâmica de plugins e agentes que executam código gerado | Código roda com privilégios do usuário; não existe isolamento efetivo. |
| JSON de credenciais e notas em texto simples | Quem lê a pasta do usuário pode obter dados e chaves. |

Não atribuo intenção maliciosa ao autor por esses problemas.

## Proteções implementadas no novo código

- API exige conexão loopback, Host local, Origin autorizada e token nos endpoints de dados antes de interpretar o corpo. Limite de tentativas de autenticação, tamanho, tempo de upload e solicitações simultâneas.
- Política de conteúdo, bloqueio de incorporação em frames e respostas sem cache. Documentação interativa por CDN desativada; esquema `/openapi.json` disponível para desenvolvimento.
- Acesso a arquivos recusa saída da pasta autorizada, arquivos internos, credenciais conhecidas, streams NTFS, symlinks, junctions e hard links.
- Execução de executáveis desligada por padrão (`CRONOS_ALLOW_EXECUTABLES=0`). Se habilitada, exige confirmação humana, usa argumentos separados sem shell e retira credenciais conhecidas do ambiente do processo filho.
- Plugins desligados por padrão. Confirmações pertencem à sessão, expiram e são de uso único; o modelo não pode aprovar a própria ação.
- `CRONOS_PRIVACY_MODE=local` bloqueia Gemini, provedores externos, Fish Audio, pesquisa externa, conselho de modelos, plugins e lançamento de executáveis. Ollama deve usar loopback. Isso não impede outros programas ou o próprio Ollama de acessar a internet.
- Aplicativo desktop não registra acessos HTTP. Chaves, vault e ZIP original não são publicados.

## Dados que saem do computador

| Recurso | Dados enviados quando utilizado |
|---|---|
| Gemini / outros modelos externos | Personalidade, mensagens, trechos recuperados da memória e resultados de ferramentas necessários à resposta. |
| Fish Audio | Áudio para transcrição ou texto para síntese. |
| Pesquisa | Consulta enviada ao buscador. |
| Consulta de outros modelos | Conteúdo da consulta, mediante confirmação. |
| Obsidian / SQLite | Armazenamento local; sincronização externa depende da configuração do usuário. |

No modo online, memória local não significa conversa privada em relação ao provedor. Um modelo pode solicitar leitura de arquivos permitidos; trechos lidos podem integrar a próxima chamada. Mantenha `CRONOS_FILES_ROOT` em pasta dedicada sem documentos sensíveis.

## Limites e próximos controles

Um processo executado ou plugin autorizado ainda pode ler arquivos e usar rede com os seus privilégios. Limpeza de variáveis não é sandbox. Proteção de caminhos reduz risco, mas não elimina corridas com outro processo que altera o sistema de arquivos. Use conta Windows comum, não Administrator, e mantenha Windows/Defender atualizados. Markdown permanece legível para o Obsidian: use criptografia do dispositivo, permissões da pasta e backups protegidos.

O script `Auditar-Windows.ps1` apenas consulta portas, regras relacionadas ao dashboard e estado do Defender. Não remove regras, não encerra processos e não lê conversas ou chaves. Consulte-o para verificar a instalação antiga; não há afirmação de que essas regras existem no seu notebook.

## Validação

60 testes passaram, incluindo bloqueio de Host/Origin/cliente remoto, autenticação e limite de tentativas, upload com tamanho declarado e em chunks, links e caminhos Windows, modo local e confirmação humana. Integrações reais exigem chaves; não foram certificadas aqui.

A auditoria de dependências com pip-audit/PyPI encontrou avisos no pip 25.0.1 do ambiente de desenvolvimento; o instalador foi atualizado para pip >=26.2. Nova consulta das 40 distribuições do ambiente não encontrou vulnerabilidades conhecidas. O teste de navegador também passou com provedores simulados. Não equivale a auditoria de binários Windows, pywebview ou das dependências antigas instaladas no notebook.
