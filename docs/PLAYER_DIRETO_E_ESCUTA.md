# Player direto e conversa contínua

A comparação com `actions/video_player.py` e `ui.py` do arquivo original mostrou que ele usa o YouTube como fonte, extrai os fluxos com yt-dlp e os reproduz em QMediaPlayer. Não havia outro catálogo de clipes nesse caminho.

Agora o frontend solicita reprodução direta em áudio/vídeo HTML do Cronos. O backend também usa esse modo por padrão. Falhas de extração ou reprodução mostram o erro; não abrem um player do YouTube como alternativa. Uma resposta antiga do servidor com player embutido é recusada pelo frontend atualizado. O endpoint legado continua disponível somente mediante pedido explícito `native=false`, para compatibilidade.

O seletor existente prioriza MP4/H.264, até 480p/30 fps, para reduzir a carga. Fontes externas podem expirar, bloquear a extração ou exigir acesso que este player não oferece. Isso não garante que todo clipe funcionará nem elimina a dependência da rede.

O microfone habilitado permite perguntas seguidas sem repetir o nome. Uma migração restaura essa preferência uma vez em instalações anteriores; mudanças posteriores no painel de Linguagem são preservadas. Durante a fala do assistente, a interrupção por “Cronos” continua separada. O botão do microfone/F4 controla a escuta. Enquanto habilitada, outras vozes próximas também podem ser captadas.

Os testes de navegador reproduzem áudio e vídeo reais gerados localmente, com catálogo e URLs externos simulados. Cobrem controles, tela cheia, recuperação do microfone e recusa do player antigo. Não substituem uma reprodução com o provedor real ou uma medição no notebook Windows.

Para atualizar: encerre o Cronos e copie o conteúdo da versão nova sobre a mesma pasta usada para iniciar. Preserve `.env`, configuração, cofre e `.cronos-local`. Reinicie nessa pasta e recarregue a página; atalhos de versões antigas continuam executando arquivos antigos.
