"""Teste isolado de síntese, sem iniciar interface ou registrar credenciais."""
import asyncio
import sys
from dotenv import load_dotenv
from cronos.config import Settings
from cronos.fish_legacy import synthesize_json


def main():
    load_dotenv('.env')
    settings=Settings.from_env()
    try:
        if sys.platform!='win32':
            raise RuntimeError('Reprodução física deste teste requer Windows.')
        if settings.privacy_mode!='online':
            raise RuntimeError('Modo local ativo: nenhuma chamada externa foi realizada.')
        if not settings.fish_key:
            raise RuntimeError('Não há chave Fish configurada neste projeto. Nenhuma chamada foi realizada.')
        if not settings.fish_reference:
            raise RuntimeError('Não há ID de voz configurado neste projeto. Nenhuma chamada foi realizada.')
        audio=asyncio.run(synthesize_json(settings.fish_key,text='Olá. Teste de voz do Kronos.',
                                         reference_id=settings.fish_reference,format='wav'))
        import winsound
        winsound.PlaySound(audio,winsound.SND_MEMORY)
        message='O pedido JSON legado retornou áudio e o Windows concluiu a reprodução. Se não ouviu, confira volume e dispositivo de saída. A captura do microfone não foi testada.'
    except Exception as exc:
        status=getattr(exc,'status',None)
        if status:
            message=f'Pedido JSON legado, modelo s2.1-pro-free: HTTP {status}.\n\nMotivo informado pelo provedor: '+getattr(exc,'safe_detail','Motivo não disponível.')+'\n\nO holograma não foi aberto. '+('HTTP 400 indica rejeição do pedido, não confirma falta de créditos.' if status==400 else 'O status informado não permite concluir sozinho a causa ou o saldo da conta.')
        elif isinstance(exc,RuntimeError):
            message=str(exc)
        else:
            message='Não foi possível concluir o teste de rede/áudio. Confira conexão e saída de som. Nenhuma credencial foi registrada.'
    if sys.platform=='win32':
        import ctypes
        ctypes.windll.user32.MessageBoxW(None,message,'Kronos — voz isolada',0)
    else:
        print(message)


if __name__=='__main__':
    main()
