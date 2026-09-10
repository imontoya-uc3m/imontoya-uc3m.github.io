#!/usr/bin/env python3
"""
Genera juegos.json a partir del inventario Montoya + datasets BGG (GitHub).
Los datasets se FILTRAN por los BGG ID del inventario: solo salen los juegos
que Montoya tiene en casa.
"""
import json, re, unicodedata
import pandas as pd

INV = "/mnt/user-data/uploads/Inventario_Montoya_BGG__1_.xlsx"
D1 = "bgg.csv"      # jalwz17/Board-Game-Data-Analysis (Kaggle, feb-2021)
D2 = "rank22.csv"   # albert-marrero/bgg-data (snapshot 13-07-2022)
OUT = "juegos.json"

# ---------- 1. Inventario ----------
inv = pd.read_excel(INV, "Hoja 1")
inv.columns = [c.strip() for c in inv.columns]
inv["BGG ID"] = pd.to_numeric(inv["BGG ID"], errors="coerce")
inv["Nombre"] = inv["Nombre"].astype(str).str.strip()

ids_inventario = set(inv["BGG ID"].dropna().astype(int))
print(f"Inventario: {len(inv)} filas, {len(ids_inventario)} BGG ID unicos")

# ---------- 2. Datasets FILTRADOS por el inventario ----------
d1 = pd.read_csv(D1, sep=";", encoding="utf-8-sig", decimal=",")
d1["ID"] = pd.to_numeric(d1["ID"], errors="coerce")
d1 = d1.dropna(subset=["ID"])
d1["ID"] = d1["ID"].astype(int)
d1 = d1[d1["ID"].isin(ids_inventario)].drop_duplicates("ID").set_index("ID")
print(f"bgg_dataset filtrado: {len(d1)} filas (de 20.000+)")

d2 = pd.read_csv(D2)
d2 = d2.dropna(subset=["id"])
d2["id"] = d2["id"].astype(int)
d2 = d2[d2["id"].isin(ids_inventario)].drop_duplicates("id").set_index("id")
print(f"rankings-2022 filtrado: {len(d2)} filas (de 137.000+)")

# ---------- 3. Parche manual ----------
# Juegos que NO estan en los datasets (posteriores a 2021 o mal indexados).
# Marcados con fuente="manual" para que sean auditables y corregibles.
MANUAL = {
    342942: dict(min_j=1, max_j=4, min_t=90, max_t=150, dif=3.7,
                 dom="Strategy Games", mec="Card Drafting, Hand Management, Tile Placement, Set Collection"),
    366013: dict(min_j=2, max_j=6, min_t=30, max_t=60, dif=1.9,
                 dom="Strategy Games, Family Games", mec="Hand Management, Simultaneous Action Selection, Racing"),
    345584: dict(min_j=2, max_j=4, min_t=15, max_t=20, dif=1.7,
                 dom="Strategy Games", mec="Hand Management, Take That, Variable Player Powers"),
    154597: dict(min_j=2, max_j=2, min_t=20, max_t=20, dif=2.3,
                 dom="Abstract Games", mec="Grid Movement, Pattern Building, Tile Placement"),
    311900: dict(min_j=1, max_j=4, min_t=60, max_t=90, dif=2.6,
                 dom="Strategy Games, Thematic Games", mec="Area Majority, Card Play Conflict Resolution, Dice Rolling"),
    30909:  dict(min_j=4, max_j=8, min_t=30, max_t=30, dif=1.4,
                 dom="Party Games", mec="Bluffing, Negotiation, Simultaneous Action Selection"),
    154883: dict(min_j=3, max_j=6, min_t=45, max_t=45, dif=1.7,
                 dom="Party Games", mec="Storytelling, Role Playing, Player Judge"),
}

# Expansiones: no se recomiendan como juego independiente.
EXPANSIONES = {225370, 330149, 309116, 202976}

# Juegos sin BGG ID. Sin datos verificables -> quedan fuera del recomendador
# hasta que se rellenen a mano en este diccionario (clave = nombre exacto).
SIN_ID = {}

DOM_ES = {
    "Strategy Games": "Estrategia", "Family Games": "Familiar",
    "Party Games": "Fiesta", "Thematic Games": "Tematico",
    "Abstract Games": "Abstracto", "Wargames": "Wargame",
    "Customizable Games": "Personalizable", "Children's Games": "Infantil",
}


def limpio(x):
    if pd.isna(x):
        return None
    return x


juegos, sin_datos = [], []

for _, row in inv.iterrows():
    bid = row["BGG ID"]
    nombre = row["Nombre"]
    if pd.isna(bid):
        sin_datos.append({"nombre": nombre, "motivo": "sin BGG ID en el inventario"})
        continue
    bid = int(bid)
    g = {
        "id": bid,
        "nombre": nombre,
        "nombre_bgg": limpio(row["Juego en BGG"]),
        "expansion": bid in EXPANSIONES,
    }

    if bid in d1.index:
        r = d1.loc[bid]
        g.update(
            min_jugadores=int(r["Min Players"]) if pd.notna(r["Min Players"]) else None,
            max_jugadores=int(r["Max Players"]) if pd.notna(r["Max Players"]) else None,
            duracion=int(r["Play Time"]) if pd.notna(r["Play Time"]) else None,
            edad_min=int(r["Min Age"]) if pd.notna(r["Min Age"]) else None,
            anyo=int(r["Year Published"]) if pd.notna(r["Year Published"]) else None,
            nota=round(float(r["Rating Average"]), 2) if pd.notna(r["Rating Average"]) else None,
            dificultad=round(float(r["Complexity Average"]), 2) if pd.notna(r["Complexity Average"]) else None,
            mecanicas=[m.strip() for m in str(r["Mechanics"]).split(",")] if pd.notna(r["Mechanics"]) else [],
            categorias=[DOM_ES.get(d.strip(), d.strip()) for d in str(r["Domains"]).split(",")] if pd.notna(r["Domains"]) else [],
            fuente="bgg_dataset_2021",
        )
    elif bid in MANUAL:
        m = MANUAL[bid]
        g.update(
            min_jugadores=m["min_j"], max_jugadores=m["max_j"],
            duracion=m["max_t"], duracion_min=m["min_t"],
            dificultad=m["dif"],
            mecanicas=[x.strip() for x in m["mec"].split(",")],
            categorias=[DOM_ES.get(d.strip(), d.strip()) for d in m["dom"].split(",")],
            fuente="manual",
        )
    else:
        g.update(min_jugadores=None, max_jugadores=None, duracion=None,
                 mecanicas=[], categorias=[], fuente="incompleto")

    # nota/descripcion del snapshot 2022 (mas reciente que el de 2021)
    if bid in d2.index:
        r2 = d2.loc[bid]
        if pd.notna(r2.get("avg_rating")):
            g["nota"] = round(float(r2["avg_rating"]), 2)
        if pd.notna(r2.get("short_description")):
            g["descripcion"] = str(r2["short_description"]).strip()
        if pd.notna(r2.get("year_published")) and not g.get("anyo"):
            g["anyo"] = int(r2["year_published"])

    if g["duracion"] is None and not g["expansion"]:
        sin_datos.append({"nombre": nombre, "id": bid, "motivo": "sin duracion/jugadores en ningun dataset"})
    juegos.append(g)

# dedup por id conservando el primero
vistos, dedup = set(), []
for g in juegos:
    if g["id"] in vistos:
        continue
    vistos.add(g["id"])
    dedup.append(g)

jugables = [g for g in dedup if not g["expansion"] and g["duracion"] is not None]

salida = {
    "generado": "2026-09-10",
    "fuentes": [
        "jalwz17/Board-Game-Data-Analysis (bgg_dataset.csv, snapshot feb-2021)",
        "albert-marrero/bgg-data (CSV/rankings/2022-07-13.csv)",
        "parche manual para titulos posteriores a 2021 (campo fuente=manual)",
    ],
    "juegos": dedup,
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(salida, f, ensure_ascii=False, indent=1)

print(f"\n{len(dedup)} juegos unicos escritos en {OUT}")
print(f"  jugables y completos : {len(jugables)}")
print(f"  expansiones          : {sum(1 for g in dedup if g['expansion'])}")
print(f"  incompletos          : {sum(1 for g in dedup if g['fuente'] == 'incompleto')}")
print(f"\nSin datos ({len(sin_datos)}):")
for s in sin_datos:
    print("  -", s["nombre"], "|", s["motivo"])
