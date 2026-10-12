"""Agente local inicial: comandos explícitos, sem shell e sem execução de downloads."""
import argparse
import os
import shutil
import sys
import webbrowser
import zipfile
from pathlib import Path
from urllib.parse import quote_plus


MAX_EXTRACTED_BYTES = 500 * 1024 * 1024


def safe_extract(archive: Path, destination: Path):
    if destination.exists():
        raise ValueError("O destino já existe; escolha uma pasta nova.")
    with zipfile.ZipFile(archive) as zipped:
        entries = zipped.infolist()
        if len(entries) > 10000 or sum(e.file_size for e in entries) > MAX_EXTRACTED_BYTES:
            raise ValueError("ZIP excede o limite de extração.")
        for entry in entries:
            # Rejeita paths absolutos, traversal, streams NTFS e links Unix.
            name = entry.filename.replace("\\", "/")
            if ":" in name or name.startswith("/") or ".." in name.split("/"):
                raise ValueError("ZIP contém caminho inseguro.")
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("ZIP contém link simbólico.")
            target = (destination / name).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError("ZIP contém caminho fora do destino.")
        destination.mkdir(parents=True)
        try:
            zipped.extractall(destination)
        except Exception:
            shutil.rmtree(destination)
            raise


def main():
    parser = argparse.ArgumentParser(description="Agente local do Cronos para Windows")
    parser.add_argument("action", choices=["downloads", "search", "extract"])
    parser.add_argument("value", nargs="?")
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Execute o agente no seu computador Windows.")
    if args.action == "downloads":
        folder = Path.home() / "Downloads"
        if not folder.is_dir():
            parser.error("Downloads não encontrado no caminho padrão do usuário.")
        os.startfile(str(folder))
    elif args.action == "search":
        if not args.value:
            parser.error("Informe o texto da pesquisa.")
        webbrowser.open("https://www.google.com/search?q=" + quote_plus(args.value))
    else:
        if not args.value or not args.destination:
            parser.error("Informe o arquivo ZIP e --destination.")
        archive = Path(args.value).resolve()
        destination = args.destination.resolve()
        print(f"Extrair {archive} para {destination}?")
        if input('Digite CONFIRMAR: ').strip() != "CONFIRMAR":
            print("Operação cancelada.")
            return
        try:
            safe_extract(archive, destination)
        except (ValueError, OSError, zipfile.BadZipFile) as exc:
            parser.error(str(exc))
        print("Extração concluída. Arquivos não foram executados.")


if __name__ == "__main__":
    main()
