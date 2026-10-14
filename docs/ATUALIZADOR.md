# Atualizações e propostas do próprio código

## Primeiro uso

Instale esta versão completa uma vez, preservando `.env`, `config/`, o cofre de memória e sua personalidade. Abra **Iniciar-Cronos-Web.bat**. O iniciador usa `pythonw` no Windows, sem prompt. Um supervisor pequeno permanece separado do servidor para recuperar o código caso a aplicação quebre. São dois processos de controle leves; não é literalmente um único processo.

O navegador pode continuar sendo Brave/Chrome. O servidor fica somente no loopback. A porta e a credencial de sessão permanecem estáveis durante os reinícios coordenados. Após a instalação, use **Recarregar página** ou atualize a página: a sessão supervisionada pode recuperar a credencial em RAM por um cookie HttpOnly, SameSite Strict, restrito ao endpoint de reconexão. Não há chaves de provedores no navegador nem token salvo em localStorage. O cookie não é uma chave de API.

Para encerrar o servidor e o supervisor: **Parar-Cronos-Web.bat**. Abrir novamente o iniciador com o supervisor já em execução pede outra janela do navegador, sem iniciar um segundo servidor. O aplicativo desktop original continua disponível, mas não aplica atualizações supervisionadas nesta versão.

## Proatividade

Uma tarefa leve consulta dados locais quando não há conversa em processamento, a partir de um minuto após a abertura:

- Tempos realmente registrados de reconhecimento, geração e preparação da voz.
- Exportações de memória pendentes.
- Ausência de uma segunda integração configurada.
- Uma consulta diária ao canal `feat/cronos-test-ui` do repositório `Pedro-Prog-crypto/Cronos`.
- Uma consulta diária às listas de modelos das integrações online já configuradas, com até duas consultas simultâneas. Somente diferenças entre listagens observadas são anunciadas como modelos adicionais. Não há chamada de geração para descobrir modelos, nem conclusão de que um modelo novo é melhor ou gratuito.

Não há catálogo universal de todas as IAs nem instalação automática de um serviço encontrado na internet. O canal usado é de desenvolvimento, não uma certificação externa de estabilidade. O repositório precisa estar acessível; se ele for privado, a instalação pode usar `CRONOS_UPDATE_GITHUB_TOKEN` (ou `GITHUB_TOKEN`) já configurado localmente, com leitura do repositório. Nunca envie esse valor pela conversa. A credencial é enviada apenas à API oficial do GitHub; redirecionamentos de download são restritos ao codeload oficial, sem repassar o cabeçalho de autorização. Consultas de metadados ainda podem contar para limites de requisição dos provedores. Novidades de outros fornecedores continuam sendo pesquisadas em fontes oficiais quando solicitadas.

As ideias aparecem numa faixa temporária e podem ser anunciadas pela voz já configurada quando o usuário está livre. **Depois** adia a sugestão por 24 horas; o anúncio de cada ideia também é limitado a uma vez por dia. É possível desligar **Sugestões proativas** no painel Integrações. Geração de código e instalação nunca são autorizadas por uma sugestão, notícia ou texto de arquivo.

## Atualização publicada

1. O aviso identifica uma revisão imutável do repositório fixo.
2. **Preparar cópia** baixa exclusivamente o ZIP daquela revisão via HTTPS do GitHub.
3. O pacote é descompactado com limites, validação de caminhos Windows/POSIX, recusa de links, duplicações e arquivos privados.
4. A preparação compila Python sem executar o código e confere as referências do bundle da interface. Mudanças nas dependências/Python/build backend exigem o instalador completo; nenhum `pip`, shell ou npm é disparado automaticamente.
5. A versão em uso segue intacta. A tela informa que ainda aguarda autorização.
6. **Autorizar backup e instalar** cria um snapshot consistente SQLite/Markdown da memória. O supervisor para o servidor, copia o código e configurações para recuperação e confere o backup antes de substituir arquivos.
7. O supervisor reinicia a aplicação e verifica banco local, registro de ferramentas, preferências e entrada da interface. Uma curta observação de inicialização também precisa passar.
8. Em falha, restaura código, configurações e o snapshot da memória, então confere a inicialização da versão anterior.
9. Em sucesso, mostra a conclusão e permite recarregar a página.

Uma atualização pode ser recusada se o código local mudou depois da preparação, se o disco está sem espaço, se o arquivo foi alterado, se a compilação falhar ou se o pacote requer novas dependências. A cópia anterior não é descartada para tentar repetidamente a mesma atualização.

## Propostas geradas por IA

Exemplo: “Cronos, proponha uma melhoria na organização da memória. Consulte os módulos necessários e prepare uma proposta sem instalar.”

O assistente dispõe de `updates_source_catalog`, `updates_read_source` e `updates_propose_code`. Geração requer confirmação humana e pode consumir a cota da IA configurada; não depende de manter uma assinatura ChatGPT Plus, mas não elimina custos e limites de API.

A IA recebe apenas os módulos permitidos solicitados, nunca `.env`, notas privadas ou configurações de chaves. A leitura recusa caminhos arbitrários e padrões comuns de credenciais embutidas. Código com segredos embutidos de forma não reconhecida exige revisão local antes do uso: não há detector infalível de segredos.

A proposta altera uma cópia, em até oito módulos Python por vez. Voz, transportes Gemini/Fish, reconhecimento, autenticação, registro de ferramentas/confirmações e componentes de atualização são protegidos contra esse editor. Frontend, dependências, novo protocolo de IA e mudanças nesses componentes exigem uma atualização publicada/revisão de desenvolvimento. Integrar modelos a conectores existentes continua possível pelo painel de integrações.

A interface oferece **Revisar alterações**, explicação, diferenças de código e plano de testes sugerido. O backend exige abertura dessa revisão para propostas de IA antes da autorização de instalação. A revisão vale 30 minutos e é vinculada ao conteúdo preparado. A proposta não autoriza a si mesma.

**Compilação e inicialização não equivalem a testes funcionais completos.** O plano sugerido pela IA não é exibido como executado. A nova versão roda com as permissões do usuário Windows; a cópia de preparação não é um sandbox de sistema operacional. Backups do Cronos não desfazem ações arbitrárias fora da aplicação. Não existe garantia de ausência de bugs nem de que uma alteração melhore desempenho. Para mudanças grandes, o procedimento recomendado continua sendo revisão e testes de desenvolvimento antes da instalação.

## Recuperação e retorno

Os controles independentes ficam em `.cronos-local/updater/runner.py` e `update_transaction.py`, fora do código substituído. O iniciador utiliza essa cópia já existente, inclusive se os módulos da aplicação não importarem mais. Um diário persistente permite detectar uma interrupção no meio da atualização e repetir a restauração na próxima abertura.

Cada transação tem hashes da cópia preparada e do estado anterior, backup do código, snapshots locais das configurações e referência ao backup consistente da memória. Esses arquivos podem conter dados privados: não compartilhe `.cronos-local` ou o cofre.

Depois de uma atualização concluída, **Preparar retorno à versão anterior** cria outra proposta baseada no backup de código. A instalação desse retorno também exige autorização, novo backup da memória atual e verificação de inicialização. Esse retorno não apaga automaticamente estudos feitos depois da atualização.

Não há tentativas infinitas, publicação automática no GitHub, autoaprovação por modelo ou alteração oculta de voz/modelo principal. Se o próprio backup estiver inconsistente ou a recuperação falhar, o supervisor registra `recovery_failed` e preserva as cópias; poderá ser necessário recuperar manualmente. Perda do disco e ações fora da aplicação não são cobertas.

## Verificações de desenvolvimento

- `python -m pytest -q`: inclui troca de arquivos, falhas durante instalação, candidato que não inicia, restauração, cookie de reconexão, propostas de código e proteção de caminhos.
- `python frontend/scripts/check-updates.py`: fluxo real da interface no Chromium, com download/servidor de atualização simulados; nenhuma chave ou geração paga.
- `npm --prefix frontend run lint` e `npm --prefix frontend run build`.

Os testes não certificam o notebook Windows real, toda alteração futura, qualidade de código gerado ou ausência de cobranças dos provedores.
