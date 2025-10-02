# hook-cryptography.py — evita collect_submodules (rompe en Py 3.13)
from PyInstaller.utils.hooks import collect_data_files

# Incluye lo mínimo necesario sin explorar submódulos en aislado
hiddenimports = [
    "cryptography.hazmat.backends",
    "cryptography.hazmat.backends.openssl",
    "cryptography.hazmat.bindings._rust",
]

datas = collect_data_files("cryptography")
