"""Design starting points, not fabricated client work or commercial leads."""

from html import escape
from .threed.integration import wants_3d
from .references import get_reference, REFERENCE_SITES
from .threed.pricing_config import get_price_for_site, PRICING_TIERS, CATEGORY_PRICING

# =============================================================================
# 📚 CATÁLOGO DE CATEGORIAS
# =============================================================================

CATEGORIES = [
    ('restaurante', 'Restaurantes', 'gastronomia', '#d9ad65', 'SABORES', 'À mesa, o tempo ganha outro sabor.', 'Uma cozinha de encontros. Um lugar para ficar.'),
    ('hotel', 'Hotéis e pousadas', 'hospitalidade', '#c69459', 'AURORA', 'Existe um lugar entre a pausa e o extraordinário.', 'Dias mais leves. Memórias que ficam.'),
    ('lava_jato', 'Lava-jatos e estética', 'automotivo', '#29c5ff', 'PULSE', 'O cuidado está em cada detalhe.', 'Estética automotiva com precisão, do primeiro ao último toque.'),
    ('loja', 'Lojas e produtos', 'comércio', '#b0ebad', 'FORMA', 'Objetos que fazem parte da sua história.', 'Uma seleção feita para durar.'),
    ('clinica', 'Clínicas e saúde', 'saúde', '#68bcb1', 'VIVA', 'Cuidado que começa pela escuta.', 'Conheça a equipe, os serviços e as formas de atendimento.'),
    ('barbearia', 'Barbearias e beleza', 'beleza', '#ce956e', 'OFÍCIO', 'Seu estilo. Nossa atenção.', 'Um espaço de cuidado, com tempo reservado para você.'),
    ('academia', 'Academias e esporte', 'esporte', '#c2f45e', 'MOVIMENTO', 'Um próximo passo. Todos os dias.', 'Conheça o espaço e encontre a atividade que combina com você.'),
    ('imobiliaria', 'Imóveis e arquitetura', 'imóveis', '#c8b39b', 'HABITAR', 'Espaços para o que vem a seguir.', 'Arquitetura, escolhas e lugares para chamar de seus.'),
    ('educacao', 'Educação e cursos', 'educação', '#9da9ff', 'PRISMA', 'O mundo muda quando você aprende.', 'Conheça os programas e descubra seu próximo caminho.'),
    ('eventos', 'Eventos e experiências', 'eventos', '#ef90c2', 'PRESENÇA', 'Alguns momentos merecem acontecer.', 'Encontros pensados do começo ao último detalhe.'),
    ('portfolio', 'Portfólios e criativos', 'criativo', '#ffa17d', 'TRAÇO', 'Ideias ganham forma aqui.', 'Projetos, processos e novas possibilidades.'),
    ('servicos', 'Serviços profissionais', 'serviços', '#83b9ee', 'NEXO', 'Clareza para resolver o que importa.', 'Conheça o trabalho e converse sobre o seu projeto.'),
    ('personalizado', 'Projeto personalizado', 'personalizado', '#b79aff', 'ESTÚDIO', 'O próximo projeto começa com uma ideia.', 'Uma direção própria, construída a partir do seu objetivo.'),
]

CATEGORY_IDS = {x[0] for x in CATEGORIES}

# =============================================================================
# 💡 FUNÇÕES AUXILIARES
# =============================================================================

def get_recommendation(category: str, site_type: str, has_3d: bool = False) -> str:
    """
    Retorna uma recomendação com base na categoria e tipo de site.
    """
    recommendations = {
        "basic": "Site simples e profissional para começar. Ideal para negócios locais e pequenos empreendedores.",
        "standard": "Site com design personalizado e recursos avançados. Perfeito para negócios em crescimento.",
        "2d_enhanced": "Site 2D com animações e interatividade. Ideal para quem busca diferencial visual.",
        "3d": "Site 3D imersivo com modelos interativos. Perfeito para produtos premium e experiências únicas."
    }
    return recommendations.get(site_type, "Site personalizado conforme suas necessidades.")

# =============================================================================
# 💰 SISTEMA DE PREÇOS (NOVO!)
# =============================================================================

def _supplied_quote(category, brief):
    """
    Calcula o orçamento com base na categoria e brief.

    Nova lógica de preços:
    - Basic 2D: R$200-500 (sites simples)
    - Standard 2D: R$1.000-4.000 (sites com design personalizado)
    - Premium 2D: R$4.000-5.000 (sites 2D avançados)
    - Premium 3D: R$5.000-15.000 (sites 3D)

    Args:
        category: Categoria do site
        brief: Descrição do briefing

    Returns:
        Dicionário com informações de preço
    """
    text = brief.casefold()

    # Verificar por recursos 3D
    has_3d = wants_3d(text)

    # Verificar por recursos 2D avançados
    has_2d_enhanced = any(term in text for term in ['animações', 'animacoes', 'interativo', 'efeitos', 'parallax'])

    # Verificar por recursos complexos
    complex_features = [term for term in ['pagamento', 'estoque', 'login', 'marketplace', 'integração', 'multiunidade'] if term in text]

    # Determinar faixa de preço
    if has_3d:
        # Sites 3D: R$5.000-15.000
        low, high = (5000, 15000)
        difficulty = 'Avançada'
        site_type = '3d'
    elif has_2d_enhanced or category in {'hotel', 'loja', 'imobiliaria', 'eventos'}:
        # Sites 2D avançados: R$4.000-5.000
        low, high = (4000, 5000)
        difficulty = 'Intermediária'
        site_type = '2d_enhanced'
    elif complex_features or category in {'hotel', 'loja'}:
        # Sites padrão: R$1.000-4.000
        low, high = (1200, 4500)
        difficulty = 'Intermediária'
        site_type = 'standard'
    else:
        # Sites básicos: R$200-500
        low, high = (200, 500)
        difficulty = 'Inicial'
        site_type = 'basic'

    # Ajustar para categorias específicas
    if category == 'imobiliaria' and has_3d:
        low, high = (7000, 15000)
    elif category == 'eventos' and has_3d:
        low, high = (6000, 12000)
    elif category == 'personalizado' and has_3d:
        low, high = (8000, 15000)

    # Obter informações adicionais do pricing config
    price_info = get_price_for_site(category, quality="standard", has_3d=has_3d)

    return {
        'min': low,
        'max': high,
        'difficulty': difficulty,
        'site_type': site_type,
        'has_3d': has_3d,
        'has_2d_enhanced': has_2d_enhanced,
        'complex_features': complex_features,
        'assumptions': [
            'Estimativa de proposta, não preço de mercado nem orçamento do cliente.',
            'Conteúdo, licenças, hospedagem, manutenção e integrações devem ser combinados.',
            'Não há informação suficiente para estimar a capacidade financeira do negócio.'
        ],
        'not_included': [
            'Pagamento real, autenticação de clientes e integrações comerciais exigem backend específico, credenciais e revisão antes de publicar.'
        ],
        'recommendation': get_recommendation(category, site_type, has_3d),
        'tier': price_info['tier'],
        'tier_name': price_info['tier_name'],
        'pricing_features': price_info['features']
    }

# =============================================================================
# 📚 CATÁLOGO COMPLETO (INTEGRADO COM REFERÊNCIAS E PREÇOS)
# =============================================================================

def catalog():
    """
    Retorna o catálogo completo de categorias com informações enriquecidas.

    Agora inclui:
    - Informações de referência (template, preços, recursos)
    - Informações de preços por tier
    - Textos e imagens de exemplo
    - Esquema de cores
    """
    catalog_items = []

    for key, label, sector, color, name, title, desc in CATEGORIES:
        try:
            # Obter informação de referência
            ref_site = get_reference(key)
        except:
            # Se não tiver referência, usar valores padrão
            ref_site = REFERENCE_SITES.get("personalizado", None)
            if ref_site is None:
                # Criar referência padrão
                from dataclasses import dataclass
                @dataclass
                class TempRef:
                    template_type: str = "2d"
                    price_range: tuple = (500, 1000)
                    features: List[str] = ["Site padrão"]
                    sample_texts: Dict[str, str] = {"hero_title": title, "hero_description": desc}
                    sample_images: List[str] = []
                    color_scheme: Dict[str, str] = {"primary": color, "background": "#0f172a", "text": "#f8fafc"}
                    layout: str = "default"
                ref_site = TempRef()

        # Obter informação de preço
        has_3d = ref_site.template_type == '3d'
        price_info = get_price_for_site(key, quality="standard", has_3d=has_3d)

        # Determinar nível de dificuldade
        if ref_site.template_type == '3d':
            difficulty = 'Avançada'
        elif ref_site.template_type == '2d_enhanced':
            difficulty = 'Intermediária'
        else:
            difficulty = 'Inicial'

        catalog_items.append({
            'id': key,
            'name': label,
            'sector': sector,
            'color': color,
            'demo_name': name,
            'headline': title,
            'description': desc,
            'difficulty': difficulty,
            'features': ref_site.features if hasattr(ref_site, 'features') else ["Site padrão"],
            'demo': True,
            'template_type': ref_site.template_type if hasattr(ref_site, 'template_type') else '2d',
            'price_range': ref_site.price_range if hasattr(ref_site, 'price_range') else (500, 1000),
            'sample_texts': ref_site.sample_texts if hasattr(ref_site, 'sample_texts') else {"hero_title": title, "hero_description": desc},
            'sample_images': ref_site.sample_images if hasattr(ref_site, 'sample_images') else [],
            'color_scheme': ref_site.color_scheme if hasattr(ref_site, 'color_scheme') else {"primary": color, "background": "#0f172a", "text": "#f8fafc"},
            'pricing_tier': price_info['tier'],
            'tier_name': price_info['tier_name'],
            'estimated_price': ref_site.price_range[0],
            'min_price': ref_site.price_range[0],
            'max_price': ref_site.price_range[1],
            'layout': ref_site.layout if hasattr(ref_site, 'layout') else 'default'
        })

    from .threed.integration import enrich_catalog
    return enrich_catalog(catalog_items)

# =============================================================================
# 🏗️ TEMPLATE BASE CSS
# =============================================================================

BASE_CSS = """
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:2rem}
body{margin:0;background:BG_COLOR;color:TEXT_COLOR;font-family:Arial,sans-serif;--accent:ACCENT_COLOR;--line:rgba(255,255,255,.15);--bg-color:BG_COLOR;--text-color:TEXT_COLOR}
body.light{background:#f7f3ec;color:#242a28;--line:#242a2840}
a{color:inherit;text-decoration:none}
button,input,select,textarea{font:inherit;touch-action:manipulation}
button,a{cursor:pointer}
a:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible{outline:3px solid var(--accent);outline-offset:5px}
button{color:inherit}button:disabled{opacity:.5;cursor:wait}
.skip{position:absolute;left:1rem;top:-100px;background:var(--accent);color:BG_COLOR;padding:1rem;z-index:10}.skip:focus{top:1rem}
.top{display:flex;justify-content:space-between;align-items:center;gap:2rem;padding:28px 5vw;border-bottom:1px solid var(--line)}
.brand{font-size:25px;letter-spacing:.2em;font-weight:600}.brand span{display:block;font-size:8px;letter-spacing:.35em;font-weight:400;margin-top:7px}
.top nav{display:flex;align-items:center;gap:30px;font-size:12px}.nav-cta{border:1px solid var(--line);padding:12px 18px}
.hero{min-height:640px;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr)}
.hero-copy{padding:80px 5vw 30px;display:flex;flex-direction:column;align-items:flex-start;min-width:0}
.eyebrow{font-size:10px;text-transform:uppercase;letter-spacing:.22em;line-height:1.9;color:var(--accent)}
h1{font:400 clamp(38px,4.8vw,76px)/1.05 Georgia,serif;letter-spacing:-.055em;margin:25px 0;max-width:650px;overflow-wrap:anywhere}
h2{font:400 clamp(26px,3.3vw,46px)/1.15 Georgia,serif;letter-spacing:-.035em}h3{font:400 26px Georgia,serif}
.intro{font-size:14px;line-height:1.9;opacity:.8;max-width:350px}
.primary{display:inline-flex;align-items:center;justify-content:space-between;gap:30px;margin-top:24px;background:var(--accent);border:0;color:BG_COLOR;padding:18px 25px;font-size:12px;min-height:48px}
.edition{font-size:9px;letter-spacing:.16em;opacity:.7;margin-top:auto;padding-top:55px}
.hero-visual{min-height:540px;position:relative;overflow:hidden}.hero-visual img,.hero-visual svg{width:100%;height:100%;position:absolute;inset:0;object-fit:cover}
.visual-label{position:absolute;left:24px;bottom:24px;font-size:8px;letter-spacing:.18em;color:white;background:#071b1bbd;padding:10px}
.about{padding:90px 10vw;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,2fr) minmax(0,1.2fr);gap:40px;border-bottom:1px solid var(--line);align-items:start}.about h2{margin:0}.about p:last-child{font-size:12px;line-height:1.9;opacity:.8}
.experiences{padding:70px 5vw}.section-head{display:flex;align-items:end;justify-content:space-between;gap:40px}.section-head h2{max-width:520px}
.offers{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:35px;border-top:1px solid var(--line);margin-top:25px}
.offer{padding:30px 0;border-bottom:1px solid var(--line)}.offer>span{font-size:10px;color:var(--accent)}.offer p{font-size:12px;line-height:1.8;opacity:.8;max-width:300px}
.offer button{background:none;border:0;border-bottom:1px solid var(--line);padding:12px 0;width:100%;display:flex;justify-content:space-between;text-align:left;font-size:12px;min-height:44px}
.contact{padding:80px 8vw;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12vw;background:#ffffff06;border-top:1px solid var(--line)}.contact>div p:last-child{font-size:13px;line-height:1.8;max-width:360px;opacity:.8}
form{display:grid;gap:18px;min-width:0}label{display:flex;flex-direction:column;gap:8px;font-size:13px;min-width:0}
input,textarea,select{min-width:0;width:100%;min-height:44px;background:transparent;color:inherit;border:0;border-bottom:1px solid var(--line);padding:10px 0;border-radius:0}
select option{color:#111;background:white}textarea{min-height:90px;resize:vertical}
.consent{flex-direction:row;align-items:center;line-height:1.6}.consent input{width:17px;min-height:17px;flex:none;accent-color:var(--accent)}
[data-form-status]{font-size:12px;line-height:1.7;min-height:1em}
.booking{padding:70px 8vw;border-top:1px solid var(--line);display:grid;grid-template-columns:minmax(0,1fr) minmax(0,2fr);gap:50px}.booking form{grid-template-columns:repeat(2,minmax(0,1fr))}.booking .consent,.booking [data-form-status]{grid-column:1/-1}
footer{border-top:1px solid var(--line);padding:35px 5vw;display:flex;justify-content:space-between;align-items:center;gap:24px}footer p{font-size:10px;opacity:.8;max-width:280px;line-height:1.7}footer>a:last-child{font-size:12px}
.lava_jato h1,.academia h1{font-family:Arial,sans-serif;font-weight:700;text-transform:uppercase;letter-spacing:-.07em}.lava_jato .hero-visual{filter:hue-rotate(135deg)}.restaurante .hero-visual{filter:sepia(.35)}
@media(max-width:760px){
.top{padding:20px}.top nav{gap:15px}.top nav>a:not(:last-child){display:none}.brand{font-size:19px}.hero{grid-template-columns:1fr}.hero-copy{padding:45px 24px 30px}h1{font-size:52px;max-width:540px}.hero-visual{min-height:350px}.edition{padding-top:30px}.about{padding:45px 24px;grid-template-columns:1fr;gap:20px}.experiences{padding:45px 24px}.section-head{display:block}.offers{grid-template-columns:1fr;gap:0}.offer{padding:24px 0}.contact,.booking{padding:45px 24px;grid-template-columns:1fr;gap:30px}.booking form{grid-template-columns:1fr}.booking .consent,.booking [data-form-status]{grid-column:auto}footer{padding:28px 24px;flex-wrap:wrap}footer p{order:3;max-width:none}
}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{animation:none!important;transition:none!important}}
"""

# =============================================================================
# 🏗️ FUNÇÃO STARTER (GERADOR DE SITES INICIAIS)
# =============================================================================

def starter(category='restaurante', name='', assets=(), brief='', reference_id=''):
    """
    Gera um site inicial para uma categoria específica.

    INTEGRAÇÃO COM:
    - references.py: Templates pré-construídos
    - pricing_config.py: Cálculo de preços

    Args:
        category: Categoria do site
        name: Nome do negócio
        assets: Tupla de paths de assets
        brief: Briefing do usuário

    Returns:
        Dicionário com arquivos HTML, CSS e JS
    """
    # Obter informações da categoria
    record = next((r for r in CATEGORIES if r[0] == category), CATEGORIES[0])
    key, label, sector, color, demo_name, title, desc = record

    # Obter site de referência
    try:
        ref_site = get_reference(reference_id or category)
    except:
        # Se não encontrar, usar padrão
        from .references import REFERENCE_SITES
        ref_site = REFERENCE_SITES.get(category, REFERENCE_SITES["personalizado"])

    # Obter informações de preço
    has_3d = wants_3d(brief)
    price_info = get_price_for_site(category, quality="standard", has_3d=has_3d)

    # Determinar tipo do site
    if has_3d:
        site_type = '3d'
    elif ref_site.template_type == '3d':
        site_type = '3d'
    else:
        site_type = ref_site.template_type

    # Usar nome do referência se não fornecido
    name = escape(name or demo_name, quote=True)

    # Usar textos de exemplo do referência
    sample_texts = ref_site.sample_texts
    hero_title = escape(sample_texts.get('hero_title', title), quote=True)
    hero_subtitle = escape(sample_texts.get('hero_subtitle', ''), quote=True)
    hero_description = escape(sample_texts.get('hero_description', desc), quote=True)
    cta_button = escape(sample_texts.get('cta_button', 'Saber mais'), quote=True)

    # Usar esquema de cores do referência
    color_scheme = ref_site.color_scheme
    bg_color = color_scheme.get('background', color)
    text_color = color_scheme.get('text', '#f4f0e6')
    accent_color = color_scheme.get('primary', color)

    # Determinar se é hotel ou tema claro
    hotel = key in {'hotel', 'imobiliaria'}
    light = hotel or key in {'clinica', 'educacao'}
    about_headlines = {
        'restaurante': 'Uma cozinha lembrada pelo que chega à mesa.',
        'hotel': 'O lugar também faz parte da viagem.',
        'lava_jato': 'Cuidado visível nos detalhes do veículo.',
        'loja': 'Uma seleção construída em torno dos produtos.',
        'clinica': 'Informação clara para uma escolha de cuidado.',
        'barbearia': 'Atendimento com tempo para cada pessoa.',
        'academia': 'Movimento que encontra espaço na rotina.',
        'imobiliaria': 'Espaços apresentados com atenção à arquitetura.',
        'educacao': 'Um caminho de aprendizagem começa pela curiosidade.',
        'eventos': 'Cada encontro começa com uma boa ideia.',
        'portfolio': 'Um olhar sobre o trabalho e as decisões por trás dele.',
        'servicos': 'Uma apresentação direta do trabalho e da equipe.',
        'personalizado': 'Uma direção criada a partir do objetivo do projeto.',
    }
    about_headline = about_headlines.get(key, about_headlines['personalizado'])

    # Obter recursos do referência
    features = ref_site.features[:3]
    if not features:
        features = ['Conheça o trabalho', 'Escolha seu caminho', 'Converse com a equipe']

    # Gerar cards de recursos
    cards = ''.join(
        f'<article class="offer"><span>0{i+1}</span><h3>{escape(feature)}</h3><p>Serviço de qualidade para seu negócio.</p><button type="button" data-service="{escape(feature)}">Saber mais <b aria-hidden="true">↑</b></button></article>'
        for i, feature in enumerate(features)
    )

    # Tratar visual - usar assets se fornecidos, senão usar imagens do referência
    if assets:
        visual = f'<img src="assets/{escape(assets[0])}" alt="Imagem de apresentação fornecida para o projeto">'
    elif ref_site.sample_images:
        first_image = ref_site.sample_images[0]
        visual = f'<img src="{escape(first_image)}" alt="Imagem de demonstração do {escape(label)}">'
    else:
        visual = illustration(key)

    # Gerar HTML com dados do referência
    html = f'''<!doctype html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{name} — {escape(label)}</title><meta name="description" content="{hero_description}"><link rel="stylesheet" href="styles.css"><script src="app.js" defer></script></head><body class="{'light' if light else 'dark'} {key}" style="--bg-color:{bg_color};--text-color:{text_color};--accent-color:{accent_color};"><a class="skip" href="#main">Ir para o conteúdo</a><header class="top"><a class="brand" href="#main">{name}<span>{escape(sector.upper())}</span></a><nav aria-label="Principal"><a href="#experiencias">{'Acomodações' if hotel else 'Conheça'}</a><a href="#sobre">Nossa essência</a><a class="nav-cta" href="#contato">Vamos conversar ↑</a></nav></header><main id="main"><section class="hero"><div class="hero-copy"><p class="eyebrow">{escape(sector)} / uma nova perspectiva</p><h1>{hero_title}</h1><p class="intro">{hero_description}</p><a class="primary" href="#experiencias">{cta_button} <span>↑</span></a><p class="edition">01 / Site gerado por Cronos Studio - Faixa de preço: R${price_info['final_price']:,.2f} ({price_info['tier_name']})</p></div><div class="hero-visual">{visual}<span class="visual-label">DESIGN DE DEMONSTRAÇÃO · CRONOS STUDIO</span></div></section><section id="sobre" class="about"><span class="eyebrow">Nossa essência</span><h2>{escape(about_headline)}</h2><p>Esta proposta mostra a direção visual do negócio. Confirme serviços, horários, endereço, imagens e demais informações com o responsável antes de publicar.</p></section><section id="experiencias" class="experiences"><div class="section-head"><p class="eyebrow">Feito para descobrir</p><h2>{'Escolha o seu próximo amanhecer.' if hotel else 'Encontre o que combina com você.'}</h2></div><div class="offers">{cards}</div></section><section id="contato" class="contact"><div><p class="eyebrow">Comece uma conversa</p><h2>Vamos cuidar<br>do próximo passo.</h2><p>Os envios são registrados neste site. Uma solicitação de horário depende da confirmação da equipe.</p></div><form data-studio-form="contact"><label>Seu nome<input name="name" autocomplete="name" maxlength="100" required></label><label>E-mail<input type="email" name="email" autocomplete="email" maxlength="180" required></label><label>Telefone (opcional)<input name="phone" type="tel" autocomplete="tel" maxlength="32"></label><label>Como podemos ajudar?<textarea name="message" maxlength="3000" required></textarea></label><label class="consent"><input type="checkbox" name="consent" required>Concordo com o uso dos dados para responder à minha solicitação.</label><button class="primary" type="submit">Enviar mensagem <span>↑</span></button><p data-form-status role="status"></p></form></section><section class="booking"><div><p class="eyebrow">Seu tempo reservado</p><h2>Solicite um horário.</h2></div><form data-studio-form="booking"><label>Nome<input name="name" maxlength="100" required></label><label>E-mail<input name="email" type="email" maxlength="180" required></label><label>Serviço<select name="service">{''.join(f'<option>{escape(feature)}</option>' for feature in features)}</select></label><label>Data<input name="date" type="date" required></label><label>Horário<input name="time" type="time" required></label><label class="consent"><input name="consent" type="checkbox" required>Autorizo contato para confirmar esta solicitação.</label><button type="submit" class="primary">Solicitar horário <span>↑</span></button><p data-form-status role="status"></p></form></section></main><footer><a class="brand" href="#main">{name}</a><p>Projeto de demonstração · confira dados e política de privacidade antes de publicar.</p><a href="#contato">Contato ↑</a></footer></body></html>'''

    # Gerar CSS com esquema de cores do referência
    css = BASE_CSS.replace('BG_COLOR', bg_color).replace('TEXT_COLOR', text_color).replace('ACCENT_COLOR', accent_color)

    # Gerar JS
    js = '''document.querySelectorAll('[data-service]').forEach(button=>button.addEventListener('click',()=>{const field=document.querySelector('[name="message"]');if(field){field.value='Quero saber mais sobre '+button.dataset.service+'.';document.querySelector('#contato').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});field.focus({preventScroll:true});}}));document.querySelectorAll('input[type="date"]').forEach(input=>{const d=new Date();input.min=[d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');});'''

    from .threed.integration import normalize
    return normalize({'index.html': html, 'styles.css': css, 'app.js': js})


def quote(category, brief, tier='reference', reference=''):
    from .threed.integration import estimate
    return estimate(category, brief, _supplied_quote(category, brief), tier=tier, reference=reference)

# =============================================================================
# 🎨 ILUSTRAÇÕES VETORIAIS (FALLBACK)
# =============================================================================

def illustration(category):
    """Ilustração vetorial original do estúdio."""
    if category == 'restaurante':
        content = '<rect width="760" height="700" fill="#14201a"/><path d="M0 0H760V700H0z" fill="url(#grain)"/><circle cx="410" cy="375" r="258" fill="#0c1710" stroke="#9b8b55" stroke-width="3"/><circle cx="410" cy="375" r="233" fill="#17251a" stroke="#625736" stroke-width="1"/><ellipse cx="410" cy="385" rx="160" ry="140" fill="#a77d3e"/><path d="M290 370Q400 200 535 357Q600 445 470 489Q370 510 280 411" fill="#d8ab61"/><path d="M310 350Q400 260 500 345M310 380Q425 290 520 389M330 410Q450 350 500 425" fill="none" stroke="#78572a" stroke-width="14"/><path d="M340 305Q220 260 265 190Q360 190 340 305M440 290Q425 190 500 204Q540 270 440 290M510 455Q585 432 603 494Q540 537 510 455" fill="#426b35"/><ellipse cx="350" cy="403" rx="15" ry="8" fill="#c9532e"/><ellipse cx="475" cy="339" rx="15" ry="8" fill="#b94625"/><path d="M705 190V610M675 190V275H705M690 190V275M100 190V610M83 190V290Q100 320 117 290V190" stroke="#b6a472" stroke-width="9" fill="none"/>'
    elif category == 'lava_jato':
        content = '<rect width="760" height="700" fill="#06182d"/><path d="M0 590 760 300M0 680 760 390" stroke="#37c8ff" stroke-width="2" opacity=".4"/><path d="M0 260 760 40M0 290 760 70" stroke="#193c5d" stroke-width="45"/><ellipse cx="430" cy="552" rx="300" ry="42" fill="#010e1d"/><path d="M85 440 215 340Q250 285 452 295L590 365 690 425 700 505 100 525 55 480Z" fill="url(#metal)" stroke="#5f8fae" stroke-width="2"/><path d="M230 345Q300 303 440 310L535 360 210 383Z" fill="#091b2b" stroke="#7d9fba"/><path d="M95 446 205 425 218 445 95 465M577 412 680 439 679 456 580 435" stroke="#c1f8ff" stroke-width="6" fill="#4fb7d4"/><circle cx="211" cy="507" r="54" fill="#07121d" stroke="#172e43" stroke-width="9"/><circle cx="211" cy="507" r="31" fill="#5a7891"/><circle cx="211" cy="507" r="18" fill="#142c42"/><circle cx="571" cy="490" r="54" fill="#07121d" stroke="#172e43" stroke-width="9"/><circle cx="571" cy="490" r="31" fill="#5a7891"/><circle cx="571" cy="490" r="18" fill="#142c42"/><path d="M345 388 345 467 490 460 485 378M350 402H390" stroke="#365773" fill="none" stroke-width="3"/>'
    else:
        content = '<rect width="760" height="700" fill="#18323b"/><circle cx="580" cy="190" r="230" fill="#365b65"/><path d="M0 500 760 80V700H0" fill="#244855"/><path d="M180 240 470 140 610 440 320 555Z" fill="#bad1c7"/><path d="M180 240 320 555 210 595 60 280Z" fill="#5e9295"/><path d="M180 240 60 280 350 180 470 140Z" fill="#e8e5d3"/><path d="M230 300 465 220M255 345 490 265M280 390 515 310" stroke="#477980" stroke-width="5"/><circle cx="535" cy="520" r="90" fill="#d5b584"/><circle cx="535" cy="520" r="64" fill="#b48c56"/><path d="M100 550H390M135 590H425" stroke="#91b4b3" stroke-width="2" opacity=".5"/>'

    return '<svg viewBox="0 0 760 700" role="img" aria-label="Ilustração vetorial original do estúdio"><defs><linearGradient id="grain" x2="1" y2="1"><stop stop-color="#30402b" stop-opacity=".4"/><stop offset="1" stop-color="#040e09" stop-opacity=".9"/></linearGradient><linearGradient id="metal" x2=".5" y2="1"><stop stop-color="#92aabb"/><stop offset=".3" stop-color="#456c8a"/><stop offset=".6" stop-color="#0f2d47"/><stop offset="1" stop-color="#04101f"/></linearGradient></defs>' + content + '</svg>'
