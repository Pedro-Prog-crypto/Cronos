# Atualização local preservando os dados

O pacote `releases/CRONOS-Atualizacao-Preservando-Dados.zip` contém a atualização da interface e do holograma R57 e um aplicador local. Pode atualizar a pasta Cronos-R50 que já está instalada, sem alterar dependências. Ele preserva as integrações, mas não contém as chaves ou memórias do usuário; esses dados continuam na instalação original.

Para quem já tem a R50 instalada e recebeu “Espaço insuficiente no disco” com o instalador completo, use `instalador.bat` da branch `feature/cronos-r57-hologram-motion`. Ele contém a atualização no próprio arquivo, procura `%USERPROFILE%\Cronos-R50` ou deixa selecionar outra pasta, lê o conteúdo embutido sem gravar outro ZIP temporário e atualiza apenas arquivos de código diferentes. O aplicador verifica espaço antes de substituir arquivos e mantém backup dos arquivos alterados. Apague o download anterior de aproximadamente 146 MB para liberar espaço antes de baixar o novo BAT.

1. Extraia em uma pasta temporária.
2. Execute `Atualizar-Cronos-Preservando-Dados.bat`.
3. Escolha a pasta do Cronos que já usa: ela precisa conter `.env`, `.venv` e a subpasta `cronos`. Não escolha a pasta nova extraída.
4. O aplicador solicita parada ao supervisor dessa instalação, se estiver ativo; a instalação fora do supervisor deve ser fechada antes. Verifica os arquivos do pacote, guarda backup dos arquivos de código afetados e substitui somente os caminhos de código do manifesto.
5. Ao concluir, o atualizador cria o atalho `CRONOS` na Área de Trabalho apontando para a pasta escolhida. Abra pelo atalho. Se usar a versão web, recarregue com Ctrl+F5.

O pacote também contém `Criar-Atalho-Cronos.vbs`, para criar o atalho depois: execute-o e selecione a pasta de instalação do Cronos.

Não lê nem reescreve o conteúdo de `.env`, `config/providers.json`, configurações privadas, cofre, banco de memórias ou preferências. Não remove arquivos adicionais que encontrar na pasta. As integrações existentes continuam usando seus registros e chaves originais. Ele não cria chaves ou integrações ausentes.

O backup do código fica em `.cronos-local/manual-updates`. Falha durante a aplicação provoca tentativa de restauração dos arquivos de código já substituídos. O manifesto SHA-256 verifica a integridade interna do pacote, não constitui assinatura externa. O pacote deve vir deste repositório.

A rotina de aplicação foi testada em diretórios isolados, incluindo preservação de dados, rejeição de pacote alterado, caminhos privados e recuperação de falha simulada. O seletor PowerShell/Windows não foi executado neste ambiente Linux.

O instalador R50 enviado na conversa excede o limite de leitura de 32 MiB. O código da versão R50 publicada no repositório indica que as integrações configuradas são guardadas na pasta instalada, em `.env`, `config/providers.json` e `vault`, e não no instalador. O atualizador preserva esses arquivos no próprio computador, sem exigir seu envio pela conversa.
