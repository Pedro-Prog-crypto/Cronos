# CRONOS Studio Pro — Fase 1

Esta entrega evolui o Studio existente. Mantém o editor, as integrações configuradas, o histórico, a prévia isolada e o exportador. A primeira missão verificável é uma pizzaria demonstrativa que aceita fotos próprias, produz um site responsivo e um pedido montável.

- **Branch/commit inicial:** `feat/studio-pro-phase1` / `7e66d82`. Ajustes posteriores ficam no mesmo histórico da branch.
- **Integrações operacionais verificadas:** API local autenticada, geração de revisão com provedor simulado, prévia Chromium, exportação e servidor local do site. Não houve chamada a um provedor de texto ou imagem externo.
- **Integrações externas não verificadas:** modelos cadastrados pelo usuário, WhatsApp real e hospedagem pública; dependem de credenciais, contato autorizado, cota e ambiente reais. O teste inspeciona o link de WhatsApp, sem enviar mensagem.
- **Gastos no teste:** zero chamadas a APIs pagas. O custo de uma geração real depende do provedor escolhido.
- **Desempenho:** testadas larguras de 390, 768 e 1440 px sem rolagem horizontal; tempos de carregamento e métricas de hardware do notebook não foram medidos.
- **Como abrir e restaurar:** no Studio, abra o projeto e a aba **Prévia**. Para recuperar uma edição anterior, escolha uma revisão no histórico existente e use a ação de restaurar. O site exportado inicia com `ABRIR-SITE.bat` no Windows ou `python server.py` em um terminal.
- **Próximo passo prioritário:** testar com fotos e dados comerciais reais e, na Fase 2, implementar seleção visual e diffs localizados com regressão automatizada.

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

Comandos executados nesta entrega: `npm --prefix frontend run lint` e `npm --prefix frontend run build` passaram; `.venv/bin/python -m pytest -q` terminou com **779 aprovados, 0 falhas** (nove avisos de dependências); `STUDIO_TEST_URL=http://127.0.0.1:8871 .venv/bin/python frontend/scripts/check-studio-pizza.py` passou. O ZIP completo e o atualizador também passaram na verificação interna de integridade e na suíte de instalação.

As fotos sintéticas são blocos de cor para testar o fluxo técnico; **não representam a qualidade fotográfica final**. A composição visual deve ser julgada novamente com fotografias reais do cliente. Nenhuma geração com API paga, publicação em hospedagem externa ou execução no notebook Windows do usuário foi afirmada nesta fase. A disponibilidade de IA para edições depende da configuração e da cota dos provedores já integrados.

## Próximas fases da especificação

Seleção de um elemento na prévia, patch localizado com diff e teste de não regressão após cada edição pertencem à Fase 2. Direção de arte comparada entre nichos pertence à Fase 3. Publicação real, serviços comerciais e os demais requisitos continuam condicionados às fases da especificação; o botão de WhatsApp prepara uma mensagem, sem processar pagamento ou confirmar pedido.
