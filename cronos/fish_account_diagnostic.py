"""Consulta somente metadados de acesso; não gera voz nem revela IDs/chave."""
import asyncio
from dotenv import load_dotenv
from cronos.config import Settings
from fishaudio import AsyncFishAudio


async def report(settings, factory=AsyncFishAudio):
    lines=[]
    if settings.privacy_mode!='online':return ['Modo local: nenhuma consulta externa foi realizada.']
    if not settings.fish_key:return ['Chave Fish ausente. Nenhuma consulta foi realizada.']
    async with factory(api_key=settings.fish_key,timeout=20) as fish:
        try:
            credits=await fish.account.get_credits(check_free_credit=True)
            lines.append('Saldo retornado pela API: '+str(credits.credit))
            lines.append('Indicador de crédito gratuito: '+str(credits.has_free_credit))
        except Exception as exc:lines.append('Consulta de saldo API falhou: HTTP '+str(getattr(exc,'status','não disponível')))
        try:
            package=await fish.account.get_package()
            lines.append('Saldo do pacote: '+str(package.balance)+'/'+str(package.total))
        except Exception as exc:lines.append('Consulta do pacote falhou: HTTP '+str(getattr(exc,'status','não disponível')))
        if settings.fish_reference:
            try:
                await fish.voices.get(settings.fish_reference)
                lines.append('A chave consegue consultar a voz configurada.')
            except Exception as exc:lines.append('Consulta da voz falhou: HTTP '+str(getattr(exc,'status','não disponível')))
        else:lines.append('ID de voz ausente na configuração.')
    lines.append('Consulta de voz não comprova síntese. Nenhum áudio foi gerado e nenhum modelo foi trocado.')
    return lines


def main():
    load_dotenv('.env')
    try:
        for line in asyncio.run(report(Settings.from_env())):print(line)
    except Exception:
        print('Não foi possível concluir a consulta. Confira conexão e configuração. Credenciais não foram exibidas.')


if __name__=='__main__':main()
