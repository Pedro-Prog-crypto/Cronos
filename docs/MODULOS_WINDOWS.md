# Central de módulos e integração com Windows

A interface definitiva continua sendo a do usuário. A bancada possui botões para as funções e a API permite incorporá-las nessa interface. Há 12 áreas funcionais; isso não significa todas as capacidades de um assistente fictício.

## Operações disponíveis

| Módulo da imagem | Operação concreta | O que a verificação comprova |
|---|---|---|
| Processamento | Recursos de RAM/disco e cálculo leve | Backend calculou o resultado; não mede inteligência |
| Visão computacional | PNG/JPEG, fotografia da câmera, captura da tela para revisão; análise pelo Gemini | Configuração é distinta de uma análise real; precisão visual não é garantida |
| Síntese de voz | Texto para Fish Audio, gravação/transcrição | Receber áudio não comprova alto-falante ou qualidade da voz |
| Entendimento de linguagem | Conversa com contexto e personalidade; teste mínimo de geração | Provedor respondeu naquela chamada, sem garantia de respostas futuras |
| Planejamento | Plano manual ou com IA, etapas persistentes, retomada | Plano foi salvo; etapas só são concluídas por declaração humana |
| Ferramentas | Listagem, esquema, execução manual e confirmação | Apenas ferramentas registradas; execução altera só o que cada ferramenta permite |
| Integrações | Catálogo, descoberta de modelos e seleção do provedor | APIs oficiais; assinatura de chat não equivale a acesso à API |
| Banco de dados | Integridade SQLite, escrita/leitura com rollback, busca e sync Obsidian | Banco respondeu; sync externa do Obsidian é configuração do usuário |
| Internet | Pesquisa com URLs de fontes | Busca respondeu; conteúdo das fontes pode estar errado |
| Dispositivos | Inventário Windows, câmera/microfone da janela, ouvinte de abertura | Inventário não testa fisicamente cada dispositivo |
| Segurança | Auditoria Windows e ações limitadas confirmadas | Leituras de configuração não certificam ausência de malware |
| Monitoramento | Radar e eventos de diagnóstico | Sinais observados dentro do escopo, não detector geral de invasões |

A interface separa disponibilidade, configuração e último teste. Estados `configuration_only` são exibidos como serviço ainda não testado. Não existem selos de “tudo seguro”. Falhas aparecem com a evidência disponível. Verificações externas só são feitas ao clicar: não se fazem chamadas de IA periodicamente para monitorar o computador.

## Instalar/atualizar no notebook

1. Baixe a branch `feat/cronos-test-ui` pelo GitHub (Code → Download ZIP) e extraia a pasta inteira.
2. Preserve seu `.env`, `config/providers.json` e vault. Execute `Instalar-Cronos.bat`; não substitua arquivos com chaves por exemplos vazios.
3. Execute `Iniciar-Cronos.bat` e configure/teste os módulos. A nuvem não acessa seu Windows: o backend precisa estar no notebook.

Recomenda-se Python 64 bits 3.11 ou 3.12 e WebView2. Pacotes principais possuem distribuição Windows x64 para Python 3.11; isso não substitui execução no computador. O projeto continua dependendo de Python. Não é um instalador `.exe` independente.

## Segurança do Windows e correções

Quando o backend roda no Windows, há leitura a cada 120 segundos, além do botão Auditar. Consulta Defender, proteção em tempo real, idade das assinaturas, firewall, privilégios administrativos, build/edição, último hotfix visível, BitLocker/Secure Boot quando acessíveis e três regras conhecidas do dashboard antigo. Falta de acesso ou outro antivírus é estado desconhecido, não prova de desproteção. `Get-HotFix` não lista todas as atualizações nem verifica pendências do Windows Update. O aviso de Windows 10 indica o fim do suporte regular; não verifica inscrição no ESU.

Ações permitidas, sempre confirmadas pela pessoa:

- Abrir Segurança do Windows e Windows Update.
- Atualizar definições e executar verificação rápida do Defender. O Defender pode tomar medidas próprias contra ameaças; não é uma varredura do Cronos.
- Habilitar os três perfis do firewall. Pode afetar conexões de programas e exigir administrador.
- Remover somente regras com estes nomes exatos: `JARVIS Dashboard Port 8000`, `JARVIS Dashboard Port 8001`, `JARVIS Dashboard Python`. Não remove outras regras. Não faça isso se ainda precisar do dashboard antigo.

Não há PowerShell arbitrário vindo da IA, limpeza indiscriminada, desativação de antivírus, atualização automática do Windows, mudança de BIOS ou elevação silenciosa. Operações que exigem permissões podem falhar: prefira abrir a tela nativa e realizar a mudança consciente. Não recomendamos rodar permanentemente o assistente como administrador.

Operações longas retornam um trabalho `running`. Consulte operações até `completed`, `failed` ou `interrupted`. Timeout e fechamento encerram o acompanhamento; ações já entregues ao Windows podem continuar. Confirmar o início de uma varredura não significa que ela terminou ou que todo o sistema está livre de malware.

## “Abrir Cronos” com a janela fechada

É um processo separado e opcional, com Vosk e sounddevice. Não depende da API Gemini/Fish e não grava nem envia o áudio de ativação. É uma implementação nova; não copia o código do ZIP legado.

1. Com a janela aberta, entre em Dispositivos → Preparar modelo de voz. Confirme o download oficial de `vosk-model-small-pt-0.3` (~31 MB) em `alphacephei.com`, com TLS verificado. O tamanho é aproximado; há limites de download e extração.
2. Consulte operações até concluir. Modelo e hashes ficam em `%LOCALAPPDATA%/Cronos/wake`, fora do projeto/vault.
3. Clique Ativar microfone do ouvinte e confirme. Consulte o estado: deve aparecer `listening`; `error` ou `stopped` não confirma escuta. Autorize o microfone nas configurações de privacidade do Windows se necessário.
4. Feche a janela do Cronos e diga **“abrir Cronos”** ou **“abrir Kronos”**. Só essas duas frases completas são aceitas, com limiar de confiança e intervalo de 20 segundos entre ativações. Não são comandos de shell.
5. Se desejar, confirme Iniciar ouvinte com Windows. Cria somente um atalho na pasta Startup do seu usuário, sem registro global ou administrador. Remover início automático apaga esse atalho; Parar microfone encerra a escuta atual.

`Iniciar-Ouvinte.bat` oferece modo visível para diagnóstico e Ctrl+C encerra. `Parar-Ouvinte.bat` permite parar mesmo com o Cronos fechado. Por padrão o ouvinte **não** está ativo e **não** inicia com Windows. Se mudar a pasta do projeto, recrie o atalho de início automático. Mantenha o projeto/ambiente virtual enquanto o atalho for utilizado.

No notebook de 4 GB, modelos de conversa continuam na nuvem. O pequeno modelo de ativação também ocupa RAM e pode competir pelo microfone: pare-o para testar gravação se o driver não compartilhar o dispositivo. Reconhecimento tem falsos positivos/negativos e pode precisar de ambiente silencioso. Não afirmamos desempenho físico medido nesse notebook.

Os hashes do modelo detectam mudanças posteriores ao primeiro download; não são assinatura independente, nem impedem alguém com acesso à conta de alterar arquivos e hashes juntos. Arquivos executáveis, traversal e links são recusados na preparação. Não há instalação silenciosa por pip durante o funcionamento.

## Visão e privacidade

A câmera tira uma fotografia e libera o dispositivo. Captura de tela retorna primeiro à janela para revisão. Uma imagem só é enviada depois de escolher Analisar e autorizar explicitamente o envio ao Gemini. O limite é 2 MiB e seis milhões de pixels; a imagem é validada localmente antes da prévia na janela, redimensionada e metadados são removidos. Não se grava a imagem no vault. Não existe filmagem contínua, reconhecimento biométrico ou controle automático de cliques.

O modo `local` bloqueia análise externa, Fish, busca e preparação por download do modelo de ativação. Um modelo já preparado pode ser usado offline. Atenção: texto e imagens enviados aos provedores estão sujeitos às políticas deles.

## Evidências e pendências

- 100 testes automatizados passaram: doze módulos, planos persistentes, visão e consentimento, caminhos/links, envio de imagem no contrato Gemini, confirmações, operações Windows simuladas, palavras de ativação, download simulado com hashes e rejeição de pacotes inseguros.
- Teste Chromium passou: cliques nos 12 módulos, plano manual/IA e progresso, imagem/câmera/tela simuladas, ferramentas e ações confirmadas, radar, áudio/transcrição simulados e layout móvel.
- Instalação e `pip check` passaram no Linux. Auditoria pip-audit não encontrou avisos conhecidos nas dependências instaladas; os quatro pacotes principais de Windows consultados também não tinham avisos na API PyPI. Bibliotecas nativas embutidas não recebem certificação por esse resultado.
- Não houve acesso ao notebook. Defender, firewall, câmera, microfone físico, reprodução Fish e abertura real por voz continuam dependendo da instalação e teste local. As chaves Gemini/Fish não estão configuradas nesta nuvem; testes delas usam simulação.
- A busca real na nuvem recebeu HTTP 202 com página de desafio do DuckDuckGo e não retornou resultados; isso foi registrado como falha, sem burlar a verificação. A bancada oferece também abrir uma pesquisa no navegador do Windows. O host do modelo não estava acessível no runtime atual; a liberação adicional foi salva no rascunho da nuvem, ainda não aplicada. Pesquisa real e download do modelo dependem da rede. Se o ambiente de nuvem bloquear os destinos, isso não demonstra falha no Windows e não deve ser marcado como sucesso. Confira cada resultado na bancada.

Roteiro final no Windows: teste geração de texto, síntese/transcrição, análise de uma imagem sem dados privados, plano e retomada, busca, leitura/sync Obsidian, ferramenta inofensiva (listar), inventário, auditoria de leitura, e depois o comando de abertura. Só confirme correções após ler seu relatório e entender a ação.
