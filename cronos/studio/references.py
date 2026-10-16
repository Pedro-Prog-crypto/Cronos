"""
Referências de sites pré-construídos para o Cronos Studio
Contém templates, textos e configurações padrão para cada categoria
"""

from typing import Dict, Any, List
from dataclasses import dataclass
import json

@dataclass
class ReferenceSite:
    """Represents a reference site template"""
    category: str
    name: str
    template_type: str  # "2d", "2d_enhanced", "3d"
    price_range: tuple
    description: str
    features: List[str]
    sample_texts: Dict[str, str]
    sample_images: List[str]
    color_scheme: Dict[str, str]
    layout: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "name": self.name,
            "template_type": self.template_type,
            "price_range": self.price_range,
            "description": self.description,
            "features": self.features,
            "sample_texts": self.sample_texts,
            "sample_images": self.sample_images,
            "color_scheme": self.color_scheme,
            "layout": self.layout
        }

# =============================================================================
# 📚 BANCO DE DADOS DE REFERÊNCIAS (12 CATEGORIAS)
# =============================================================================

REFERENCE_SITES = {

    "restaurante": ReferenceSite(
        category="restaurante",
        name="Restaurante Clássico",
        template_type="2d",
        price_range=(400, 800),
        description="Template ideal para restaurantes, bares e cafés que buscam um site profissional e atraente.",
        features=[
            "Cardápio digital interativo",
            "Galeria de pratos com fotos",
            "Sistema de reservas online",
            "Integração com Google Maps",
            "Depoimentos de clientes",
            "Redes sociais integradas",
            "Design responsivo"
        ],
        sample_texts={
            "hero_title": "Sabores que Encantam",
            "hero_subtitle": "Cozinha Autoral",
            "hero_description": "Descubra um mundo de sabores em nosso restaurante. Receitas tradicionais reinventadas com ingredientes frescos.",
            "about_title": "Sobre Nós",
            "about_text": "Somos apaixonados por gastronomia. Nosso chef traz anos de experiência para criar pratos que encantam os sentidos.",
            "services_title": "Nossos Serviços",
            "cta_button": "Faça sua Reserva",
            "footer_text": "Restaurante [NOME] - O melhor da gastronomia local"
        },
        sample_images=[
            "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800",
            "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=800",
            "https://images.unsplash.com/photo-1551218808-94e220e084d2?w=800",
            "https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=800"
        ],
        color_scheme={
            "primary": "#D4A574",
            "secondary": "#8B4513",
            "background": "#2C1E1A",
            "text": "#F5F5F5",
            "accent": "#FFD700"
        },
        layout="restaurant_classic"
    ),

    "restaurante_premium": ReferenceSite(
        category="restaurante",
        name="Restaurante Premium",
        template_type="2d_enhanced",
        price_range=(2000, 4000),
        description="Template premium para restaurantes de alta gastronomia com animações e interatividade.",
        features=[
            "Cardápio digital com fotos em alta resolução",
            "Galeria 360° do ambiente",
            "Sistema de reservas com calendário",
            "Animações suaves",
            "Integração com delivery",
            "Menu interativo",
            "Design exclusivo"
        ],
        sample_texts={
            "hero_title": "Experiência Gastronômica",
            "hero_subtitle": "Alta Cozinha",
            "hero_description": "Viva uma experiência única de sabores. Nosso chef estrela cria pratos que são verdadeiras obras de arte.",
            "about_title": "Nossa História",
            "about_text": "Com mais de 10 anos de tradição, somos referência em gastronomia na região. Prêmios nacionais e internacionais.",
            "services_title": "Cardápio Especial",
            "cta_button": "Reserve sua Mesa",
            "footer_text": "Restaurante [NOME] - Alta gastronomia desde [ANO]"
        },
        sample_images=[
            "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800",
            "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=800",
            "https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=800"
        ],
        color_scheme={
            "primary": "#8B0000",
            "secondary": "#FFD700",
            "background": "#000000",
            "text": "#FFFFFF",
            "accent": "#D4AF37"
        },
        layout="restaurant_premium"
    ),

    "hotel": ReferenceSite(
        category="hotel",
        name="Hotel Standard",
        template_type="2d",
        price_range=(1200, 2500),
        description="Template para hotéis e pousadas que buscam um site profissional para atrair hóspedes.",
        features=[
            "Galeria de acomodações",
            "Sistema de reservas",
            "Visualização de quartos",
            "Localização e atrações",
            "Avaliações de hóspedes",
            "Fotos do ambiente",
            "Informações de contato"
        ],
        sample_texts={
            "hero_title": "Seu Refúgio",
            "hero_subtitle": "Conforto e Elegância",
            "hero_description": "Acomodações sofisticadas com vista para o mar. Experiência única de hospitalidade.",
            "about_title": "Sobre o Hotel",
            "about_text": "Localizado em [LOCAL], oferecemos as melhores acomodações com serviço de excelência.",
            "services_title": "Nossas Acomodações",
            "cta_button": "Reserve Agora",
            "footer_text": "Hotel [NOME] - O melhor da hospitalidade"
        },
        sample_images=[
            "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800",
            "https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=800",
            "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800"
        ],
        color_scheme={
            "primary": "#1E3A8A",
            "secondary": "#FBBF24",
            "background": "#F8FAFC",
            "text": "#1E293B",
            "accent": "#3B82F6"
        },
        layout="hotel_standard"
    ),

    "hotel_3d": ReferenceSite(
        category="hotel",
        name="Hotel 3D Premium",
        template_type="3d",
        price_range=(7000, 15000),
        description="Template 3D para hotéis que querem oferecer uma experiência imersiva aos clientes.",
        features=[
            "Tour virtual 3D do hotel",
            "Visualização 3D dos quartos",
            "Navegação interativa",
            "Galeria de fotos em alta resolução",
            "Sistema de reservas integrado",
            "Efeitos de luz realistas",
            "Animações suaves"
        ],
        sample_texts={
            "hero_title": "Viva a Experiência",
            "hero_subtitle": "Hotel [NOME]",
            "hero_description": "Explore nosso hotel em 3D. Veja cada detalhe das nossas acomodações antes de fazer sua reserva.",
            "about_title": "Nossa Estrutura",
            "about_text": "Conheça nossos quartos, áreas de lazer e serviços exclusivos com nosso tour virtual.",
            "services_title": "Acomodações",
            "cta_button": "Faça um Tour Virtual",
            "footer_text": "Hotel [NOME] - Experiência imersiva em 3D"
        },
        sample_images=[
            "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800",
            "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800",
            "https://images.unsplash.com/photo-1618773928121-c32242e63be3?w=800"
        ],
        color_scheme={
            "primary": "#3B82F6",
            "secondary": "#1E40AF",
            "background": "#0F172A",
            "text": "#F8FAFC",
            "accent": "#60A5FA"
        },
        layout="hotel_3d"
    ),

    "loja": ReferenceSite(
        category="loja",
        name="Loja Virtual",
        template_type="2d_enhanced",
        price_range=(1500, 3500),
        description="Template para lojas e-commerce que buscam vender produtos online.",
        features=[
            "Catálogo de produtos",
            "Carrinho de compras",
            "Filtros de busca",
            "Páginas de produtos detalhadas",
            "Avaliações de clientes",
            "Sistema de pagamentos",
            "Painel de administração"
        ],
        sample_texts={
            "hero_title": "Moda e Estilo",
            "hero_subtitle": "Coleção 2024",
            "hero_description": "Peças exclusivas para quem busca estilo e qualidade. Roupas, acessórios e calçados.",
            "about_title": "Sobre a Loja",
            "about_text": "Trabalhamos com as melhores marcas para oferecer produtos de alta qualidade.",
            "services_title": "Nossos Produtos",
            "cta_button": "Comprar Agora",
            "footer_text": "Loja [NOME] - Moda e estilo para você"
        },
        sample_images=[
            "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=800",
            "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=800",
            "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=800"
        ],
        color_scheme={
            "primary": "#EC4899",
            "secondary": "#BE185D",
            "background": "#FEF7ED",
            "text": "#1F2937",
            "accent": "#F9A8D4"
        },
        layout="ecommerce"
    ),

    "clinica": ReferenceSite(
        category="clinica",
        name="Clínica de Saúde",
        template_type="2d",
        price_range=(1000, 2000),
        description="Template para clínicas, consultórios e centros de saúde.",
        features=[
            "Apresentação da equipe médica",
            "Serviços oferecidos",
            "Agendamento de consultas",
            "Depoimentos de pacientes",
            "Localização e contato",
            "Informações sobre especialidades",
            "Blog de saúde"
        ],
        sample_texts={
            "hero_title": "Saúde e Bem-Estar",
            "hero_subtitle": "Cuidado que Faz a Diferença",
            "hero_description": "Equipe especializada em saúde e bem-estar. Tratamentos personalizados.",
            "about_title": "Nossa Equipe",
            "about_text": "Médicos especializados em diversas áreas para oferecer o melhor atendimento.",
            "services_title": "Nossos Serviços",
            "cta_button": "Agende sua Consulta",
            "footer_text": "Clínica [NOME] - Saúde e bem-estar para você"
        },
        sample_images=[
            "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=800",
            "https://images.unsplash.com/photo-1576091160399-112ba8d25d1f?w=800",
            "https://images.unsplash.com/photo-1582750433449-648ed127bb54?w=800"
        ],
        color_scheme={
            "primary": "#06B6D4",
            "secondary": "#0891B2",
            "background": "#F0F9FF",
            "text": "#0F172A",
            "accent": "#22D3EE"
        },
        layout="healthcare"
    ),

    "academia": ReferenceSite(
        category="academia",
        name="Academia de Ginástica",
        template_type="2d_enhanced",
        price_range=(1300, 2800),
        description="Template para academias, centros de esporte e fitness.",
        features=[
            "Aulas e horários",
            "Professores qualificados",
            "Planos de treino",
            "Matrícula online",
            "Depoimentos de alunos",
            "Galeria de fotos",
            "Vídeos de aulas"
        ],
        sample_texts={
            "hero_title": "Transforme seu Corpo",
            "hero_subtitle": "Resultados que Inspiram",
            "hero_description": "Alcance seus objetivos com nossos treinamentos personalizados.",
            "about_title": "Nossa Estrutura",
            "about_text": "Ambiente moderno com equipamentos de última geração.",
            "services_title": "Nossos Planos",
            "cta_button": "Matricule-se Agora",
            "footer_text": "Academia [NOME] - Seu corpo em forma"
        },
        sample_images=[
            "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800",
            "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=800",
            "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=800"
        ],
        color_scheme={
            "primary": "#10B981",
            "secondary": "#059669",
            "background": "#0F172A",
            "text": "#F0FDF4",
            "accent": "#34D399"
        },
        layout="fitness"
    ),

    "imobiliaria": ReferenceSite(
        category="imobiliaria",
        name="Imobiliária Standard",
        template_type="2d",
        price_range=(1500, 3000),
        description="Template para imobiliárias e corretores de imóveis.",
        features=[
            "Busca de imóveis",
            "Galeria de propriedades",
            "Filtros avançados",
            "Visualização de plantas",
            "Localização no mapa",
            "Contato com corretor",
            "Simulador de financiamento"
        ],
        sample_texts={
            "hero_title": "Encontre seu Lar",
            "hero_subtitle": "Imóveis para Todos os Estilos",
            "hero_description": "Casas, apartamentos, terrenos e muito mais. Encontre o imóvel perfeito para você.",
            "about_title": "Sobre a Imobiliária",
            "about_text": "Trabalhamos com as melhores opções do mercado imobiliário.",
            "services_title": "Nossos Imóveis",
            "cta_button": "Buscar Imóveis",
            "footer_text": "Imobiliária [NOME] - Seu sonho, nossa missão"
        },
        sample_images=[
            "https://images.unsplash.com/photo-1560472354-b33ff0c44a43?w=800",
            "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=800",
            "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?w=800"
        ],
        color_scheme={
            "primary": "#1F2937",
            "secondary": "#4B5563",
            "background": "#F9FAFB",
            "text": "#111827",
            "accent": "#3B82F6"
        },
        layout="real_estate"
    ),

    "imobiliaria_3d": ReferenceSite(
        category="imobiliaria",
        name="Imobiliária 3D Premium",
        template_type="3d",
        price_range=(7000, 15000),
        description="Template 3D para imobiliárias que querem mostrar imóveis de forma imersiva.",
        features=[
            "Tour virtual 3D dos imóveis",
            "Visualização 3D de plantas",
            "Navegação interativa",
            "Efeitos de luz realistas",
            "Galeria de fotos em 360°",
            "Sistema de busca integrado",
            "Animações de explodir/transparência"
        ],
        sample_texts={
            "hero_title": "Viva o Imóvel",
            "hero_subtitle": "Antes de Comprar",
            "hero_description": "Explore cada cômodo em 3D. Veja a distribuição, acabamentos e potencial do imóvel.",
            "about_title": "Nossa Tecnologia",
            "about_text": "Modelos 3D realistas para você tomar a melhor decisão.",
            "services_title": "Imóveis em 3D",
            "cta_button": "Faça um Tour Virtual",
            "footer_text": "Imobiliária [NOME] - Tecnologia 3D a seu serviço"
        },
        sample_images=[
            "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800",
            "https://images.unsplash.com/photo-1600585154526-990dced4db0d?w=800",
            "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800"
        ],
        color_scheme={
            "primary": "#1E40AF",
            "secondary": "#3B82F6",
            "background": "#0F172A",
            "text": "#F8FAFC",
            "accent": "#60A5FA"
        },
        layout="real_estate_3d"
    ),

    "eventos": ReferenceSite(
        category="eventos",
        name="Eventos e Experiências",
        template_type="2d_enhanced",
        price_range=(1200, 2500),
        description="Template para empresas de eventos, casamentos e festas.",
        features=[
            "Galeria de eventos",
            "Calendário de datas",
            "Formulário de orçamento",
            "Depoimentos de clientes",
            "Localização",
            "Integração com redes sociais",
            "Vídeos de eventos passados"
        ],
        sample_texts={
            "hero_title": "Momentos Inesquecíveis",
            "hero_subtitle": "Seu Evento, Nossa Especialidade",
            "hero_description": "Criamos experiências únicas para o seu grande dia.",
            "about_title": "Sobre Nós",
            "about_text": "Equipe especializada em transformar sonhos em realidade.",
            "services_title": "Nossos Serviços",
            "cta_button": "Solicite um Orçamento",
            "footer_text": "Eventos [NOME] - Criando memórias"
        },
        sample_images=[
            "https://images.unsplash.com/photo-1511795409834-ef04bbd61622?w=800",
            "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=800",
            "https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=800"
        ],
        color_scheme={
            "primary": "#8B5CF6",
            "secondary": "#7C3AED",
            "background": "#0F0F23",
            "text": "#F5F3FF",
            "accent": "#A78BFA"
        },
        layout="events"
    ),

    "eventos_3d": ReferenceSite(
        category="eventos",
        name="Eventos 3D Premium",
        template_type="3d",
        price_range=(6000, 12000),
        description="Template 3D para empresas de eventos que querem mostrar ambientes de forma imersiva.",
        features=[
            "Tour virtual 3D do espaço",
            "Visualização 3D da decoração",
            "Navegação interativa",
            "Efeitos de luz e som",
            "Galeria de fotos 360°",
            "Animações de montagem",
            "Integração com calendário"
        ],
        sample_texts={
            "hero_title": "Viva o Evento",
            "hero_subtitle": "Antes de Reservar",
            "hero_description": "Explore nosso espaço em 3D. Veja cada detalhe da decoração e distribuição.",
            "about_title": "Nosso Espaço",
            "about_text": "Ambiente versátil que se adapta ao seu estilo.",
            "services_title": "Eventos em 3D",
            "cta_button": "Faça um Tour Virtual",
            "footer_text": "Eventos [NOME] - Tecnologia 3D para seu evento"
        },
        sample_images=[
            "https://images.unsplash.com/photo-1511795409834-ef04bbd61622?w=800",
            "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=800",
            "https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=800"
        ],
        color_scheme={
            "primary": "#8B5CF6",
            "secondary": "#EC4899",
            "background": "#0F0F23",
            "text": "#F5F3FF",
            "accent": "#F472B6"
        },
        layout="events_3d"
    ),

    "portfolio": ReferenceSite(
        category="portfolio",
        name="Portfólio Criativo",
        template_type="2d",
        price_range=(300, 800),
        description="Template para portfólios de profissionais criativos.",
        features=[
            "Galeria de projetos",
            "Apresentação pessoal",
            "Seção de habilidades",
            "Depoimentos",
            "Contato direto",
            "Blog opcional",
            "Design minimalista"
        ],
        sample_texts={
            "hero_title": "Meu Trabalho",
            "hero_subtitle": "[SEU NOME]",
            "hero_description": "Designer/Desenvolvedor com paixão por criar experiências digitais únicas.",
            "about_title": "Sobre Mim",
            "about_text": "Com [X] anos de experiência, já trabalhei com clientes de diversos segmentos.",
            "services_title": "Meus Projetos",
            "cta_button": "Ver Portfólio",
            "footer_text": "[SEU NOME] - Design & Desenvolvimento"
        },
        sample_images=[
            "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800",
            "https://images.unsplash.com/photo-1551650975-87deedd944c3?w=800",
            "https://images.unsplash.com/photo-1581291518857-4e27b48ff24e?w=800"
        ],
        color_scheme={
            "primary": "#8B5CF6",
            "secondary": "#06B6D4",
            "background": "#0F0F23",
            "text": "#F5F3FF",
            "accent": "#F472B6"
        },
        layout="portfolio"
    ),

    "servicos": ReferenceSite(
        category="servicos",
        name="Serviços Profissionais",
        template_type="2d",
        price_range=(400, 1000),
        description="Template para prestadores de serviços (advocacia, contabilidade, etc.).",
        features=[
            "Apresentação da empresa",
            "Lista de serviços",
            "Equipe",
            "Depoimentos",
            "Formulário de contato",
            "Localização",
            "Área do cliente"
        ],
        sample_texts={
            "hero_title": "Soluções para seu Negócio",
            "hero_subtitle": "[NOME DA EMPRESA]",
            "hero_description": "Oferecemos serviços de qualidade para atender suas necessidades.",
            "about_title": "Sobre Nós",
            "about_text": "Equipe especializada com anos de experiência no mercado.",
            "services_title": "Nossos Serviços",
            "cta_button": "Solicite um Orçamento",
            "footer_text": "[NOME] - Soluções profissionais"
        },
        sample_images=[
            "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=800",
            "https://images.unsplash.com/photo-1497366216548-37526070297c?w=800",
            "https://images.unsplash.com/photo-1521737604893-d14cc237f11d?w=800"
        ],
        color_scheme={
            "primary": "#1E40AF",
            "secondary": "#3B82F6",
            "background": "#F8FAFC",
            "text": "#1E293B",
            "accent": "#60A5FA"
        },
        layout="services"
    ),

    "educacao": ReferenceSite(
        category="educacao",
        name="Educação e Cursos",
        template_type="2d",
        price_range=(1000, 2500),
        description="Template para escolas, cursos e centros de educação.",
        features=[
            "Apresentação de cursos",
            "Matrícula online",
            "Calendário acadêmico",
            "Corpo docente",
            "Depoimentos de alunos",
            "Galeria de fotos",
            "Blog educacional"
        ],
        sample_texts={
            "hero_title": "Transforme seu Futuro",
            "hero_subtitle": "[NOME DA INSTITUIÇÃO]",
            "hero_description": "Cursos de qualidade para sua formação profissional.",
            "about_title": "Sobre Nós",
            "about_text": "Instituição comprometida com a excelência no ensino.",
            "services_title": "Nossos Cursos",
            "cta_button": "Matricule-se",
            "footer_text": "[NOME] - Educação de qualidade"
        },
        sample_images=[
            "https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=800",
            "https://images.unsplash.com/photo-1541339907198-e08756dedf3f?w=800",
            "https://images.unsplash.com/photo-1529390079861-591de354faf5?w=800"
        ],
        color_scheme={
            "primary": "#1E40AF",
            "secondary": "#10B981",
            "background": "#F8FAFC",
            "text": "#1E293B",
            "accent": "#3B82F6"
        },
        layout="education"
    ),

    "barbearia": ReferenceSite(
        category="barbearia",
        name="Barbearia Clássica",
        template_type="2d",
        price_range=(400, 900),
        description="Template para barbearias e salões de beleza.",
        features=[
            "Apresentação de serviços",
            "Galeria de cortes",
            "Agendamento online",
            "Equipe de profissionais",
            "Produtos vendidos",
            "Depoimentos",
            "Localização"
        ],
        sample_texts={
            "hero_title": "Estilo e Elegância",
            "hero_subtitle": "Barbearia [NOME]",
            "hero_description": "Cortes e tratamentos para você se sentir único.",
            "about_title": "Sobre Nós",
            "about_text": "Tradição e modernidade em um só lugar.",
            "services_title": "Nossos Serviços",
            "cta_button": "Agende seu Horário",
            "footer_text": "Barbearia [NOME] - Seu estilo, nossa paixão"
        },
        sample_images=[
            "https://images.unsplash.com/photo-1585747860715-2ba37e788b70?w=800",
            "https://images.unsplash.com/photo-1622969807722-428e0a331f34?w=800",
            "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=800"
        ],
        color_scheme={
            "primary": "#8B4513",
            "secondary": "#D2691E",
            "background": "#1A120B",
            "text": "#F5F5DC",
            "accent": "#FFD700"
        },
        layout="barbershop"
    ),

    "lava_jato": ReferenceSite(
        category="lava_jato",
        name="Lava-Jato Profissional",
        template_type="2d",
        price_range=(400, 1000),
        description="Template para lava-jatos e centros automotivos.",
        features=[
            "Apresentação de serviços",
            "Galeria de antes/depois",
            "Preços e pacotes",
            "Agendamento online",
            "Localização",
            "Depoimentos",
            "Promoções"
        ],
        sample_texts={
            "hero_title": "Brilho e Proteção",
            "hero_subtitle": "Lava-Jato [NOME]",
            "hero_description": "Serviços de lavagem e estética automotiva de qualidade.",
            "about_title": "Sobre Nós",
            "about_text": "Equipe treinada e produtos de primeira linha.",
            "services_title": "Nossos Serviços",
            "cta_button": "Agende Agora",
            "footer_text": "Lava-Jato [NOME] - Seu carro como novo"
        },
        sample_images=[
            "https://images.unsplash.com/photo-1607860108855-64acf2078ed9?w=800",
            "https://images.unsplash.com/photo-1605559424843-9e4c228bf1c2?w=800",
            "https://images.unsplash.com/photo-1599490659213-e2b9527bd087?w=800"
        ],
        color_scheme={
            "primary": "#0EA5E9",
            "secondary": "#0284C7",
            "background": "#0F172A",
            "text": "#F8FAFC",
            "accent": "#38BDF8"
        },
        layout="car_wash"
    ),

    "personalizado": ReferenceSite(
        category="personalizado",
        name="Projeto Personalizado",
        template_type="3d",
        price_range=(8000, 15000),
        description="Template para projetos personalizados com requisitos específicos.",
        features=[
            "Design sob medida",
            "Desenvolvimento customizado",
            "Integrações específicas",
            "Animações personalizadas",
            "Modelos 3D exclusivos",
            "Sistema de gerenciamento",
            "Suporte dedicado"
        ],
        sample_texts={
            "hero_title": "Seu Projeto, Nossa Expertise",
            "hero_subtitle": "[NOME DO CLIENTE]",
            "hero_description": "Criamos soluções digitais únicas para atender suas necessidades específicas.",
            "about_title": "Sobre o Projeto",
            "about_text": "Cada detalhe é pensado e desenvolvido especialmente para você.",
            "services_title": "Nossas Soluções",
            "cta_button": "Fale Conosco",
            "footer_text": "[NOME] - Tecnologia personalizada"
        },
        sample_images=[
            "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800",
            "https://images.unsplash.com/photo-1551650975612-9a054b0db644?w=800",
            "https://images.unsplash.com/photo-1581291518857-4e27b48ff24e?w=800"
        ],
        color_scheme={
            "primary": "#8B5CF6",
            "secondary": "#06B6D4",
            "background": "#0F0F23",
            "text": "#F5F3FF",
            "accent": "#F472B6"
        },
        layout="custom"
    )
}

# =============================================================================
# 🔍 FUNÇÃO PARA BUSCAR REFERÊNCIA POR CATEGORIA
# =============================================================================

def get_reference(category: str) -> ReferenceSite:
    """
    Retorna a referência de site para uma categoria específica.
    Se a categoria não existir, retorna a referência 'personalizado'.
    """
    return REFERENCE_SITES.get(category, REFERENCE_SITES["personalizado"])

# =============================================================================
# 📊 FUNÇÃO PARA LISTAR TODAS AS CATEGORIAS
# =============================================================================

def list_categories() -> List[str]:
    """Retorna uma lista de todas as categorias disponíveis."""
    return list(REFERENCE_SITES.keys())

# =============================================================================
# 🎨 FUNÇÃO PARA BUSCAR REFERÊNCIA POR TIPO DE TEMPLATE
# =============================================================================

def get_references_by_type(template_type: str) -> List[ReferenceSite]:
    """
    Retorna todas as referências de um tipo específico de template.
    Tipos: '2d', '2d_enhanced', '3d'
    """
    return [ref for ref in REFERENCE_SITES.values() if ref.template_type == template_type]