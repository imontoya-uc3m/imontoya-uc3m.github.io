#!/usr/bin/env python3
"""plantilla.html + juegos.json + logo.png  ->  index.html (un solo fichero)."""
import base64, json, pathlib

datos = json.loads(pathlib.Path("juegos.json").read_text("utf-8"))
compacto = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
assert "</script" not in compacto, "el JSON contiene un cierre de script"

logo = base64.b64encode(pathlib.Path("logo.png").read_bytes()).decode()
logo_uri = "data:image/png;base64," + logo

html = (pathlib.Path("plantilla.html").read_text("utf-8")
        .replace("/*__DATOS__*/", compacto)
        .replace("/*__LOGO__*/", logo_uri))
pathlib.Path("index.html").write_text(html, "utf-8")

n = len([g for g in datos["juegos"] if not g["expansion"] and g["duracion"]])
print(f"index.html: {len(html)/1024:.0f} KB · {n} juegos · logo incrustado · 1 sola peticion")
