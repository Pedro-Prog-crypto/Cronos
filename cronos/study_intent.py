"""Small, deterministic intent checks for educational presentation and web lookup."""
from __future__ import annotations

import re
import unicodedata


def normalize(text: str) -> str:
    value = unicodedata.normalize("NFD", str(text).casefold())
    return "".join(char for char in value if not unicodedata.combining(char))


def asks_visual_capability(text: str) -> bool:
    """An operational question about Cronos's own mural has a local answer."""
    value = normalize(text)
    return bool(re.search(
        r"\b(?:voce|cronos|kronos|chronos)\b.{0,70}"
        r"\b(?:consegue|pode|sabe|tem capacidade de)\b.{0,100}"
        r"\b(?:mostrar|exibir|buscar|pesquisar|procurar)\b.{0,45}"
        r"\b(?:imagens?|fotos?|fotografias)\b", value,
    ))


def is_study_request(text: str) -> bool:
    value = normalize(text)
    explicit = re.search(
        r"\b(?:explique|explica|me ensine|ensine|me ajuda a entender|ajude a entender|"
        r"quero entender|nao entendi|nao compreendi|me de uma dica|estude|resuma|resumo|compare|qual a diferenca|todas? as? obras|lista completa|"
        r"o que (?:e|foi|significa|causou|aconteceu)|como funciona|como (?:foi|aconteceu|surgiu)|"
        r"por que|por qual motivo|quem (?:foi|e|era|vai ganhar|voce acha|voce considera)|o que acha de|qual a sua opiniao|qual sua opiniao|me conte sobre|me conta sobre|"
        r"me fale|fale sobre|me explica|me explique|analise|analisa|quais foram as causas|pessoas? mais importantes?)\b",
        value,
    )
    school_topic = re.search(
        r"\b(?:historia|filosofia|biologia|matematica|fisica|quimica|geografia|"
        r"portugues|literatura|sociologia|prova|vestibular|enem|pais|guerra mundial|"
        r"revolucao|filosofo|equacao|teorema|celula|mitocondria|fotossintese|"
        r"primeira guerra|segunda guerra|causas da|consequencias da)\b",
        value,
    )
    contextual = re.search(
        r"\b(?:como|por que|porque)\b.{0,80}\b(?:ele|ela|isso|aconteceu|funciona|mudou|comecou|terminou|influenciou|causou)\b",
        value,
    )
    return bool(explicit or contextual or (school_topic and "?" in value))


def is_visual_request(text: str) -> bool:
    """A visual explanation belongs to Cronos's mural, not an external browser."""
    value = normalize(text)
    if re.search(r"\b(?:sem imagens|sem fotos|so texto|somente texto|por escrito|de forma escrita|apenas texto|nao (?:mostre|mostrar|exiba|exibir|quero imagens|quero fotos))\b", value):
        return False
    return bool(
        re.search(r"\b(?:mostre|mostra|mostrar|exiba|exibe|quero ver|coloque|poe|busque|procure)\b.{0,100}\b(?:imagens?|fotos?|fotografias|mural visual)\b", value)
        or re.search(r"\b(?:explique|explica|apresente|apresenta|mostre|mostra)\b.{0,100}\b(?:com imagens|com fotos|visualmente|de forma visual|apresentacao visual|apresentacao imersiva)\b", value)
        or re.search(r"\b(?:apresentacao visual|apresentacao imersiva|mural de imagens)\s+(?:sobre|de|do|da)\b", value)
    )


def requests_exhaustive_lookup(text: str) -> bool:
    value = normalize(text)
    if re.search(r"\b(?:nao|sem)\s+(?:pesquis|busc|procur)", value):
        return False
    explicit_search = re.search(r"\b(?:pesquis|busc|procur|consulte fontes|verifique na web)\w*\b", value)
    exhaustive = re.search(
        r"\b(?:todas? as? obras|lista completa|todos os|todas as|"
        r"relacao completa|catalogo completo|fontes e referencias|"
        r"cite as fontes|com fontes|dados atuais|resultado atual|hoje|agora|"
        r"noticias|previsao do tempo|cotacao|lei vigente)\b",
        value,
    )
    return bool(explicit_search or exhaustive)
