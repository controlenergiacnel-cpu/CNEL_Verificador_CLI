# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = []
hiddenimports += collect_submodules('pyhanko')
hiddenimports += collect_submodules('pyhanko_certvalidator')
hiddenimports += collect_submodules('fitz')
hiddenimports += collect_submodules('PIL')
hiddenimports += collect_submodules('pytesseract')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('.\\tools', 'tools')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'tensorflow', 'scipy', 'pandas', 'matplotlib'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CNEL_Verificador_CLI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
