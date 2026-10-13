# Cena cósmica e espiral

O fundo usa o PNG original enviado pelo usuário. Há 38 estrelas com brilho por opacidade e duas estrelas cadentes com ciclos de 29 e 43 segundos. Ao ocultar a janela, essas animações pausam. A árvore de funções está encostada à direita, com estrela, linhas e ícones estáticos; o holograma central conserva sua animação em um worker.

O cofre vazio não desenha pontos nem rastros. Cada nota real recebe um ponto branco pequeno; as cinco curvas crescem até os pontos existentes. Essas curvas são decoração da galáxia, não relações de conhecimento. As relações entre notas continuam sendo desenhadas separadamente a partir dos links reais. O desenho limita pontos e rastros a 1.200 notas para conter o custo gráfico; isso não remove notas do cofre.

Para conferir a aparência com 850 notas sintéticas e com um cofre vazio, execute `python frontend/scripts/preview-memory.py` em um ambiente com Playwright/Chromium. As capturas ficam em `.cronos-local/visual-preview`. Nenhuma nota de demonstração é gravada no Obsidian e nenhuma API de IA é chamada.

A redução de processamento foi verificada no navegador de testes. O desempenho físico do Samsung Flash F30 ainda precisa ser conferido no notebook. Os 12 painéis próprios estão descritos em [PAINEIS.md](PAINEIS.md).
