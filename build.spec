# PyInstaller spec — build with: pyinstaller build.spec
# Produces dist/ClaudeMeter.exe (single file, no console window).

from pathlib import Path

block_cipher = None

_assets: list = []
# Bundle EVERY asset file (svg/png/ico) — so users can drop in their own
# logo with any filename and the rebuild picks it up automatically.
_assets_dir = Path("assets")
if _assets_dir.is_dir():
    for f in _assets_dir.iterdir():
        if f.is_file() and f.suffix.lower() in (".svg", ".png", ".ico", ".jpg", ".jpeg"):
            _assets.append((str(f).replace("\\", "/"), "assets"))

a = Analysis(
    ["src/claude_usage_widget/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=_assets,
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtSvg",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "test",
        "unittest",
        "pytest",
        "PySide6.QtWebEngineCore",
        "PySide6.QtMultimedia",
        "PySide6.Qt3DCore",
        "PySide6.QtQuick",
        "PySide6.QtQml",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtOpenGL",
        "PySide6.QtPdf",
        "PySide6.QtPositioning",
        "PySide6.QtSql",
        "PySide6.QtTest",
        "PySide6.QtWebChannel",
        "PySide6.QtWebSockets",
    ],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ClaudeMeter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # no console window — pure GUI
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
