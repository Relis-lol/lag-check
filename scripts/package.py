"""Package an already-built portable directory with notices and a SHA-256 sum."""

import hashlib
import importlib.metadata
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lagcheck import __version__  # noqa: E402


def main():
    bundle = ROOT / "dist" / "LagCheck"
    assert (bundle / "LagCheck.exe").is_file(), "Run PyInstaller first"
    for name in ["README.md", "LICENSE", "CHANGELOG.md", "SECURITY.md"]:
        shutil.copy2(ROOT / name, bundle / name)
    shutil.copytree(ROOT / "docs", bundle / "docs", dirs_exist_ok=True)
    notices = bundle / "third-party-licenses"
    notices.mkdir(exist_ok=True)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    assert python_license.exists(), "Python license missing"
    shutil.copy2(python_license, notices / "Python-LICENSE.txt")
    tcl_licenses = list((Path(sys.base_prefix) / "tcl").glob("*/license.terms"))
    # The official Windows Python LICENSE.txt already includes Tcl and Tk terms.
    # Some distributions also ship an additional Tk license. Preserve it if present.
    license_text = python_license.read_text(encoding="utf-8")
    assert "Scriptics" in license_text and "Apple Inc." in license_text, (
        "Tcl/Tk terms missing from Python license"
    )
    for p in tcl_licenses:
        shutil.copy2(p, notices / (p.parent.name + "-LICENSE.txt"))
    dependencies = [
        "pyinstaller",
        "pyinstaller-hooks-contrib",
        "altgraph",
        "packaging",
        "pefile",
        "pywin32-ctypes",
        "setuptools",
    ]
    for dependency in dependencies:
        dist = importlib.metadata.distribution(dependency)
        texts = [
            f
            for f in (dist.files or [])
            if "license" in f.name.lower() or f.name.lower().startswith("copying")
        ]
        if not texts:
            raise RuntimeError("Missing dependency license: " + dependency)
        for index, f in enumerate(texts):
            source = Path(dist.locate_file(f))
            if source.is_file():
                shutil.copy2(source, notices / f"{dependency}-{index}-{source.name}")
    (notices / "NOTICE.txt").write_text(
        "Lag Check uses Python and Tcl/Tk at runtime. Their original license texts are included. PyInstaller is used to package the application; its bootloader exception permits distributing this MIT-licensed application. Build-tool license notices are included for transparency. No dependency license is replaced by the project MIT license.\n",
        encoding="utf-8",
    )
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(exist_ok=True)
    target = artifacts / f"LagCheck-{__version__}-windows-x64.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                z.write(path, path.relative_to(bundle.parent))
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (artifacts / "SHA256SUMS.txt").write_text(
        f"{digest}  {target.name}\n", encoding="ascii"
    )
    print(f"Packaged {target.name}: {target.stat().st_size / 1024**2:.1f} MiB")


if __name__ == "__main__":
    main()
