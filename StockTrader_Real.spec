# -*- mode: python ; coding: utf-8 -*-
import os

def collect_ai_engine():
    """ai_engine 폴더에서 __pycache__ 제외하고 수집"""
    result = []
    for root, dirs, files in os.walk('ai_engine'):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in files:
            if f.endswith('.pyc'):
                continue
            src = os.path.join(root, f)
            result.append((src, root))
    return result

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=collect_ai_engine() + [('ls_api.py', '.')],
    hiddenimports=['ls_api'],
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
