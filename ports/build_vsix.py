#!/usr/bin/env python3
"""
build_vsix.py — empaqueta el theme Ocular como extension VSCode instalable
(.vsix), reusando SIEMPRE los 4 color-theme.json ya generados por
ports/build_ports.py en ports/out/vscode/ (fuente unica, no se duplican
aqui) y los metadatos versionados en ports/vscode-extension/.

Metodo primario: `npx --yes @vscode/vsce package` (herramienta oficial,
valida el manifest contra el schema de VSCode). Si npx/vsce no estan
disponibles en la maquina, cae a un empaquetador manual via zipfile que
replica el formato VSIX -- ver docstring de _package_manual().

Uso: python3 ports/build_vsix.py
Salida: ports/out/vscode/ocular-<version>.vsix (version leida del propio
package.json empaquetado -- una sola fuente de verdad, no se hardcodea).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
EXT_SRC = os.path.join(HERE, "vscode-extension")
THEMES_SRC = os.path.join(HERE, "out", "vscode")
OUT_DIR = THEMES_SRC  # ports/out/vscode/ -- mismo directorio que los JSON fuente

THEME_FILES = [
    "ocular-rooibos-color-theme.json",
    "ocular-manzanilla-color-theme.json",
    "ocular-rooibos-deutan-color-theme.json",
    "ocular-manzanilla-deutan-color-theme.json",
]


def _stage(staging):
    for name in ("package.json", "README.md", "LICENSE"):
        shutil.copy(os.path.join(EXT_SRC, name), os.path.join(staging, name))
    shutil.copy(os.path.join(REPO, "preview", "icon.png"), os.path.join(staging, "icon.png"))
    themes_dir = os.path.join(staging, "themes")
    os.makedirs(themes_dir, exist_ok=True)
    for fname in THEME_FILES:
        src = os.path.join(THEMES_SRC, fname)
        if not os.path.exists(src):
            print(f"FALTA {src} -- corre ports/build_ports.py primero", file=sys.stderr)
            sys.exit(1)
        shutil.copy(src, os.path.join(themes_dir, fname))


def _package_vsce(staging, out_path):
    if shutil.which("npx") is None:
        return False
    result = subprocess.run(
        ["npx", "--yes", "@vscode/vsce", "package", "-o", out_path],
        cwd=staging, capture_output=True, text=True,
    )
    print(result.stdout.strip())
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return False
    return os.path.exists(out_path)


def _package_manual(staging, out_path):
    """
    Fallback sin node/vsce: arma el .vsix a mano con zipfile.

    Un .vsix es un paquete OPC (Open Packaging Conventions, el mismo
    contenedor de .docx/.xlsx): un zip con
      - [Content_Types].xml      (content-types por extension de archivo)
      - extension.vsixmanifest   (metadata: id, version, publisher...)
      - extension/               (el contenido de la extension tal cual)

    Formato documentado en
    https://code.visualstudio.com/api/working-with-extensions/publishing-extension
    (seccion "Packaging extensions"). No se ejercita en esta maquina (aqui
    SI hay node/npx) -- ver reporte de la corrida real.
    """
    pkg = json.load(open(os.path.join(staging, "package.json")))
    manifest = f"""<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="{pkg['name']}" Version="{pkg['version']}" Publisher="{pkg['publisher']}"/>
    <DisplayName>{pkg['displayName']}</DisplayName>
    <Description xml:space="preserve">{pkg.get('description', '')}</Description>
    <Categories>{','.join(pkg.get('categories', []))}</Categories>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code"/>
  </Installation>
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/>
  </Assets>
</PackageManifest>
"""
    content_types = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json"/>
  <Default Extension="md" ContentType="text/markdown"/>
  <Default Extension="png" ContentType="image/png"/>
  <Default Extension="vsixmanifest" ContentType="text/xml"/>
</Types>
"""
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("extension.vsixmanifest", manifest)
        for root, _, files in os.walk(staging):
            for fname in files:
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, staging)
                zf.write(full, os.path.join("extension", rel))
    print(f"OK {out_path} (empaquetado manual via zipfile -- vsce no disponible)")
    return True


def main():
    staging = tempfile.mkdtemp(prefix="ocular-vsix-")
    try:
        _stage(staging)
        with open(os.path.join(staging, "package.json")) as f:
            version = json.load(f)["version"]
        os.makedirs(OUT_DIR, exist_ok=True)
        out_path = os.path.join(OUT_DIR, f"ocular-{version}.vsix")
        if os.path.exists(out_path):
            os.remove(out_path)

        ok = _package_vsce(staging, out_path)
        if not ok:
            print("vsce no disponible o fallo -- usando fallback manual (zipfile)")
            ok = _package_manual(staging, out_path)
        if not ok or not os.path.exists(out_path):
            print("ERROR: no se genero el .vsix", file=sys.stderr)
            sys.exit(1)

        size_kb = os.path.getsize(out_path) / 1024
        print(f"\nOK {out_path} ({size_kb:.1f} KiB)")
    finally:
        shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    main()
