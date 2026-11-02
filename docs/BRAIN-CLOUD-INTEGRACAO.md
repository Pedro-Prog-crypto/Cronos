# Cronos Desktop + Brain Cloud

O Cronos Desktop conversa com o Brain pela API `/v1`, e não por uma pasta de código. O nome do ZIP, da pasta e a versão do Brain podem mudar. O contrato necessário é `GET /v1/health`, `POST /v1/auth/sessions` e `POST /v1/chat` da versão 0.4.4 enviada pelo usuário.

## Conectar no Windows

1. Inicie o Brain Cloud e abra a tela **Integração**. Use **Preparar conexão** e baixe `cronos-desktop.json`.
2. Na pasta da instalação completa do Cronos, dê dois cliques em `CONECTAR-BRAIN-CLOUD.bat` e escolha esse JSON.
3. O assistente verifica a identidade do servidor e o login; guarda a conexão em `vault/.cronos/brain-cloud.json`. Abra novamente o Cronos.

Esse arquivo contém uma credencial privada. Ele não vai para o GitHub nem para o pacote público. A migração do vault preserva o pareamento. Se o Brain estiver em outro computador, o endereço exportado precisa ser HTTPS acessível; `127.0.0.1` só alcança a própria máquina. O Brain precisa estar rodando. Na cópia recebida, ainda não há um modelo externo configurado; sem isso a API de conversa devolve indisponibilidade e o Cronos usa sua integração local.

O roteamento ao Brain só fica ativo no modo de privacidade `online`. No modo `local`, as perguntas continuam no motor local, mesmo com um arquivo de pareamento salvo.

## O que a ligação faz agora

- Perguntas de conversa e estudo em texto, incluindo fala já transcrita, vão ao Brain. Com o pareamento ativo, a janela usa transcrição antes da conversa, inclusive quando havia áudio direto do Gemini configurado. O Brain responde, mantém o histórico remoto e, com `remember:true`, guarda a pergunta como memória episódica conforme seu contrato atual. O Cronos fala a resposta com sua própria saída de voz e mostra sua própria interface. Uma cópia simples dos dois textos fica no histórico local da janela para continuidade de comandos do computador; não cria notas de conhecimento locais.
- O mapeamento entre conversas locais e remotas fica no vault. A troca de versão/pasta do Brain não altera o pareamento enquanto URL, dispositivo e API v1 permanecerem válidos.
- Enquanto o Cronos estiver aberto ou rodando em segundo plano, ele envia presença autenticada ao Brain periodicamente. A tela **Integração** do Brain pode verificar a conexão; presença online não significa que um modelo de IA esteja configurado.
- Pedidos que exigem ferramentas do computador, leitura de tela, página pública ou pesquisa atual ficam no motor local: o endpoint de chat do Brain 0.4.4 ainda não executa ferramentas do Desktop nem recebe imagens. Se o Brain falhar, o Cronos tenta responder pelas integrações locais e marca o retorno na resposta.
- O contrato atual do Brain aceita até 8 mil caracteres por pergunta. Falas mais longas usam o motor local, sem cortar a pergunta para caber.
- As notas e integrações antigas do Cronos continuam no vault local. Este pareamento **não migra automaticamente** essas notas, chaves ou provedores para o Brain. Publicar ou enviar dados privados à nuvem exigirá uma migração explícita e verificada. O código do Brain já oferece memória e personalidade próprias, mas sua qualidade depende dos modelos configurados nele.

## Microfone

O Brain recebe texto depois da transcrição. Ele não corrige áudio inaudível. A captura pela janela exige pelo menos 350 ms de voz detectada para o envio automático. O botão manual aceita um sinal de áudio curto de 100 ms quando o senhor o aperta, mesmo que a detecção automática tenha perdido a fala, mas não envia silêncio digital acumulado. O comportamento no microfone físico do usuário ainda precisa ser conferido nessa instalação. Use a frase reconhecida no painel **Entendimento de linguagem** para separar erro de captação de erro do Brain.
