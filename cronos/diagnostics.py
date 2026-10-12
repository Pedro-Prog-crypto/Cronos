"""Teste mínimo do provedor sem gravar conversa ou revelar credenciais."""
import asyncio

from dotenv import load_dotenv

from cronos.config import Settings
from cronos.providers import ProviderError, make_provider


def main():
    load_dotenv(".env")
    settings = Settings.from_env()
    print("Diagnóstico de conexão do Cronos")
    print("Provedor:", settings.provider)
    if settings.provider == "gemini":
        print("Modelo:", settings.gemini_model)
        print("Chave Gemini:", "configurada" if settings.gemini_key.strip() else "ausente")
    print("Executando uma chamada mínima à IA; pode consumir cota/créditos.")
    try:
        asyncio.run(make_provider(settings).reply("Você é um assistente. Responda brevemente.",
                                                 [{"role": "user", "content": "Diga olá. Não há temas para memorizar."}]))
    except ProviderError as exc:
        print("FALHA:", str(exc))
        raise SystemExit(1)
    print("OK: o provedor respondeu no formato esperado. Nenhuma conversa foi salva.")


if __name__ == "__main__":
    main()
