# CRONOS Studio Pro — Fase 1

Esta entrega evolui o Studio existente. Mantém o editor, as integrações configuradas, o histórico, a prévia isolada e o exportador. A primeira missão verificável é uma pizzaria demonstrativa que aceita fotos próprias, produz um site responsivo e um pedido montável.

## Mapa do projeto existente

| Parte | Arquivos | Situação constatada |
|---|---|---|
| Interface do Studio | `frontend/src/components/SiteStudio.tsx`, `StudioVisuals.tsx` | Projetos, briefing, IA, revisão por conversa, assets, editor, prévia e exportação já existiam. |
| Rotas e geração | `cronos/studio/routes.py`, `service.py`, `provider_pool.py` | API autenticada, fallback de provedores configurados, validação e versões em SQLite. |
| Projetos e arquivos | `cronos/studio/store.py` | Projetos no cofre local; cada revisão preserva os três arquivos gerados. |
| Prévia e entrega | `cronos/studio/validation.py`, `bridge.js`, `features.js`, `runtime.py` | Prévia isolada, runtime de formulários e interações, ZIP com servidor local. |

## Implementado agora

- Modelo editorial original para pizzaria em `cronos/studio/pizza.py`: hero, cardápio, galeria e área de pedido; 12 sabores **fictícios e identificados como demonstração**.
- Fotos importadas com hash para evitar cópias idênticas, limite de 32 recursos por projeto e associação explícita ao sabor ou à abertura. O modelo não inventa fotos do negócio; imagens não vinculadas ainda aparecem na galeria.
- Carrinho com dois tamanhos e preços demonstrativos distintos, quantidades, remoção, observações e mensagem de WhatsApp preenchida a partir de número fornecido. Sem contato informado, o pedido externo fica indisponível.
- Comando de criação local da pizzaria dentro do Studio. A edição por conversa existente recebeu orientação para preservar os arquivos, fotos vinculadas e funções fora do pedido. Cada mudança validada cria revisão; o histórico anterior permanece.
- Prévia no navegador e ZIP editável com HTML, CSS, JavaScript, runtime, servidor local, imagens de produto e `asset-manifest.json` com origem, hash, vínculo e uso na página.

## Evidência de execução

O teste de API em `tests/test_studio_pizza.py` envia oito fotos sintéticas **apenas como dados de teste**, vincula cada uma a uma pizza, monta o site, revisa uma seção por provedor simulado e confere todos os arquivos exportados. O teste de navegador em `frontend/scripts/check-studio-pizza.py` aciona o botão real da interface, abre a prévia em 390, 768 e 1440 px, verifica 12 produtos, oito imagens carregadas, ausência de rolagem horizontal e de erros JavaScript, total por tamanho, observações no link do WhatsApp e funcionamento do ZIP em um servidor separado. As capturas geradas ficam em `outputs/studio-pizzaria-mobile.png` e `outputs/studio-pizzaria-desktop.png`.

As fotos sintéticas são blocos de cor para testar o fluxo técnico; **não representam a qualidade fotográfica final**. A composição visual deve ser julgada novamente com fotografias reais do cliente. Nenhuma geração com API paga, publicação em hospedagem externa ou execução no notebook Windows do usuário foi afirmada nesta fase. A disponibilidade de IA para edições depende da configuração e da cota dos provedores já integrados.

## Próximas fases da especificação

Seleção de um elemento na prévia, patch localizado com diff e teste de não regressão após cada edição pertencem à Fase 2. Direção de arte comparada entre nichos pertence à Fase 3. Publicação real, serviços comerciais e os demais requisitos continuam condicionados às fases da especificação; o botão de WhatsApp prepara uma mensagem, sem processar pagamento ou confirmar pedido.
