# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for backend.exe

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

# 获取项目根目录
backend_dir = Path(SPECPATH).parent
project_root = backend_dir.parent

# 添加路径
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(project_root))

# 定义 block_cipher（用于加密 Python 字节码，可选）
block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[str(backend_dir), str(project_root)],
    binaries=[],
    datas=[
        # 包含 .env.example（如果存在）
        # (str(backend_dir / 'env.example'), '.'),
    ],
    hiddenimports=[
        'backend.vision',
        'backend.speech',
        'backend.auth_supabase',
        'backend.db_models',
        'backend.db_operations',
        'backend.db_supabase',
        'backend.payment_stripe',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.websockets_impl',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.loops.auto',
        'uvicorn.loops.uvloop',
        'uvicorn.loops.asyncio',
        'pydantic._internal._config',
        'pydantic._internal._generate_schema',
        'pydantic._internal._model_construction',
        'pydantic._internal._fields',
        'pydantic._internal._validators',
        'faster_whisper',
        'faster_whisper.transcribe',
        'faster_whisper.audio',
        'faster_whisper.decoding',
        'faster_whisper.tokenizer',
        'faster_whisper.vad',
        'faster_whisper.feature_extractor',
        'faster_whisper.model',
        'faster_whisper.utils',
        'ctranslate2',
        'ctranslate2.translators',
        'ctranslate2.models',
        'ctranslate2.specs',
        'ctranslate2.translators.cuda',
        'ctranslate2.translators.cpu',
        'onnxruntime',
        'onnxruntime.capi',
        'onnxruntime.capi.onnxruntime_pybind11_state',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'tkinter',
        'pandas',
        'numpy.distutils',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Use onedir mode (directory mode) instead of onefile
# This makes startup faster and file organization clearer
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # Key: Don't pack binaries into exe
    name='backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=True,  # Show console window (for debugging)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Can add icon path here
)

# Copy binaries to directory
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='backend'
)

