# Integração integral do material enviado para o Cronos Studio

Os oito anexos foram lidos e incorporados, incluindo os textos, modelos, gerador, catálogo e HTMLs enviados nesta conversa.

## Arquivos

- `cronos/studio/references.py`: as 17 referências originais, com textos, recursos, imagens, preços e paletas, sem retirar categorias ou variantes.
- `cronos/studio/catalog.py`: o catálogo enviado, mantendo as 13 categorias, geração inicial e ilustrações. As ligações ao compilador e à estimativa ficam explicitamente identificadas no código.
- `cronos/studio/threed/config.py`, `models.py`, `generator.py`, `pricing_config.py`, `__init__.py`: configurações, os três modelos completos, gerador e funções de preço/exportação do módulo enviado.
- `cronos/studio/threed/templates/basic.html`, `standard.html`, `premium.html`: os três templates. O básico foi reconstruído do bloco da mensagem; Standard e Premium mantêm os HTMLs anexados. A prévia aplica os dados da referência escolhida.
- `examples/3d-product-demo/index.html`: o exemplo completo dos fones. As três URLs de bibliotecas foram ligadas às cópias locais em `vendor/`, para permitir abrir o exemplo sem CDN.
- `cronos/studio/mistral_original/`: os **oito anexos sem alterações**, identificados por seus SHA-256. Os blocos de configuração, inicialização e template básico da mensagem também ficam documentados em arquivos separados. Eles foram formatados como código; não são anexos binários originais.
- `cronos/studio/legacy_catalog.py`: cópia do catálogo anterior para manter seu código disponível. Sites já salvos permanecem nas versões originais do cofre.

## Uso

Abra **ESTÚDIO DE SITES**. O catálogo mostra categorias, imagem de exemplo (ou composição de reserva se a fonte não carregar), preços da referência, tipo de template e paleta. No painel direito escolha a referência, a faixa de projeto, o template e, para 3D, o modelo procedural. O detalhe expansível mantém os recursos, textos e URLs de imagens que vieram no material.

**GERAR SITE AUTOMATICAMENTE** cria uma versão local com o template selecionado, sem consumir IA. O resultado é identificado como template; não é anunciado como trabalho personalizado de uma IA. Os comandos curtos **“Cronos, criar site para restaurante”** e **“Cronos, criar site 3D para imobiliária”** fazem essa criação local. Pedidos com briefing detalhado continuam no fluxo de personalização e aprovação pela IA.

Os três modelos são **fones com estojo**, **avião** e **edifício com dez andares, telhado, antena, entrada e janelas**. A cena usa a geometria completa de `models.py`, incluindo os elementos que a cópia simplificada dentro do gerador não desenhava. Há rotação, zoom, separação, restauração e transparência; fones também abrem/fecham o estojo, e o avião tem os controles de movimento. São modelos conceituais feitos com primitivas, não reproduções técnicas ou ultrarrealistas de um Buds comercial ou de um imóvel real.

O visualizador GLB anterior continua disponível para um arquivo real fornecido pelo usuário. Ele não é obrigatório para os modelos procedurais. Quando há GLB autorizado no projeto, a solicitação à IA dá preferência a ele; não pede dois visualizadores simultâneos.

## Preços

As quatro faixas do material estão disponíveis explicitamente:

| Faixa | Valor sugerido |
| --- | --- |
| Econômico / Basic 2D | R$200–500 |
| Standard 2D | R$1.000–4.000 |
| Premium 2D | R$4.000–5.000 |
| Premium 3D | R$5.000–15.000 |

As referências possuem suas próprias faixas, também preservadas: restaurante R$400–800, imobiliária 3D R$7.000–15.000, eventos 3D R$6.000–12.000, por exemplo. **Faixa da referência escolhida** usa esses valores; escolher um dos quatro níveis usa a faixa daquele nível. Um pedido explicitamente 3D requer a faixa 3D. Integrações comerciais adicionais continuam indicadas como escopo específico. As faixas são sugestões de proposta, não promessa de preço de mercado ou avaliação financeira de um estabelecimento.

## Correções e conexões necessárias

O material, sem correções, não compila ou não se conecta à prévia existente. As cópias exatas permitem comparar todas as mudanças:

1. `models.py` usava `DEFAULT_3D_SETTINGS` sem importar. O nome foi importado de `config.py`.
2. O JavaScript dos modelos tinha `const case`, palavra reservada, e `fuselagemGeometry`/`fuselagem` onde a variável declarada era `fuselageGeometry`/`fuselage`. Esses nomes foram corrigidos.
3. A f-string do gerador continha seis chaves de fechamento não escapadas. Foram escapadas para permitir importar o módulo.
4. O import relativo de referências no preço é atendido por `threed/references.py`. A função de preço agora respeita o argumento de nível, que antes era ignorado; hotel 2D não é transformado automaticamente em cobrança de modelo 3D.
5. O catálogo original retornava CSS com chaves duplicadas e `style` inline, incompatível com a prévia isolada. `threed/integration.py` separa HTML/CSS/JS e mantém as regras e paletas do material; não libera scripts arbitrários de sites gerados.
6. Os arquivos HTML continham alertas de envio fictício e controles de demonstração sem ligação com o runtime. O adaptador conecta contato e solicitação de horário ao servidor existente, acrescenta consentimento e nomes acessíveis, e liga os botões à cena completa. Não anuncia envio de e-mail, pagamento ou reserva confirmada.
7. Three.js 0.128.0, OrbitControls 0.128.0 e GSAP 3.11.4 são fornecidos localmente, com origem, hashes e arquivos de licença/README. As URLs originais permanecem nos fontes; a prévia/exportação não depende delas. As regras e condições das bibliotecas continuam aplicáveis.
8. As cenas medem o espaço do painel, limitam a densidade de pixels e o desenho a aproximadamente 30 quadros por segundo, respeitam redução de movimento e liberam recursos ao fechar. Nenhuma peça da geometria foi removida para isso.

Os scripts de cena são código conhecido deste módulo, isolado da aplicação. HTML/CSS/JS solicitados à IA continuam sujeitos aos validadores, iframe com origem opaca, CSP e proibição de acesso ao sistema. Somente as URLs literais de imagens do banco enviado são aceitas, além dos assets locais. O backend baixa essas fotografias com limite de tempo/tamanho, valida o formato e as incorpora à prévia/exportação; a página gerada continua sem permissão de acessar imagens remotas dinamicamente. Há cache limitado e composição de reserva se o download falhar; no modo local, não há download. URLs arbitrárias e scripts externos continuam recusados. Imagens externas podem estar fora do ar e seus direitos precisam ser conferidos antes de publicar; o material não fornece licenças de cada fotografia.

## Dados, reservas de IA e exportação

A atualização lê e preserva `.env`, integrações, personalidade, cofre, conversas e versões. Não migra ou apaga projetos antigos. O catálogo completo é retornado por `studio_status`, conforme solicitado.

A geração e revisão pela IA mantêm a troca automática entre todas as integrações configuradas e permitidas. Não há chamadas pagas na criação local por template. Cancelamento manual continua encerrando a tarefa. Geração de imagens continua sendo uma capacidade separada, com confirmação própria.

A exportação inclui a cena procedural e as bibliotecas usadas, além do runtime e dos formulários. Não inclui chaves, cofre, contatos da prévia nem o token do Cronos. O site exportado precisa ser aberto pelo `ABRIR-SITE.bat`/`server.py` para gravar formulários localmente. Publicação comercial, domínio, e-mail, pagamento, autenticação e estoque ainda exigem configuração específica; essas funcionalidades não são criadas por uma lista de recursos do template.

## Verificação

Os testes verificam todos os anexos originais, as 17 referências, os três templates, as quatro faixas e os três modelos. O navegador executa WebGL, rotação, zoom, separação/restauração, transparência, abertura/fechamento do estojo, telas de 390/1280 px, o comando curto e um ZIP em servidor HTTP independente com gravação real de contato. Modelos não fazem chamadas a CDN durante a prévia. Os provedores e fotos da galeria são fixtures identificadas; não se afirma teste pago de IA, disponibilidade real de todas as fotos nem execução no notebook Windows do usuário.
