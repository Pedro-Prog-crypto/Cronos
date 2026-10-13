"""Teste mínimo do provedor sem gravar conversa ou revelar credenciais."""
import asyncio
import argparse
import hashlib

from dotenv import load_dotenv

from cronos.config import Settings
from cronos.providers import ProviderError, make_provider
from cronos.integrations import available_models
from cronos import usage


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--generate',action='store_true',help='Enviar uma geração real; consome cota.')
    args=parser.parse_args(argv)
    load_dotenv(".env", override=True)
    settings = Settings.from_env()
    import json
    saved=usage.ROOT/'last-gemini-error.json'
    if saved.exists():
        try:print('Último erro registrado:',json.loads(saved.read_text(encoding='utf-8'))['message'])
        except (OSError,ValueError,KeyError):pass
    print("Diagnóstico de conexão do Cronos")
    print("Provedor:", settings.provider)
    if settings.provider == "gemini":
        print("Modelo:", settings.gemini_model)
        print("Chave Gemini:", "configurada" if settings.gemini_key.strip() else "ausente")
        identity=hashlib.sha256((settings.gemini_key.strip()+'|'+settings.gemini_model).encode()).hexdigest()
        remaining=usage.remaining(identity)
        if remaining>0:print('Pausa ativa preservada entre reinícios:',int(remaining)+1,'segundos. Não confirma horário de renovação da cota.')
    counts={};total=0
    for filename in ('gemini-requests.previous.jsonl','gemini-requests.jsonl'):
        path=usage.ROOT/filename
        if not path.exists():continue
        try:
            for line in path.read_text(encoding='utf-8').splitlines():
                try:row=json.loads(line)
                except ValueError:continue
                if row.get('model')!=settings.gemini_model:continue
                total+=1;source=row.get('source','operation');counts[source]=counts.get(source,0)+1
        except OSError:pass
    print('Tentativas Gemini registradas localmente para este modelo:',total)
    for source,count in sorted(counts.items()):print('Origem:',source,'— chamadas:',count)
    if not args.generate:
        print('Consulta local concluída. Nenhuma chamada à IA foi enviada. Isso não confirma acesso ou cota disponível.')
        print('Para testar uma geração explicitamente: python -m cronos.diagnostics --generate')
        return
    print("Executando uma chamada mínima à IA; pode consumir cota/créditos.")
    try:
        with usage.request_scope('diagnostic'):
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
    print("OK: a chamada mínima respondeu. Isso não confirma cota para uma conversa completa, que envia mais contexto e pode usar ferramentas. Nenhuma conversa foi salva.")


if __name__ == "__main__":
    main()
