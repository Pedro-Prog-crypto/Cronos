# Nitidez do holograma R44

O canvas do holograma é dimensionado conforme a largura realmente exibida e a densidade de pixels da tela, limitado a 900 × 900 pixels para manter o custo de renderização previsível. O worker e o fallback usam a mesma medida. Uma mudança de tamanho remonta o canvas e recalcula o bitmap após 180 ms, sem reiniciar o sistema de voz.

No Chromium, a 1280 × 720, o bitmap mediu 430 × 430 em escala 1×, 860 × 860 em 2× e 900 × 900 em 3×. Em uma tela móvel 3×, ao mudar a largura de 390 para 430 pixels, passou de 768 × 768 para 847 × 847. Capturas sucessivas do canvas no worker e no fallback produziram quadros diferentes, confirmando animação contínua. A aparência final no Windows e o desempenho em hardware mais lento ainda precisam de verificação na instalação do usuário.
