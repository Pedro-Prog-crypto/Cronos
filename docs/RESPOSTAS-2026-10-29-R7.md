# Recuperação de esperas longas — R7

O relato de 200 segundos não pôde ser reproduzido no notebook do usuário. A revisão encontrou caminhos que permitiam esperas acumuladas: três tentativas de voz, chamadas ao SDK com seus próprios retries, recebimento de corpo HTTP sem limite no navegador e espera sem prazo por blocos PCM. O limite por provedor também não cobria a espera total da conversa, incluindo fila e ferramentas.

## Correções

- Conversas em streaming têm um orçamento total de 24 segundos até o primeiro trecho útil, incluindo fila e tentativas. Se nenhuma integração concluir, o erro aparece e a pergunta transcrita fica no campo para tentar novamente. Chamadas sem streaming também recebem um limite total de 24 segundos. No streaming, ao começar uma explicação, o limite inicial é desarmado; a geração ativa conserva o orçamento do provedor.
- Síntese completa tem um limite de oito segundos no backend, incluindo tentativas internas do SDK. No navegador, cada bloco tem um orçamento compartilhado de dez segundos para cabeçalhos, corpo e até duas tentativas. Somente falhas HTTP recuperáveis permitem a segunda tentativa; erro de credencial não gera três chamadas seguidas.
- A transcrição Fish tem limite total de doze segundos no backend e no navegador. Reconhecimento alternativo usa o mesmo limite. Uma falha de reconhecimento não é uma resposta nem uma medição de início da fala.
- O player PCM encerra a espera se ficar oito segundos sem receber um bloco. Esse prazo mede inatividade, não a duração da explicação.
- A falha de síntese mostra a resposta escrita automaticamente. Ela continua chegando e é salva, mesmo que a voz não esteja disponível.

Os limites são de recuperação de falhas, não promessa de início em cinco segundos. A velocidade real depende também da rede e das APIs. Uma geração que já começou mantém seus limites configurados; essa versão não garante disponibilidade das integrações.

## Verificação

`tests/test_voice_deadlines.py` testa cancelamento de conversa silenciosa, próxima pergunta após falha, explicação ativa além do limite inicial, cancelamento de chamadas Fish travadas, corpo HTTP parado e ausência de blocos PCM. Prazos são reduzidos nos testes para reproduzir falhas sem esperar minutos.

`tools/check_conversation_latency_browser.py` testa nove cenários com interface compilada, servidor HTTP real, gravação sintética, SSE e reprodução WAV. Serviços externos são controlados. O cenário novo força falha de síntese e confere que o texto completo aparece. Nenhuma dessas medições certifica latência real da nuvem ou dispositivos físicos Windows.

Baixe o pacote completo pelo GitHub e extraia. Na nova pasta, use `MIGRAR-DADOS-DA-VERSAO-ANTIGA.bat` para copiar seus dados e depois `ABRIR-CRONOS.bat`. Mantenha a origem até conferir as memórias e integrações. Credenciais privadas não são publicadas no GitHub.

Resultado final: 660 testes Python passaram em 85,30 segundos, sem falhas; um aviso de depreciação da dependência HTTP de testes. Nove cenários de navegador passaram, incluindo falha de síntese com preservação do texto. TypeScript e compilação passaram. Consulte `VERIFICACAO-2026-10-29-R7.json`.
