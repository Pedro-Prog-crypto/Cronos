# Contrato da API — v0.1

Todas as rotas de dados exigem `Authorization: Bearer <CRONOS_API_TOKEN>`.
`GET /health` é público e confirma apenas que o processo HTTP responde.
Esquema: `/openapi.json`. Documentação interativa: `/docs`.

Configure `CRONOS_CORS_ORIGINS` com a origin exata da interface, por exemplo
`http://localhost:5173`; múltiplas origins são separadas por vírgula. CORS fica
desabilitado por padrão.

## Conversa

`POST /chat`, JSON:

```json
{"message":"O que Sócrates defendia?","session_id":null}
```

Resposta:

```json
{
  "session_id":"UUID gerado pelo servidor",
  "reply":"Texto da resposta",
  "topics":["Sócrates"],
  "notes":["Temas/sócrates-identificador.md"]
}
```

Guarde e reutilize `session_id` para continuar; omita para começar outra
conversa. Limite: 16.000 caracteres. As notas são gravadas após uma resposta
válida do provedor. Esta versão não transmite respostas em streaming.

`GET /conversations/{session_id}` retorna `session_id` e `messages`, uma lista
de objetos com `role` (`user` ou `assistant`) e `content`.

## Voz

`POST /voice/speech`, JSON `{"text":"Olá, sou o Cronos."}`. Retorna bytes MP3
com `Content-Type: audio/mpeg`. Limite: 5.000 caracteres. Requer chave e ID da voz.

`POST /voice/transcribe`: áudio diretamente no corpo binário, por exemplo com
`Content-Type: audio/wav`. Limite: 10 MiB. Retorna `{"text":"transcrição"}`.
Formatos aceitos dependem do Fish Audio.

Fluxo da interface: gravar, transcrever, enviar texto a `/chat`, enviar a resposta
a `/voice/speech` e reproduzir o MP3. Permita continuar por texto se a voz falhar.

## Status e erros

`GET /status` informa provedor e presença de configurações sem revelar chaves.
Presença de chave não comprova acesso ao serviço.

- `401`: token ausente/incorreto.
- `413`: áudio acima do limite.
- `422`: entrada inválida.
- `503`: configuração ausente ou provedor de conversa indisponível.
- `502`: falha de síntese/transcrição.
- `500`: falha de acesso à memória/personalidade.

Erros usam o campo `detail`. Não reenvie automaticamente mensagens já respondidas
sem considerar duplicação e cobrança. O agente Windows é separado: ainda não há
rota de execução de comandos, sincronização de vault ou controle remoto.
