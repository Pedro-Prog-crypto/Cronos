# Uma pasta de dados para todas as versões

Baixe `ABRIR-CRONOS-COM-MEUS-DADOS.zip`, extraia o único BAT e abra-o.
Na primeira execução, selecione a **pasta extraída do Cronos que contém seus
dados atuais**, com `.env`, `cronos` e o cofre de memórias configurado. O BAT não
extrai RAR ou ZIP. Não selecione uma versão vazia se quer importar suas memórias.

O iniciador cria `Cronos-Dados` dentro da pasta Documentos do Windows (inclusive
quando Documentos está redirecionada para OneDrive). Antes de importar, faz uma
cópia completa da instalação em `Documents/CRONOS-Backups`. As bases SQLite são
copiadas pela API de backup, incluindo alterações confirmadas no WAL. Arquivos
originais não são apagados. Caminhos externos configurados também são importados.

Na pasta permanente ficam:

- `.env`: chaves e configurações, mantendo os modelos e valores existentes;
- `config/`: integrações, conselho de IAs e demais configurações salvas;
- `vault/`: conversas, notas, bancos de memória, projetos e dados do estúdio;
- `modelos/`: personalidade e recursos locais existentes;
- `.cronos-local/`: estado local importado, sem o atualizador antigo;
- `DADOS-CRONOS.json`: registro da origem e localização do backup, sem chaves;
- `.launcher/`: inicialização e controle de uma única sessão.

Só as três configurações de caminho do cofre, personalidade e lista de provedores
são ajustadas na cópia do `.env`. O `.env` original permanece intacto. APIs não
são testadas nem enviadas durante a importação.

## Ao atualizar ou escolher outra versão

Abra **sempre esse BAT** e selecione a pasta do programa que quer usar. Ele
reutiliza `Cronos-Dados`; não importa um cofre antigo por cima dela. Um arquivo
sem segredos em `.cronos-local/data-home.json` liga cada instalação aos dados.
Versões novas sem `.env` recebem apenas um arquivo de orientação, sem duplicar
suas chaves. A configuração real continua na pasta permanente.

As novas conversas são gravadas diretamente nessa pasta, não num backup.
Voltar ao código de outra versão não volta a memória. O iniciador usa um
supervisor compatível com a pasta permanente e para a versão anterior antes de
trocar a instalação. Se uma recuperação automática de código ocorrer, ela não
substitui as memórias compartilhadas por um backup antigo.

O BAT instala sua atualização embutida **uma vez por instalação**; depois não
reaplica código antigo sobre atualizações posteriores. A pasta do programa e seu
ambiente Python continuam necessários: `Cronos-Dados` não é o aplicativo inteiro.
Versões muito antigas podem não compreender mudanças futuras do formato dos
dados; manter uma pasta compartilhada não torna todos os formatos compatíveis.

## Se a importação falhar

Nada é publicado como concluído. A pasta `Cronos-Dados-importando-...` contém
um aviso de importação incompleta; a origem e o backup são mantidos. Corrija o
problema e execute o BAT novamente. Se já houver uma pasta `Cronos-Dados` sem
registro válido, o iniciador interrompe em vez de substituí-la. Um cofre
configurado que não existe também interrompe a importação.

Não apague nem compartilhe `Cronos-Dados` ou os backups: contêm suas chaves e
informações pessoais. Faça cópias periódicas com o Cronos fechado. Os arquivos
distribuídos no GitHub contêm apenas código; a importação dos seus arquivos
acontece no seu computador.
