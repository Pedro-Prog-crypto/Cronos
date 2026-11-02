"""Extract explicit personal deadlines without relying on model guesses."""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta, timezone

SAO_PAULO = timezone(timedelta(hours=-3), 'America/Sao_Paulo')
KINDS = {'prova': 'prova', 'avaliacao': 'prova', 'exame': 'prova', 'vestibular': 'prova',
         'entrevista': 'entrevista', 'entrega': 'entrega', 'trabalho': 'trabalho',
         'reuniao': 'reunião', 'consulta': 'consulta', 'compromisso': 'compromisso'}
MONTHS = {'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'abril': 4, 'maio': 5, 'junho': 6,
          'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12}


def plain(value: str) -> str:
    normalized = unicodedata.normalize('NFD', value.casefold())
    return ''.join(char for char in normalized if not unicodedata.combining(char))


def _date(text: str, today: date) -> date | None:
    match = re.search(r'\b(?:daqui a|em)\s+(\d{1,3}|um|uma|dois|duas|tres)\s+(dias?|semanas?|meses?)\b', text)
    if match:
        numbers = {'um': 1, 'uma': 1, 'dois': 2, 'duas': 2, 'tres': 3}
        count = numbers.get(match[1], int(match[1]) if match[1].isdigit() else 0)
        unit = match[2]
        days = count * (30 if unit.startswith('mes') else 7 if unit.startswith('semana') else 1)
        return today + timedelta(days=days) if 0 < days <= 3660 else None
    if re.search(r'\bdepois de amanha\b', text):
        return today + timedelta(days=2)
    if re.search(r'\bamanha\b', text):
        return today + timedelta(days=1)
    match = re.search(r'\b(?:dia\s+)?(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b', text)
    if match:
        year = int(match[3]) if match[3] else today.year
        if year < 100:
            year += 2000
        try:
            result = date(year, int(match[2]), int(match[1]))
            if not match[3] and result < today:
                result = result.replace(year=year + 1)
            return result
        except ValueError:
            return None
    match = re.search(r'\b(?:dia\s+)?(\d{1,2})\s+de\s+([a-z]+)(?:\s+de\s+(\d{4}))?\b', text)
    if match and match[2] in MONTHS:
        year = int(match[3]) if match[3] else today.year
        try:
            result = date(year, MONTHS[match[2]], int(match[1]))
            if not match[3] and result < today:
                result = result.replace(year=year + 1)
            return result
        except ValueError:
            return None
    return None


def explicit_event(message: str, now: datetime | None = None) -> dict | None:
    """Only store a dated commitment stated by the user, never a question/example."""
    text = plain(message)
    if not text or '?' in message or re.search(r'\b(?:exemplo|hipotetic\w*|imagin\w*|suponha|se eu tivesse|se eu tiver|qual|quando)\b', text):
        return None
    if not re.search(r'\b(?:tenho|terei|vou ter|minha|meu|preciso entregar|preciso fazer|acontecera|sera|esta marcada|esta marcado)\b', text):
        return None
    kind = next((label for word, label in KINDS.items() if re.search(r'\b' + word + r'\b', text)), None)
    if not kind:
        return None
    today = (now or datetime.now(SAO_PAULO)).astimezone(SAO_PAULO).date()
    due = _date(text, today)
    if due is None or due < today:
        return None
    subject = re.search(r'\b(?:prova|avaliacao|exame|entrevista|entrega|trabalho|reuniao|consulta|compromisso)\s+(?:importante\s+)?de\s+([\w ]{2,45})', text)
    subject = re.split(r'\b(?:dia|daqui|amanha|em|e|sera|acontecera)\b', subject[1])[0].strip() if subject else ''
    title = kind + (f' de {subject}' if subject else '')
    return {'title': title[:100], 'kind': kind, 'due_date': due.isoformat(), 'source': message[:500]}


def resolution(message: str) -> tuple[str, str] | None:
    text = plain(message)
    if '?' in message:
        return None
    match = re.search(r'\b(?:cancelei|cancelaram|foi cancelad[ao]|ja fiz|ja terminei|conclui|terminei)\b.{0,80}\b(prova|avaliacao|exame|entrevista|entrega|trabalho|reuniao|consulta|compromisso)\b', text)
    if not match:
        return None
    kind = KINDS[match[1]]
    return kind, 'cancelled' if re.search(r'cancel', match[0]) else 'completed'
