"""Uma imagem explicitamente compartilhada; sem captura contínua ou execução."""
import base64
import io
import warnings

from PIL import Image, UnidentifiedImageError
from cronos.upload_limits import MAX_UPLOAD_BYTES,MAX_IMAGE_PIXELS


def normalize_image(raw):
    if not raw or len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("Envie PNG/JPEG de até 30 MiB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in {"PNG", "JPEG"} or image.width * image.height > MAX_IMAGE_PIXELS:
                    raise ValueError("Use PNG/JPEG com até 40 milhões de pixels.")
                if image.format=="JPEG":image.draft("RGB",(1600,1600))
                image.load()
                image.thumbnail((1600, 1600))
                # Remove EXIF/metadados; nenhuma imagem é gravada no disco.
                clean = Image.new("RGB", image.size, "white")
                if image.mode == "RGBA":
                    clean.paste(image, mask=image.getchannel("A"))
                else:
                    clean.paste(image.convert("RGB"))
                output = io.BytesIO()
                clean.save(output, format="JPEG", quality=85)
                return {"mime_type": "image/jpeg", "data": base64.b64encode(output.getvalue()).decode()}
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError("Imagem inválida ou grande demais para análise segura.") from exc


def capture_screen():
    import sys
    if sys.platform != "win32":
        raise ValueError("Captura da tela disponível somente no Windows local.")
    from PIL import ImageGrab
    with ImageGrab.grab() as image:
        image.thumbnail((1600, 1600))
        output = io.BytesIO()
        image.convert("RGB").save(output, format="PNG")
        return output.getvalue()
