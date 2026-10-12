# Análise do CRONOS V32 e reconstrução do núcleo

Fonte: `CRONOS_V32_INTEGRADO_CORRIGIDO (1).zip`, enviado pelo usuário.
Inventário: [legacy-inventory.json](legacy-inventory.json).

## Cobertura

109 arquivos, 6.659.891 bytes descompactados: 72 módulos Python, documentação,
scripts Windows, três conjuntos de interface e assets. Todos foram inventariados
e receberam SHA-256. Os 72 módulos passaram por parsing AST sem execução;
imports, classes, funções, ferramentas e dependências foram registrados.
Os arquivos textuais foram lidos para identificar fluxos, prompts, limites,
configurações e operações externas. Os 13 assets de imagem foram verificados
por formato/dimensões; o modelo OBJ contém 468 vértices e 898 faces.

Nenhum instalador, script ou módulo do pacote foi executado durante a análise.
Parsing válido não comprova funcionamento no Windows ou acesso aos provedores.
Não havia no ZIP arquivos de credenciais ou o JSON de memória de uma instalação
ativa. A interface compilada não inclui seus fontes originais de desenvolvimento.

## Arquitetura anterior

| Parte | Arquivos | Papel |
|---|---|---|
| Conversa e coordenação | `main.py`, `core/gemini.py`, `core/llm_client.py` | Sessão Gemini Live, áudio, ferramentas e chamadas locais |
| Múltiplas IAs | `core/ai_council.py`, `plugins/conselho_ias.py` | Descoberta, concorrência e síntese de respostas |
| Voz | `core/fish_audio_tts.py`, `tts.py`, `stt.py`, `audio_devices.py`, `echo.py`, `wake_word.py`, `hotkey.py` | Fish Audio, alternativas locais, microfone, wake word e filtros de eco |
| Memória | `memory/memory_manager.py`, `core/auto_memory.py`, `core/obsidian.py`, `core/storage_paths.py` | JSON pessoal, captura por regex, notas diárias e temas |
| Extensão | `core/action_loader.py`, `plugin_loader.py`, `plugins/_template.py` | Descoberta de módulos e despacho por introspecção |
| Ações | `actions/` | Arquivos, navegador, tela, apps, sistema, documentos, mídia e mensagens |
| Interface | `ui.py`, `web_ui.py`, `interface/`, `interface_v32/`, avatar/HUD | PyQt, WebEngine e recursos visuais |
| Controle remoto | `dashboard/server.py` | Dashboard de celular e conexão com o processo principal |
| Instalação | `setup.py`, BATs, VBS e launcher | Dependências, atalhos e inicialização desktop |

## Limitações confirmadas no código

| Evidência | Consequência |
|---|---|
| `memory_manager.py`: `MAX_VALUE_LENGTH=380`, `_truncate_value` | Valores longos perdem conteúdo ao atualizar |
| `memory_manager.py`: `MEMORY_MAX_CHARS=200000`, `_trim_to_limit` | Entradas antigas podem ser removidas automaticamente |
| `memory_manager.py`: `PROMPT_CORE_CHARS=900` | Pouca memória aparece diretamente no contexto, apesar de busca sob demanda |
| `core/auto_memory.py`: padrões de primeira pessoa | Captura depende de frases específicas, não de compreensão geral |
| `core/obsidian.py`: `extract_topic` usa prefixos de perguntas | Conversas naturais e múltiplos temas podem não virar notas adequadas |
| `core/obsidian.py`: busca por substring inteira | Variações de frase, acentos e nomes prejudicam recuperação |
| `core/prompt.txt`: uma linha por tarefa, cerca de dez frases, roteiro teatral | Estilo rígido compete com a qualidade da explicação |
| `interaction_policy.py`: personalidade aponta para arquivo ausente no ZIP | A personalidade separada não está presente; o prompt grande permanece dominante |
| `main.py`: `_on_text_command` retorna sem sessão Live ou quando adormecido | Conversa digitada depende do estado da voz |
| `llm_client.py`: `num_predict=600` | Respostas locais são limitadas independentemente do tamanho do problema |
| `ai_council.py`: `_agree`/`_consensus` com interseção de palavras | Similaridade de redação pode ser confundida com concordância factual |
| `fish_audio_tts.py`: `_DARK_*` e `is_dark_topic` | Assunto pode trocar voz automaticamente |
| `fish_audio_tts.py`: modelos marcados como gratuitos e fallback local | O rótulo no código não comprova disponibilidade/preço ou sucesso do Fish |
| Ações importam módulos de UI, áudio e configuração global | Reaproveitamento isolado exige adaptação; copiar arquivos não basta |

Os mecanismos de confirmação e undo do pacote são ideias úteis. Não foram
tratados como limitações a eliminar. A versão nova usa confirmações vinculadas
à conversa, expiráveis e resolvidas pela interface humana; argumentos do modelo
não autorizam alterações. Nunca executa uma ferramenta só porque uma nota manda.

## Núcleo novo implementado

- `engine.py`: contexto por orçamento configurável, planejamento em etapas,
  execução de ferramentas, síntese e registro de resultados antes da chamada
  seguinte. Falhas posteriores mantêm as ações auditáveis.
- `storage.py`: SQLite transacional, histórico completo, busca FTS5 por conteúdo,
  aliases, reindexação de notas manuais e exportações Markdown recuperáveis.
  Sem descarte automático de memórias antigas e sem truncar valores armazenados.
- `integrations.py`: manifesto de provedores e adaptadores Gemini, Ollama,
  OpenAI compatível e Anthropic. Sem número fixo de provedores cadastrados.
- `tools.py`: catálogo tipado e ferramentas independentes da interface.
  Consulta múltiplas IAs com resultados separados e confirmação do envio.
- Fish Audio: síntese, transcrição, referência/velocidade configuráveis e áudio
  em streaming, com diagnóstico por tipo de falha. Sem voz trocada por keywords.
- `migrate.py`: prévia e migração explícita de configurações e relatos antigos,
  sem executar o código antigo, substituir credenciais existentes ou apagar fontes.
- Personalidade Markdown concisa e editável, sem bordões ou contagem fixa de frases.

## Recursos e estado de adaptação

| Recurso do pacote anterior | Estado no núcleo novo |
|---|---|
| Chat por texto e contexto persistente | Reconstruído e testado com modelos simulados |
| Obsidian, temas e busca de memórias | Reconstruído; notas manuais, aliases e recuperação de falhas testados |
| Gemini / Ollama | Adaptadores e contratos HTTP testados; contas reais pendentes |
| Conselho e provedores compatíveis | Manifesto e consultas independentes; sem votação por palavras |
| Fish TTS / transcrição | Contratos testados; voz real e cota dependem da conta |
| Streaming Fish | Endpoint implementado e testado com streams simulados |
| Arquivos de texto / ZIP / movimentação | Ferramentas com escopo e confirmação, testadas |
| Abrir apps, pastas e navegador | Adaptadores Windows; execução gráfica pendente no Windows |
| Pesquisa web | DDGS instalado; proxy respondeu 403 ao túnel; liberação do domínio salva no rascunho, ainda não aplicada |
| Plugins | Contrato de entry points, ativação explícita e relatório de erros |
| Wake word, PTT, interrupção, Gemini Live e áudio offline | Ainda não portados |
| Tela/câmera, automação de cliques e controle geral do sistema | Ainda não portados |
| WhatsApp/Telegram, jogos e lembretes do sistema | Ainda não portados |
| Processamento Office/PDF, mídia e dashboard remoto | Ainda não portados |
| Interface, avatar, HUD e imagens antigas | Excluídos do reaproveitamento, conforme pedido |

Os itens pendentes não aparecem no catálogo como se funcionassem. A API foi
preparada para sua interface; não inclui cópia da interface V32. A inteligência
continua dependendo do modelo e das evidências disponíveis. Orçamentos de
contexto, limites das APIs, disco e hardware permanecem limites reais.

## Origem e licença

O `LICENSE` do ZIP identifica **MARK LV — JARVIS**, copyright 2026
**FatihMakes**, sob **CC BY-NC 4.0**. O pacote e seus assets não foram publicados
no repositório novo. A reconstrução contém implementações novas e um inventário
de referência, sem transplantar o código, prompts ou interface do ZIP.
Reaproveitamento direto futuro de código do pacote deve preservar atribuição e
respeitar os termos dessa licença, incluindo a restrição de uso comercial.

## Validação desta reconstrução

50 testes passaram. O teste no Chromium exercitou chat, histórico, áudio,
transcrição e layout com serviços simulados. Provedores reais e a janela
Windows continuam pendentes de credenciais/hardware. A consulta externa
DuckDuckGo foi bloqueada pelo proxy (CONNECT 403). O rascunho do ambiente
foi atualizado com html.duckduckgo.com, preservando Fish/Gemini e os presets;
a publicação e aplicação da configuração são etapas separadas.
