"""Lightweight task planning for one assistant identity, not forty fake model calls."""
from __future__ import annotations

import re
from dataclasses import dataclass

from cronos.study_intent import is_study_request, normalize, requests_exhaustive_lookup


@dataclass(frozen=True)
class CognitivePlan:
    roles: tuple[str, ...]
    guidance: str


def plan_for(message: str, tools: set[str] | None = None) -> CognitivePlan:
    """Select only relevant reasoning disciplines; tools remain separately gated."""
    text = normalize(message)
    tools = tools or set()
    roles = ['contexto', 'raciocínio']
    instructions = []
    if is_study_request(message):
        roles.append('educador')
        instructions.append('Ensine com contexto, mecanismo, exemplo e limite; não encerre após uma definição rasa.')
    if re.search(r'\b(?:decid|escolh|vale a pena|melhor op[cç][aã]o|concorda|o que acha|sua opini[aã]o)\w*\b', text):
        roles.extend(('decisão', 'crítica'))
        instructions.append('Compare alternativas e evidências; dê sua conclusão fundamentada mesmo quando discordar do senhor. Separe fato, inferência e opinião.')
    if re.search(r'\b(?:plano|planej|meta|projeto|organizar|objetivo|passo a passo)\w*\b', text):
        roles.append('planejamento')
        instructions.append('Transforme o objetivo em próximos passos concretos e verificáveis, adaptando quando houver mudança.')
    if re.search(r'\b(?:erro|bug|c[oó]digo|programa[cç][aã]o|python|api|integra[cç][aã]o)\b', text):
        roles.extend(('engenharia', 'depuração'))
        instructions.append('Diagnostique a causa com evidência antes de propor correção; distinga hipótese de teste executado.')
    if re.search(r'\b(?:prova|avalia[cç][aã]o|exame|entrevista|prazo|amanh[aã]|semana|data)\b', text):
        roles.append('tempo')
        instructions.append('Use a data atual e os compromissos registrados; peça esclarecimento quando a data for ambígua.')
    if re.search(r'\b(?:foto|imagem|visual|painel|v[ií]deo|gr[aá]fico)\b', text):
        roles.append('composição visual')
        instructions.append('Relacione cada imagem a um fato da explicação; não afirme ter exibido mídia se a busca falhar.')
    if requests_exhaustive_lookup(message):
        roles.append('pesquisa')
        instructions.append('Para fatos atuais ou listas completas, consulte fontes atuais se a ferramenta estiver disponível; cite fonte e data.')
        if 'web_search' not in tools and 'web_news' not in tools:
            instructions.append('A pesquisa pode estar indisponível: não invente resultados.')
    if re.search(r'\b(?:verdade|confirme|verifique|fontes?|boato|falso)\b', text):
        roles.append('verificação')
        instructions.append('Compare alegações com fontes; identifique contradições e incertezas, sem transformar lembranças em prova.')
    if re.search(r'\b(?:minha vida|meu futuro|me aconselh|estou preocupado|estou triste|fam[ií]lia|meu irm[aã]o)\b', text):
        roles.append('aconselhamento')
        instructions.append('Considere os objetivos e a autonomia do senhor; ofereça conselho concreto, sem fingir sentimentos humanos.')
    return CognitivePlan(tuple(dict.fromkeys(roles)), ' '.join(instructions))


def explicit_goal(message: str) -> str | None:
    """Capture an actual user-stated long-term goal, never a hypothetical one."""
    if '?' in message or re.search(r'\b(?:imagine|exemplo|hipotetic|suponha)\b', normalize(message)):
        return None
    match = re.search(r'\b(?:quero aprender|minha meta\s+(?:é|e)|meu objetivo\s+(?:é|e)|pretendo estudar|quero me preparar para)\s+(.{4,120})', message, re.I)
    if not match:
        return None
    title = re.split(r'[.!?\n]', match[1])[0].strip(' ,;:')
    return title[:120] if len(title) >= 4 else None
