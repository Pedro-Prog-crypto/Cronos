# Escuta contínua e mapa

Ao conectar a janela desktop, o microfone solicita acesso e abre automaticamente.
O botão original liga/desliga a escuta; pausas e respostas não o desligam.
Durante a fala do assistente, o stream permanece aberto, mas a transcrição fica
bloqueada para reduzir eco. Uma falha na permissão inicial pode exigir clicar
novamente depois de liberar o microfone nas configurações do Windows.

A captura local usa AudioWorklet, PCM mono de 16 kHz e pequenos buffers por frase.
Dispensa codificar WebM e decodificar novamente antes do Vosk nessa rota. Mantém
fallback para ambientes sem AudioWorklet. O início da síntese continua em trechos
com a voz Fish configurada; não substitui a voz personalizada. A espera real dos
provedores depende da conexão e da disponibilidade deles.

O desenho do núcleo permanece nos workers. Componentes estáveis evitam redesenhar
a árvore React a cada consulta de monitoramento; canvases ocultos pausam desenho.
Nenhuma animação foi removida. Isso não garante desempenho no Flash F30 sem medir
o programa no aparelho.

## Olho de Deus

Ordens como “Kronos, abrir olho de Deus”, “abra o olho de Deus” e “você pode abrir
o olho de Deus, por favor?” são ações locais da interface, sem chamada Gemini ou
busca nos arquivos. “Feche o olho de Deus” retorna à memória e desmonta o mapa 3D.
Depois de aberto, “abrir aeroporto Charles de Gaulle” ou “abrir cidade de São
Paulo” consulta a busca mundial e navega para o local. Perguntas informativas e
ordens negativas não abrem o mapa. O modo de privacidade local bloqueia serviços
externos. O mapa precisa de internet para imagens e localização.

A integração usa o visualizador Cesium do projeto original e navegação mundial;
não inclui todos os feeds de vigilância/dados do projeto upstream.

## Memória, configuração e diagnóstico

A espiral começa vazia e ganha pequenos círculos brancos conforme existem notas
Markdown reais. Linhas representam relações reais; não há notas de demonstração
no vault. Capturas de prévia com centenas de pontos usam dados simulados somente
no teste, sem preencher o Obsidian do usuário.

Importar a voz original preserva uma chave Gemini já configurada e seu modelo.
Erros HTTP futuros do Gemini deixam mensagem sanitizada em
`.cronos-local/last-gemini-error.json`, sem chave, pergunta ou corpo da resposta.
Após HTTP 429 há uma pausa local antes de tentar novamente, respeitando
Retry-After quando numérico. Essa pausa não renova cota nem muda plano/modelo.
O erro anterior que desapareceu não pode ser recuperado retroativamente.

## Abrir e atualizar

Preserve `.env` e o vault. Atualize a mesma pasta usada para iniciar o Kronos,
incluindo `cronos/ui` completo. Abra `Iniciar-Cronos.vbs` para iniciar sem prompt.
Não precisa reimportar a voz que já funciona. A instância Kronos é única;
WebView2 utiliza processos auxiliares do próprio Windows, portanto não é
literalmente um único processo no Gerenciador de Tarefas.

Validação de desenvolvimento: build/TypeScript, testes Python, comandos locais
e fluxo de voz em Chromium com entrada e provedores simulados. O teste do mapa
abre o Cesium real e verifica fechamento, sem validar imagens externas ao vivo.
Microfone físico, latência dos provedores e launcher Windows precisam ser
verificados no aparelho do usuário.
