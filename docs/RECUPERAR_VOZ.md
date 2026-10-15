# Recuperar a mesma voz após trocar de versão

Mantenha uma única pasta de instalação. Uma pasta extraída do GitHub não traz suas chaves, ID de voz ou memórias: esses dados particulares não são publicados.

1. Encerre o servidor da pasta atual usando **Parar-Cronos-Web.bat**. Fechar só a aba não encerra o servidor.
2. Nessa mesma pasta, abra **Importar-Voz-Original.bat**.
3. Escolha o arquivo **.env da versão em que a voz funcionava**. O seletor também aceita o `config/fish_audio.json` e ZIP original que já eram suportados. Não escolha o .env da instalação atual.
4. O importador recupera os campos Fish dessa configuração e cria uma cópia do .env atual em `.cronos-local/env-before-voice-*.bak`. Para uma fonte .env, não altera Gemini, microfone, memória, personalidade nem o arquivo de origem.
5. Reabra **Iniciar-Cronos-Web.bat dessa mesma pasta** e use **Síntese de voz → Testar voz**.

Não envie o .env, chaves ou backups por mensagem. O importador não gera áudio nem consulta saldo. Ele não ativa plano, não procura credenciais em outras pastas por conta própria e não troca o modelo ou referência por outro.

## Reprodução

Uma saída salva que não existe mais ou a falta da API de seleção de saída agora leva à saída padrão, com aviso, em vez de impedir a fala. Se o volume da voz estiver em zero, o Cronos explica onde aumentá-lo e não envia síntese inútil ao provedor. Confira também se o Windows ou o navegador estão silenciados; a página não consegue desfazer um silenciamento feito fora dela.

Os testes automatizados reproduzem áudio WAV/PCM de teste no Chromium. Isso verifica o fluxo de reprodução, não o acesso à conta Fish nem o som físico dos alto-falantes do usuário. Erros HTTP de chave, acesso ou cobrança precisam ser distinguidos pela mensagem real; não são classificados automaticamente como saldo zerado.
