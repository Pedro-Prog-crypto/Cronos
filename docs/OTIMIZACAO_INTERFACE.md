# Otimização da interface — 13/10/2026

A pergunta falada deixa de abrir a caixa de conversa e fecha uma caixa já aberta.
O histórico e a resposta por voz permanecem; o painel de texto pode ser aberto
explicitamente. A substituição dos painéis e da apresentação de textos pelo novo
card depende do desenho que o usuário ainda enviará. Nenhum card foi inventado.

## Mudanças

- O medidor do microfone/voz atualiza referências lidas pelo canvas. Não dispara
  uma renderização React de toda a cena a cada amostra (~20 vezes por segundo).
- As linhas e anéis luminosos fixos do painel direito são rasterizados numa imagem
  SVG em memória, recalculada em mudança de estado/hover. Pontos, trajetórias,
  animação contínua e resposta visual aos estados continuam presentes.
- Os pontos móveis usam gradientes luminosos em vez de duas convoluções gaussianas
  por ponto a cada quadro. O brilho do núcleo usa uma aura estática e bloom dinâmico
  em buffers de meia resolução. O passe nítido conserva os 20 filamentos e 120
  amostras existentes; não houve novo corte de fios.
- Núcleo e estrela têm orçamento de 30 Hz, sincronizado com requestAnimationFrame.
  O movimento usa tempo decorrido. Animações SVG dos trajetos continuam independentes.
- As 150 agulhas da estrela continuam animadas, usando o halo comum em vez de um
  blur separado para cada agulha.
- Busca/indexação e gravação de memória do turno usam threads, liberando o event
  loop do servidor durante o trabalho de disco. Não reduz por si só a demora
  dos provedores Gemini/Fish, nem modifica personalidade, modelos ou chaves.

## Verificação e limites

127 testes Python passaram; TypeScript e build passaram. Browser validou entrada
falada simulada, envio automático, reprodução de WAV previamente recebido,
memória atualizada, ausência de abertura automática da conversa, animações,
comandos locais, mapa Cesium e liberação ao fechar. IA/transcrição/texturas do
mapa foram simuladas; não é um teste físico de microfone ou APIs ao vivo.

Comparação Chromium headless 1920x1080, CPU desacelerada em 4x, 90 notas de exemplo,
janela de medição de 6 segundos, contando somente limpezas do canvas visível:

| Medida | Antes | Depois |
| --- | --- | --- |
| Quadros observados | 33 | 80 |
| Intervalo mediano | 186,5 ms | 74,7 ms |
| Intervalo percentil 95 | 232,9 ms | 93,1 ms |
| Tempo de tarefas do navegador | 6,107 s | 6,240 s |

A cadência melhorou, mas a carga extrema ainda saturou esse teste: não comprova
redução geral de CPU/RAM, 30 FPS nesse cenário, nem fluidez no Samsung Flash F30.
O teste de estresse não representa a GPU física do notebook. Medir no Windows
permanece necessário. Não houve promessa de tempo fixo para Gemini ou Fish.

A captura entregue ao usuário foi renderizada pelo build real, com um grafo de
90 notas/81 links de exemplo fornecido apenas ao browser. Esses dados NÃO são
salvos no vault nem são pontos predefinidos do programa. Vault vazio permanece
sem pontos. A disposição atual forma grupos; ainda não é a galáxia da referência.
