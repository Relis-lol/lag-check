# Build on Windows; bundle only explicit resources, never session data.
a = Analysis(
    ['run.py'], pathex=[], binaries=[],
    datas=[('lagcheck/resources/*.ps1', 'lagcheck/resources')],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='LagCheck',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False, uac_admin=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='LagCheck')
