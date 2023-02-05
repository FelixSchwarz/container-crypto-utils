# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# .spec file was generated with:
#   - (setup.py develop)
#   - pyinstaller --onefile --hidden-import=docopt scripts/crypted-container-ctl
from pathlib import Path
SRC_PATH = Path(SPECPATH).absolute().as_posix()

from PyInstaller.utils.hooks import copy_metadata


a = Analysis(['scripts/crypted-container-ctl'],
             pathex=[SRC_PATH],
             binaries=[],
             datas=[
                *copy_metadata('ContainerCryptoUtils'),
             ],
             hiddenimports=[
                 'docopt',
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='crypted-container-ctl',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )
