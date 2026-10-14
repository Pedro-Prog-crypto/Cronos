# Stremio no Cronos

Diga “Cronos, abrir o filme Matrix” ou “Cronos, abrir a série Game of Thrones temporada 2 episódio 3”. O painel pesquisa metadados públicos do Cinemeta; escolha o título correto e clique em **Abrir no Stremio**. Não é necessário fornecer ator. Temporada e episódio são opcionais, mas devem ser informados juntos.

Esta versão abre o **Stremio instalado no Windows do servidor Cronos**, usando o protocolo registrado pelo aplicativo. Se estiver acessando Cronos de outro aparelho, a abertura ocorre no computador servidor. Não é um player Stremio dentro da página. Essa opção aproveita o player e as configurações existentes sem carregar um segundo reprodutor no Cronos.

A abertura leva à página do título/episódio; você ainda seleciona uma fonte disponível no Stremio. O Cronos não instala complementos, não lê sua conta nem comprova reprodução somente porque enviou o pedido. Disponibilidade depende do catálogo e dos seus serviços. Não há promessa de reprodução automática de qualquer filme.

Abra o Stremio uma vez para registrar seu protocolo. Se o Windows não reconhecer o link, repare a instalação oficial. As permissões de busca web e abertura de aplicativos do Cronos continuam valendo. O modo local desativa o catálogo online.

Implementação baseada na leitura dos projetos oficiais `Stremio/stremio-shell` (c3a8bcbf857d5569b6ae7444ead0dc0a0814888b) e `Stremio/stremio-web` (bb2405ca6ce1bb2e358f800ab530e8ed7d043e9e): URI `stremio:///detail/{tipo}/{id}/{videoId}` com hostname vazio. Testes automatizados usam catálogo e iniciador Windows simulados; reprodução real no computador do usuário não foi validada no ambiente Linux.
