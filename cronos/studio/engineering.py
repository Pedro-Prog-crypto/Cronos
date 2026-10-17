"""Executable delivery contracts, independent of a provider's self-assessment.

This is a finite capability registry, not a claim to understand every request.
Unknown requirements stay in the full brief sent to the model and need review.
"""
import re
import unicodedata
from html.parser import HTMLParser

FEATURES = {
    'search': ('Busca no conteúdo', r'\b(?:busca|buscar|pesquisa|pesquisar|buscador)\b', 'data-collection-search'),
    'filter': ('Filtro por categoria', r'\b(?:filtro|filtros|filtrar|filtragem)\b', 'data-collection-filter'),
    'sort': ('Ordenação dos itens', r'\b(?:ordenacao|ordenar|ordene|classificar por preco)\b', 'data-collection-sort'),
    'cart': ('Carrinho de demonstração', r'\b(?:carrinho|sacola)\b', 'data-studio-cart'),
}
DEPENDENCIES = {
    'payment': ('Pagamento real', r'\b(?:pagamento|pagamentos|checkout|pix|cartao de credito)\b', 'É preciso conectar um provedor de pagamento e validar valores no servidor; o site não pode confirmar uma compra sozinho.'),
    'accounts': ('Contas de clientes', r'\b(?:login|autenticacao|contas de clientes|area do cliente)\b', 'Exige autenticação e autorização no servidor. Não criar senhas, sessão ou login fictício como se fossem reais.'),
    'inventory': ('Estoque e entrega', r'\b(?:estoque|frete|rastreio|rastreamento)\b', 'Dados reais de estoque e entrega precisam de serviço próprio. Não prometer disponibilidade ou rastreio inventados.'),
    'persistence': ('Carrinho salvo entre visitas', r'\b(?:persistencia|persistente|salvar carrinho|carrinho salvo|manter carrinho)\b', 'O carrinho interno dura enquanto a página está aberta; persistência entre visitas não está conectada.'),
}


def folded(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value.lower()) if unicodedata.category(c) != 'Mn')


def mentions(text, pattern):
    """Return last explicit polarity; a negation in another sentence is not global."""
    result = None
    for clause in re.split(r'[.!?;\n]+|\b(?:mas|porem)\b', folded(text)):
        for match in re.finditer(pattern, clause):
            prefix = clause[max(0, match.start()-55):match.start()]
            negative = re.search(r'\b(?:sem|retire|remova|remover|tirar|dispense|desative)\b|\b(?:nao|nunca)\s+(?:quero|inclua|incluir|coloque|tenha|preciso|precisa|use|usar|adicione|adicionar|implemente|deve|ter)\b', prefix)
            preserve = re.search(r'\b(?:(?:nao|nunca)\s+(?:remov\w*|retir\w*|tir\w*|desativ\w*|exclu\w*|alter\w*|mud\w*|perc\w*|apag\w*)|sem\s+(?:alter\w*|mud\w*|remov\w*|perder))\b', prefix)
            # "não apenas busca, mas filtros" still requests search.
            result = bool(preserve) or not bool(negative) or bool(re.search(r'nao\s+(?:apenas|so|somente)', prefix))
    return result


def plan(project, request, previous=None):
    previous = previous or {}
    wanted = {item['id'] for item in previous.get('features', []) if item.get('id') in FEATURES}
    pending = {item['id'] for item in previous.get('dependencies', []) if item.get('id') in DEPENDENCIES}
    # A revision request takes precedence over the original brief. No silent loss
    # of accepted features when the user asks only for a colour/typography change.
    for target, registry in ((wanted, FEATURES), (pending, DEPENDENCIES)):
        for key, (_, pattern, *_) in registry.items():
            state = mentions(project.get('brief', ''), pattern) if not previous else None
            update = mentions(request, pattern)
            if update is not None: state = update
            if state is True: target.add(key)
            elif state is False: target.discard(key)
    minimum = previous.get('minimum_items', 0) if wanted else 0
    for text in ((project.get('brief','') if not previous else ''), request):
        counts=re.findall(r'\b(\d{1,4})\s+(?:produtos?|itens|pratos?|servicos?)\b', folded(text))
        if counts and wanted: minimum=max(1,int(counts[-1]))
    # A web search requested as research is not an on-page search component.
    if 'search' in wanted and not previous and re.search(r'\b(?:pesquise|pesquisar|busque|buscar)\b.{0,35}\b(?:imagens|fotos|referencias|internet|web)\b', folded(request)) and not re.search(r'\b(?:busca|buscador|barra de pesquisa)\b', folded(project.get('brief','')+' '+request)):
        wanted.discard('search')
    forms=set(previous.get('forms', ['contact']))
    if not previous and project.get('category') in {'restaurante','hotel','clinica','salao','servicos'}: forms.add('booking')
    for text in ((project.get('brief','') if not previous else ''),request):
        booking=mentions(text,r'\b(?:reserva|reservas|agendamento|agendamentos|solicitacao de horario)\b')
        if booking is True: forms.add('booking')
        elif booking is False: forms.discard('booking')
        if re.search(r'\bsem formularios?\b',folded(text)): forms.clear()
    advanced = previous.get('level')=='advanced' or project.get('tier') in {'standard','premium_2d','premium_3d'} or len(wanted) >= 2 or bool(re.search(r'\b(?:premium|avancado|intermediario)\b', folded(project.get('brief','')+' '+request)))
    return {
        'version': 1, 'level': 'advanced' if advanced else 'standard',
        'minimum_items': minimum, 'forms': sorted(forms),
        'blockers': ['O pedido exige '+str(minimum)+' itens. A coleção interna aceita até 200; reduza a seleção ou planeje um catálogo paginado com backend antes de construir.'] if minimum>200 else [],
        'features': [{'id': key, 'label': FEATURES[key][0]} for key in FEATURES if key in wanted],
        'dependencies': [{'id': key, 'label': DEPENDENCIES[key][0], 'detail': DEPENDENCIES[key][2]} for key in DEPENDENCIES if key in pending],
        'steps': ['Definir a composição a partir da direção aprovada e do público.',
                  'Construir hierarquia, imagens, estados vazios e comportamento no celular.',
                  'Ligar as funções do pedido e mostrar pendências reais.',
                  'Revisar estrutura e regressões; testar interações no navegador.'],
        'performance': {'max_collection_items': 200, 'motion': 'Curta e opcional; respeitar redução de movimento. 3D somente se solicitado; sem animações pesadas contínuas.'},
        'coverage': 'Verificações automáticas cobrem os componentes listados e a estrutura. Pedidos fora desse conjunto continuam no briefing e exigem revisão específica; não há garantia universal.'
    }


CONTRACT = '''engineering_plan é o contrato verificável deste pedido. Preserve suas funções ao revisar.
Para search/filter/sort/cart use os componentes internos abaixo; o runtime conecta as interações,
sem forçar composição, cores ou textos. NÃO duplique esses handlers no app.js. Você cria o design.
Coleção: um contêiner data-studio-collection com itens de id único data-item="id",
data-title="Nome", data-category="categoria", data-price="25.90" (valor decimal em reais).
Todos os itens são irmãos dentro de um contêiner próprio; até 200 itens, sem modelos fictícios de negócio real.
Se search: input data-collection-search com label. Se filter: select data-collection-filter com
option value="" para Todos e valores correspondentes a data-category. Se sort: select
data-collection-sort com opções default, price-asc, price-desc, name. Uma busca/filtro age
na própria coleção, com estado vazio [data-collection-empty hidden role="status"] e contador
[data-collection-count role="status"]. Crie os estados vazios e o estilo [hidden]{display:none!important}.
Se cart: somente uma coleção. Cada item tem button type="button" data-cart-add e data-price
numérico. Fora da coleção, um painel data-studio-cart com data-cart-items (ul),
data-cart-total (output) e data-cart-count (span); no painel avise claramente que é demonstração,
sem compra ou pagamento conectado. O runtime cria li.studio-cart-row, span, botões de aumentar,
diminuir e remover, com nomes acessíveis. Estilize .studio-cart-row e seus botões em styles.css.
Carrinho funciona nesta página; não persiste ao recarregar. Não mostre checkout de mentira.
O runtime deve ter conteúdo já no HTML: não crie os itens dinamicamente nem mova seus contêineres.
FAQ pode usar details/summary nativos. Modais próprios têm nome, foco inicial, Escape e retorno de foco.
Inclua estados de carregamento/erro apenas para operações reais; sem indicadores fictícios de sucesso.
Contraste legível, foco visível, metas de descrição e um h1, navegação com destino real.
Preserve as funções que já estavam aprovadas quando a alteração pedir só aparência.
Não ignore uma função desconhecida: descreva a limitação no resumo, sem alegar que foi implementada.
engineering_plan.forms define quais formulários são necessários: contact e/ou booking. Não imponha
agendamento a uma loja de produtos, nem formulários quando a lista for vazia. Siga o contrato de campos.
Dependencies são conexões pendentes: explique cada uma no resumo em português; não prometa ativação.
'''


class Markup(HTMLParser):
    def __init__(self):
        super().__init__(); self.nodes = []; self.parents = []; self.stack = []
    def handle_starttag(self, tag, attrs):
        index = len(self.nodes)
        self.nodes.append((tag, dict(attrs))); self.parents.append(tuple(self.stack))
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
            self.stack.append(index)
    def handle_endtag(self, tag):
        for pos in range(len(self.stack)-1, -1, -1):
            if self.nodes[self.stack[pos]][0] == tag:
                del self.stack[pos:]; break
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs); self.handle_endtag(tag)


def review(files, contract):
    """Validate actual markup, not markers hidden in comments or AI claims."""
    doc = Markup(); doc.feed(files['index.html'])
    checks = []
    def add(name, ok, detail):
        checks.append({'name': name, 'status': 'passed' if ok else 'failed', 'detail': detail})
    features = {item['id'] for item in contract['features']}
    # Inspect registered components even if a model added one outside the brief.
    for key, (_, _, marker) in FEATURES.items():
        if any(marker in attrs for _, attrs in doc.nodes): features.add(key)
    if features:
        roots = [i for i, (_, a) in enumerate(doc.nodes) if 'data-studio-collection' in a]
        add('Coleções do pedido', bool(roots) and len(roots)<=8 and not any(other in doc.parents[root] for root in roots for other in roots) and (len(roots)==1 if 'cart' in features else True), 'Use data-studio-collection; carrinho aceita uma coleção por página.')
        item_ids = []
        for root in roots:
            children = [(i,t,a) for i,(t,a) in enumerate(doc.nodes) if root in doc.parents[i]]
            items = [(i,a) for i,t,a in children if 'data-item' in a]
            item_ids.extend(a['data-item'] for _,a in items)
            valid_items = bool(items) and len(items)<=200 and all(a.get('data-item','').strip() and a.get('data-title','').strip() and a.get('data-category','').strip() for _,a in items)
            same_parent = len({doc.parents[i] for i,_ in items})==1
            add('Itens identificados da coleção '+str(len(checks)),valid_items and same_parent,'De 1 a 200 itens irmãos, com data-item único, data-title e data-category.')
            if contract.get('minimum_items'):
                add('Quantidade de itens solicitada',len(items)>=contract['minimum_items'],str(contract['minimum_items'])+' itens exigidos pelo pedido; '+str(len(items))+' encontrados no HTML.')
            categories = {a.get('data-category') for _,a in items}
            for key in sorted(features-{'cart'}):
                marker=FEATURES[key][2]
                controls=[(i,t,a) for i,t,a in children if marker in a]
                ok=len(controls)==1
                if key=='search': ok=ok and controls[0][1]=='input' and controls[0][2].get('type','text') in {'text','search'}
                else:
                    ok=ok and controls[0][1]=='select'
                    options={a.get('value') for i,t,a in children if t=='option' and controls and controls[0][0] in doc.parents[i]}
                    ok=ok and ({'',*categories}<=options if key=='filter' else {'default','price-asc','price-desc','name'}<=options)
                add(FEATURES[key][0],ok,'Controle interno '+marker+' ligado a esta coleção; o comportamento é testado na prévia.')
            add('Estado vazio e contagem',all(any(marker in a for _,_,a in children) for marker in ('data-collection-empty','data-collection-count')),'Informe nenhum resultado e quantidade encontrada sem inventar itens.')
            if features & {'sort','cart'}:
                prices=[a.get('data-price','') for _,a in items]
                add('Valores numéricos dos itens',all(re.fullmatch(r'\d{1,7}(?:\.\d{1,2})?',p) for p in prices),'data-price decimal positivo ou zero em reais; sem conversão de texto monetário.')
            if 'cart' in features:
                add('Adicionar cada item ao carrinho',all(any('data-cart-add' in a and t=='button' and a.get('type')=='button' and item in doc.parents[i] for i,t,a in children) for item,_ in items),'Botão do runtime em cada item; sem envio de formulário.')
        add('IDs dos itens únicos',len(set(item_ids))==len(item_ids),'Identificadores repetidos misturam produtos e tornam a entrega inválida.')
        if 'cart' in features:
            panels=[i for i,(_,a) in enumerate(doc.nodes) if 'data-studio-cart' in a]
            add('Painel do carrinho',len(panels)==1 and all(any(marker in a and panels[0] in doc.parents[i] for i,(_,a) in enumerate(doc.nodes)) for marker in ('data-cart-items','data-cart-total','data-cart-count')),'Um painel com itens, total e contador; o navegador testa adicionar/remover e o cálculo.')
    if contract['level']=='advanced':
        add('Hierarquia e descrição da página',sum(t=='h1' for t,_ in doc.nodes)==1 and any(t=='meta' and a.get('name')=='description' and a.get('content','').strip() for t,a in doc.nodes),'Uma entrada principal e descrição específica da página; não certifica qualidade estética.')
        css=files['styles.css']
        add('Movimento com alternativa reduzida',not re.search(r'\b(?:animation|transition)\s*:',css) or 'prefers-reduced-motion' in css,'Se há movimento, styles.css oferece alternativa para quem pede redução.')
    return checks
