# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# numpy / pandas 전체 수집 (바이너리 .dll/.pyd 포함)
np_d,  np_b,  np_h  = collect_all('numpy')
pd_d,  pd_b,  pd_h  = collect_all('pandas')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[] + np_b + pd_b,
    datas=[
        ('ai_engine',         'ai_engine'),
        ('engine_config.json', '.'),
    ] + np_d + pd_d,
    hiddenimports=[
        'requests', 'urllib3', 'charset_normalizer', 'certifi', 'idna',
        'PyQt5', 'PyQt5.QtWidgets', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.sip',
        'sqlite3',
        'ai_engine', 'ai_engine.db', 'ai_engine.comm', 'ai_engine.core',
        'ai_engine.conditions', 'ai_engine.data', 'ai_engine.learning',
    ] + np_h + pd_h,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='StockTrader_Real',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='StockTrader_Real',
)
