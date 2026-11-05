# Cronos R38 — fala e Studio de Sites

- A prévia da fala começa com o navegador e inicia o reconhecedor local após 0,5 s sem palavras. Quando o navegador reconhece, sua legenda prevalece. No modo online, a hipótese local é apenas provisória: a gravação completa segue para Fish/Gemini antes de virar pergunta. O modo privado usa só o modelo local.
- A transcrição online dá prioridade aos reconhecedores em nuvem configurados; o Vosk é reserva após falha deles. O modelo português local é aquecido em segundo plano na abertura, inclusive quando a opção de responder apenas após chamada está ligada.
- O Studio verifica se o serviço e o modelo Ollama locais existem antes de marcá-lo pronto no seletor. Após falha de todos os provedores, mostra os motivos e o acesso direto a Integrações. Erros 401 exigem chave válida; 429 exigem cota disponível. O código não declara um site criado por IA quando nenhum modelo entregou uma versão validada.
- O instalador de um arquivo atualiza apenas código e interface, preservando as credenciais, projetos e memórias da instalação escolhida.

Verificação: suíte completa de Python, compilação TypeScript/Vite, simulações de transcrição parcial e instalação do pacote. Microfone físico do usuário e validade das chaves externas não são verificáveis neste ambiente.
