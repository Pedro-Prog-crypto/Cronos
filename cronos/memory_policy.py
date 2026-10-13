"""Knowledge notes exclude social and interface-only turns, not subject areas."""
import re
import unicodedata

def normalized(text):
    text=''.join(c for c in unicodedata.normalize('NFD',text.casefold()) if not unicodedata.combining(c))
    text=re.sub(r'[^\w\s]',' ',text)
    text=re.sub(r'\s+',' ',text).strip()
    return re.sub(r'^(?:cronos|kronos|jarvis)(?:\s+|$)','',text).strip()

def social_or_control(text):
    text=normalized(text)
    if not text:return True
    phrase=r'(?:oi|ola|ei|bom dia|boa tarde|boa noite|obrigad[oa]|valeu|ok|beleza|tchau|ate mais|tudo bem|sim|nao|na escuta|esta na escuta|voce esta na escuta|esta ai|ta ai|voce esta ai|voce ta ai|esta me ouvindo|ta me ouvindo|voce esta me ouvindo|voce ta me ouvindo|consegue me ouvir|me ouve|teste|testando|teste de (?:voz|audio|microfone))'
    if re.fullmatch(phrase+r'(?: '+phrase+r')*',text):return True
    return bool(re.fullmatch(r'(?:abrir|abra|abre|fechar|feche|fecha|mostrar|mostre|ativar|ative|desativar|desative|ligar|desligar) (?:o |a )?(?:painel|conversa|microfone|olho de deus|memoria|obsidian)',text))

GENERIC_TITLES={'saudacao','saudacoes','cumprimento','cumprimentos','conversa casual','chamada do assistente','disponibilidade do assistente','confirmacao de escuta','teste de audio','teste de voz','teste de microfone','status do assistente'}

def knowledge_topics(message,topics):
    # Short confirmations may continue a substantive discussion in its context.
    if social_or_control(message) and normalized(message) not in {'sim','nao','ok','beleza'}:return []
    return [topic for topic in topics if normalized(topic['title']) not in GENERIC_TITLES and (not normalized(topic['title']) or not social_or_control(topic['title']))]

def graph_note(path,title):
    if path.startswith('Conversas/') or path=='Mapa de Conhecimento.md':return False
    if path.startswith(('Memorias/','Temas/')) and (normalized(title) in GENERIC_TITLES or (social_or_control(title) and (normalized(title) or path.startswith('Memorias/')))):return False
    return True
