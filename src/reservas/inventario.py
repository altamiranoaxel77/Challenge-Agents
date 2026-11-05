"""Carga del inventario precargado (R1). Solo lectura."""
from __future__ import annotations

import json
from pathlib import Path

from reservas.dominio import Unidad

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
INVENTARIO_POR_DEFECTO = RAIZ_PROYECTO / "data" / "inventario.json"


def cargar_inventario(ruta: str | Path | None = None) -> dict[str, Unidad]:
    ruta = Path(ruta) if ruta else INVENTARIO_POR_DEFECTO
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    unidades: dict[str, Unidad] = {}
    for item in datos["unidades"]:
        unidad = Unidad(id=item["id"], equipo=item["equipo"])
        if unidad.id in unidades:
            raise ValueError(f"ID de unidad duplicado en el inventario: {unidad.id}")
        unidades[unidad.id] = unidad
    return unidades
