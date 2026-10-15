# Gemini do Kronos original

A análise de `CRONOS-Original - Copia.zip` encontrou duas rotas distintas:
`main.py` conversa pela API Live, e `core/gemini.py` usa Live em sessões isoladas
para obter respostas por `output_audio_transcription`. A implementação anterior
do novo Kronos usava somente REST `generateContent`. Uma cota/indisponibilidade
de REST não determina a disponibilidade de Live.

O novo `cronos/gemini_live.py` adapta o fluxo original: SDK oficial google-genai,
API v1beta, `live.connect`, envio de turnos e leitura de transcrição da saída.
Os modelos foram extraídos do original, sem inventar IDs:

- Principal: `models/gemini-3.1-flash-live-preview`.
- Alternativa original: `models/gemini-2.5-flash-native-audio-preview-12-2025`.

Apenas a indisponibilidade de conexão/modelo permite tentar a alternativa; um
limite de uso Live não dispara outra geração. Erros são sanitizados e sessões
fecham ao concluir/falhar. O atraso/cooldown de REST não bloqueia a rota Live.
Live também possui limites e cobrança conforme a conta do provedor; a mudança
não ativa faturamento nem garante disponibilidade gratuita permanente.

A personalidade definida pelo usuário continua sendo enviada integralmente.
Não foi copiada a instrução `_ONE_SHOT_SYSTEM` do original que suprimia a
personalidade. Também não foram copiados scripts, plugins, respostas prontas,
mensagens proativas ou execução de comandos do sistema. Memória, ferramentas e
confirmação humana continuam no motor atual. O formato JSON permite persistir
os temas e executar ferramentas; a síntese final continua pela voz Fish escolhida.
O áudio nativo recebido por Live é descartado durante a leitura, sem guardar uma
gravação nem substituir a voz personalizada.

## Atualização Windows

Preserve `.env` e seu vault; atualize os arquivos do projeto na pasta correta.
Execute `Instalar-Cronos.bat` para instalar o SDK novo. Depois abra
`Iniciar-Cronos.vbs`. Se não existir `GEMINI_TRANSPORT` no `.env`, Live já é o
padrão. A configuração explícita é:

```dotenv
GEMINI_TRANSPORT=live
GEMINI_LIVE_MODEL=models/gemini-3.1-flash-live-preview
```

`GEMINI_MODEL` continua disponível para `GEMINI_TRANSPORT=rest`; ele não seleciona
o modelo Live. Selecionar um modelo REST na bancada muda a rota apenas para
aquela execução. Adaptadores adicionais Gemini do manifesto continuam em REST.
Diagnosticar-Cronos é uma consulta local; `--generate` solicita uma geração real
pela rota atualmente selecionada. Não há necessidade de reimportar a voz.

## Verificação

Uma chamada real Live retornou JSON válido com a personalidade. Uma conversa
real pelo endpoint `/chat` respondeu sobre Platão e criou uma nota Markdown em
vault temporário. Nenhum histórico/vault do usuário foi usado ou substituído.
Os testes automatizados cobrem protocolo, histórico, preservação de personalidade,
fechamento de recursos, alternativa original, pausa de cota Live e distinção de
429/503. Microfone, Fish e fluidez física no Windows não foram certificados por
esses testes; a interface não foi alterada nesta atualização.

## Proveniência

Fluxo adaptado de `core/gemini.py` e modelos de `main.py` do pacote enviado pelo
usuário. Original MARK LV — JARVIS, Copyright (c) 2026 FatihMakes, CC BY-NC 4.0.
Adaptação: integração de configuração, histórico, formato estruturado, proteção
de credenciais e memória do Kronos. Licença original preservada em
`cronos/licenses/ORIGINAL-KRONOS-LICENSE.txt`.

## Recuperação local de formato

A leitura das respostas agora preserva uma resposta válida quando apenas os metadados opcionais de memória falham, aceita objetos JSON cercados por Markdown e pedidos de ferramenta válidos sem narração. Isso também vale para os conectores REST/OpenAI compatível/Anthropic/Ollama. Nenhuma chamada extra é feita para corrigir o formato.

Na rota Live, uma resposta em linguagem natural só é aceita depois de o servidor confirmar o fim do turno. Nesse caso não são criadas ferramentas nem notas de memória. JSON malformado e comandos incompletos continuam recusados. Uma desconexão sem confirmação de fim não é tratada como resposta natural completa. Os últimos erros Live de formato também ficam registrados localmente no diagnóstico, sem guardar o conteúdo da pergunta/resposta.

Essas correções não resolvem erros de cota (429), serviço (503), chave ou modelo indisponível. Não mudam o modelo configurado nem a voz Fish. Testes dessa recuperação usam respostas simuladas; o erro específico do usuário depende da mensagem apresentada na instalação dele.
