# Configuração do original recuperada

O ZIP CRONOS-Original - Copia.zip contém config/fish_audio.json com chave e ID
configurados. A chave NÃO acompanha o repositório. O ID principal coincide com o
informado pelo usuário. Parâmetros encontrados: modelo s2.1-pro-free, formato WAV,
velocidade 1, latência balanced, endpoint HTTPS oficial /v1/tts, corpo JSON.

## Atualização no Windows

1. Feche o Kronos, atualize a branch feat/cronos-test-ui e preserve .env/vault.
2. Execute Instalar-Cronos.bat. Ele instala as dependências e prepara o pequeno
   modelo português Vosk. Se o download falhar, a instalação informa a pendência;
   execute novamente com internet. Não desliga verificações TLS.
3. Execute Importar-Voz-Original.bat e selecione o ZIP original que contém a
   configuração real, ou seu fish_audio.json. Ele lê apenas JSON, não extrai ou
   executa programas do arquivo. Substitui os campos Fish, restaura a chave Gemini quando presente no original
   e seleciona Vosk para transcrição. Preserva o modelo Gemini escolhido, vault
   e personalidade.
4. Execute Iniciar-Cronos.bat. A conexão interna continua automática. O .env
   local passa a ter prioridade sobre variáveis antigas herdadas do Windows.

A importação faz backup do .env existente em .cronos-local, ignorado pelo Git.
Ambos contêm dados privados: preserve localmente, não publique. Não use um ZIP
sem config/fish_audio.json nem uma configuração de exemplo sem sua chave.

## Fluxo de áudio

- Voz personalizada: Fish, com os parâmetros reais do original. Sem substituição
  silenciosa pela voz do Windows, mesmo que o original tivesse fallback_voice=true.
- Reconhecimento: Vosk português local, carregado apenas quando necessário e
  reaproveitado. Não consulta o endpoint ASR Fish; exige o modelo instalado.
- A interface converte gravações para WAV mono/16 bits/16 kHz antes do Vosk.
- Saída WAV do Fish: o cabeçalho de streaming pode conter comprimentos indefinidos;
  finalizamos o RIFF preservando as amostras PCM, para reprodução finita no player.
- A resposta da IA continua dependendo do Gemini configurado; sucesso da voz não
  resolve HTTP 404/503 do Gemini. Limitações de precisão do Vosk permanecem.

## Evidência desta tarefa

Houve chamada REAL à API Fish usando a configuração fornecida e uma chamada pelo
endpoint autenticado do Kronos: HTTP 200, áudio PCM 24 kHz. As consultas de saldo
antes/depois da chamada curta pelo backend retornaram API 0.000000 e pacote
7734/8000 em ambas. Isso é uma observação desse teste, não garantia de gratuidade
permanente ou ausência de contabilização posterior. Saldo API zero não impediu
esta chamada específica. Nenhuma chave foi impressa ou incluída no commit. A chave Gemini original
também foi testada com gemini-3.8-flash, escolhido pelo usuário: resposta JSON
válida recebida. Uma chamada bem-sucedida não garante disponibilidade permanente.

127 testes Python e TypeScript/build passaram. Browser verificou reprodução de
um WAV real já recebido; outras etapas usaram IA/entrada/transcrição simuladas.
O modelo Vosk oficial foi baixado e carregado após corrigir a validação para sua
estrutura plana (final.mdl/mfcc.conf/HCLr.fst/Gr.fst). Houve reconhecimento de um
trecho real, com resultado imperfeito: isso não certifica precisão. Microfone
físico, reprodução física e fluidez no Windows continuam pendentes.

Gemini: uma resposta direta com a chave original e gemini-3.8-flash foi validada;
um teste posterior de conversa completa também recebeu 503 do serviço. Agora
há uma única repetição após 503, mantendo chave/modelo/pedido e sem repetir
ações de ferramentas. Não há garantia de disponibilidade do serviço.
