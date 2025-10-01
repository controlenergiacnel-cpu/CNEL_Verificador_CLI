# cnel_verificador.spec
# Genera un one-folder con main.py como entrypoint y assets de tools/
block_cipher = None

from PyInstaller.utils.hooks import copy_metadata
datas = []
# incluir carpeta tools completa
datas += [("tools", "tools")]

# (si usas Tesseract portable, puedes añadir tessdata aquí)
# datas += [("third_party/tesseract/tessdata", "tessdata")]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # libs que a veces hay que forzar según tu ambiente
        'pyhanko', 'pyhanko.sign.validation', 'pyhanko_certvalidator',
        'fitz', 'PIL', 'pytesseract', 'asn1crypto', 'PyPDF2'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='CNEL_Verificador_CLI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,   # CLI visible (para GUI cambia a False)
    disable_windowed_traceback=False,
)
