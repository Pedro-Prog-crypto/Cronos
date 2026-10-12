"""Teste mínimo do provedor sem gravar conversa ou revelar credenciais."""
import asyncio

from dotenv import load_dotenv

from cronos.config import Settings
from cronos.providers import ProviderError, make_provider
from cronos.integrations import available_models


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
        if settings.provider == 'gemini' and '404' in str(exc):
            print("Consultando os modelos anunciados para esta chave, sem gerar texto...")
            try:
                models=asyncio.run(available_models(settings,'gemini'))
                for model in models:print("Modelo disponível:",model)
                print("Escolha um modelo da lista em GEMINI_MODEL no .env e reinicie. A lista não comprova cota gratuita.")
            except ProviderError as lookup_error:
                print("Consulta de modelos falhou:",str(lookup_error))
        raise SystemExit(1)
    print("OK: o provedor respondeu no formato esperado. Nenhuma conversa foi salva.")


if __name__ == "__main__":
    main()
