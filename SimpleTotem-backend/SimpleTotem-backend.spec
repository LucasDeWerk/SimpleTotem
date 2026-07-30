# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — SimpleTotem-backend
# Gera um único binário: SimpleTotem-backend
# Executar de dentro de SimpleTotem-backend/:
#   pyinstaller SimpleTotem-backend.spec

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hiddenimports = [], [], []

# Pacotes com sub-módulos dinâmicos (uvicorn, fastapi, starlette carregam
# handlers por string; pydantic e pydantic_core têm extensões C)
for pkg in ('uvicorn', 'fastapi', 'starlette', 'pydantic', 'pydantic_core'):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# SQLAlchemy carrega dialetos por string → garante todos os submodulos
hiddenimports += collect_submodules('sqlalchemy')

# Imports adicionais que o PyInstaller não detecta estaticamente
hiddenimports += [
    # uvicorn internals
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.loops.asyncio',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    # async
    'anyio._backends._asyncio',
    # banco
    'sqlalchemy.dialects.sqlite',
    'sqlalchemy.dialects.sqlite.pysqlite',
    # auth
    'jose',
    'jose.jwt',
    'passlib.handlers.bcrypt',
    # form data (FastAPI multipart)
    'multipart',
    'python_multipart',
    # stdlib usado dinamicamente
    'email.mime.multipart',
    'email.mime.text',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', '_tkinter', 'test', 'unittest', 'xmlrpc'],
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
    name='SimpleTotem-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX pode quebrar extensões .so no Linux
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
