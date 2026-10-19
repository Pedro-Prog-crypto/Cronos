# Atualização local preservando os dados

O pacote `releases/CRONOS-Atualizacao-Preservando-Dados.zip` contém a atualização de interface, análise e Estúdio de Sites da revisão indicada em tools/interface_update_manifest.json e um aplicador local. É destinado à instalação existente baseada em b736566, sem alteração de dependências. Não é uma instalação completa e não inclui chaves ou memórias do usuário.

1. Extraia em uma pasta temporária.
2. Execute `Atualizar-Cronos-Preservando-Dados.bat`.
3. Escolha a pasta do Cronos que já usa: ela precisa conter `.env`, `.venv` e a subpasta `cronos`. Não escolha a pasta nova extraída.
4. O aplicador solicita parada ao supervisor dessa instalação, se estiver ativo; a instalação fora do supervisor deve ser fechada antes. Verifica os arquivos do pacote, guarda backup dos arquivos de código afetados e substitui somente os caminhos de código do manifesto.
5. Ao concluir, o atualizador cria o atalho `CRONOS` na Área de Trabalho apontando para `Iniciar-Cronos-Web.bat` da pasta escolhida. Abra pelo atalho e recarregue com Ctrl+F5. Se quiser fixar na barra de tarefas, clique com o botão direito no atalho e escolha **Fixar na barra de tarefas** (no Windows 11, talvez esteja em **Mostrar mais opções**).

O pacote também contém `Criar-Atalho-Cronos.vbs`, para criar o atalho depois: execute-o e selecione a pasta de instalação do Cronos.

Não lê nem reescreve o conteúdo de `.env`, `config/providers.json`, configurações privadas, cofre, banco de memórias ou preferências. Não remove arquivos adicionais que encontrar na pasta. As integrações existentes continuam usando seus registros e chaves originais. Ele não cria chaves ou integrações ausentes.

O backup do código fica em `.cronos-local/manual-updates`. Falha durante a aplicação provoca tentativa de restauração dos arquivos de código já substituídos. O manifesto SHA-256 verifica a integridade interna do pacote, não constitui assinatura externa. O pacote deve vir deste repositório.

A rotina de aplicação foi testada em diretórios isolados, incluindo preservação de dados, rejeição de pacote alterado, caminhos privados e recuperação de falha simulada. O seletor PowerShell/Windows não foi executado neste ambiente Linux.

Os arquivos enviados na conversa excederam o limite de transferência de 32 MiB. Não foi possível verificar se aqueles ZIPs contêm `.env` e memórias; o instalador preserva os dados da pasta real escolhida no computador, sem exigir seu envio pela conversa.
