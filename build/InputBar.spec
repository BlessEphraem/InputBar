# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['../src/InputBar.pyw'],
    pathex=[],
    binaries=[],
    datas=[
        ('../src/Assets/Icons/Logo.ico',  'Assets/Icons'),
        ('../src/Assets/Icons/*.svg',     'Assets/Icons'),
        ('../src/Assets/Themes/',         'Assets/Themes'),
        # .py files must be on disk (not in PYZ) so importlib.util.spec_from_file_location
        # can load Core modules and Plugins at runtime.
        ('../src/Core/*.py',              'Core'),
        ('../src/_version.py',            '.'),
        ('../src/Plugins/',               'Plugins'),
    ],
    hiddenimports=[
        'pystray._win32',
        'PIL._tkinter_finder',
        # App.py (loaded as datas) — PyInstaller won't auto-detect these imports
        'rapidfuzz',
        'rapidfuzz.fuzz',
        'rapidfuzz.process',
        'rapidfuzz.distance',
        'rapidfuzz.utils',
        'win32com',
        'win32com.client',
        'pywintypes',
        'win32file',
        'win32pipe',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'pydoc', 'PyQt5', 'PySide2', 'PySide6'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='InputBar',
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
    icon=['../src/Assets/Icons/Logo.ico'],
    uac_admin=False,
    contents_directory='Lib',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='InputBar',
)
