# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    hiddenimports=[
        'requests', 'urllib3', 'charset_normalizer', 'certifi', 'idna',
        'PyQt5', 'PyQt5.QtWidgets', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.sip',
        'numpy', 'numpy.core', 'numpy.core._multiarray_umath',
        'pandas', 'pandas.core', 'pandas.io',
        'sqlite3',
        'ai_engine', 'ai_engine.db', 'ai_engine.comm', 'ai_engine.core',
        'ai_engine.conditions', 'ai_engine.data', 'ai_engine.learning',
    ],
    datas=[
        ('ai_engine', 'ai_engine'),
        ('engine_config.json', '.'),
    ],
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
