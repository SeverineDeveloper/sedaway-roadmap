#!/usr/bin/env python3
"""Copia el mapa del roadmap a este repo, quitando los datos privados, y lo publica.

Uso:
    python sync.py            # sanea, y si hay cambios hace commit + push
    python sync.py --watch    # lo repite cada vez que cambia el data.json de origen
    python sync.py --dry-run  # solo sanea y verifica; no hace commit ni push

El origen (la carpeta fuera de git) se puede cambiar con la variable ROADMAP_SRC.
"""
import json, os, re, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(os.environ.get(
    "ROADMAP_SRC",
    r"C:\Users\deleg\Documents\Github Projects\SedaWay\Appartamentos graphify\mapa",
))

EMP_GENERIC = "Entidad del grupo. Los datos societarios no se publican."
PHONE = re.compile(r"\+?\d[\d ()-]{8,}\d")
IDS = re.compile(r"\b(RNC|RM|Reg\.)\s*[\w.-]+", re.I)
PRIVATE_HOSTS = re.compile(r"https?://(?:docs|drive)\.google\.com\S*", re.I)


def sanitize(data):
    for n in data["nodes"]:
        n.pop("url", None)  # enlaces a Google Drive
        if n.get("type") == "emp":  # empresa y legal: nombre sí, datos societarios no
            n["description"] = EMP_GENERIC
    raw = json.dumps(data, ensure_ascii=False)
    raw = PRIVATE_HOSTS.sub("[enlace privado]", raw)
    raw = PHONE.sub("[número oculto]", raw)
    raw = IDS.sub(lambda m: m.group(1) + " [oculto]", raw)
    return json.loads(raw)


def verify(text):
    problems = []
    if re.search(r"google\.com", text, re.I):
        problems.append("queda un enlace de Google")
    if re.search(r"\d{1,2}-\d{2}-\d{5}-\d", text):
        problems.append("queda un RNC")
    if re.search(r"\+1[ -]?\d{3}[ -]?\d{3}", text):
        problems.append("queda un teléfono")
    if re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text):
        problems.append("queda un correo")
    return problems


def build():
    data = json.loads((SRC / "data.json").read_text(encoding="utf-8"))
    out = json.dumps(sanitize(data), ensure_ascii=False, indent=1) + "\n"
    problems = verify(out)
    if problems:
        sys.exit("No se publica: " + "; ".join(problems))
    (HERE / "data.json").write_text(out, encoding="utf-8")
    shutil.copyfile(SRC / "index.html", HERE / "index.html")


def git(*a):
    return subprocess.run(["git", *a], cwd=HERE, capture_output=True, text=True, check=True).stdout


def publish(dry):
    build()
    if dry:
        print("Verificado: sin enlaces, teléfonos, RNC ni correos.")
        return
    if not git("status", "--porcelain").strip():
        print("Sin cambios.")
        return
    git("add", "index.html", "data.json")
    git("commit", "-m", "Actualiza el roadmap " + time.strftime("%Y-%m-%d %H:%M"))
    git("push")
    print("Publicado.")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    if "--watch" in sys.argv:
        last = None
        while True:
            m = (SRC / "data.json").stat().st_mtime
            if m != last:
                last = m
                publish(dry)
            time.sleep(5)
    else:
        publish(dry)
