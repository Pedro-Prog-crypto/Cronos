"""Exemplo de plugin novo, independente dos módulos do pacote antigo."""
from datetime import datetime
from cronos.tools import Arguments, Tool


def build_tools(settings, memory):
    return [Tool("local_clock", "Consulta a data/hora local do computador.", Arguments,
                 lambda args: {"datetime": datetime.now().astimezone().isoformat()})]
