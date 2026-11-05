"""Carga del inventario precargado (R1). Solo lectura."""
from __future__ import annotations

import json
import os
from pathlib import Path

from reservas.dominio import Unidad
from reservas.errores import ErrorAlmacenamiento

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
INVENTARIO_POR_DEFECTO = RAIZ_PROYECTO / "data" / "inventario.json"


def ruta_inventario(ruta: str | Path | None = None) -> Path:
    """Prioridad: argumento > variable RESERVAS_INVENTARIO > data/inventario.json del repo (S11)."""
    return Path(ruta or os.environ.get("RESERVAS_INVENTARIO") or INVENTARIO_POR_DEFECTO)


def cargar_inventario(ruta: str | Path | None = None) -> dict[str, Unidad]:
    ruta = ruta_inventario(ruta)
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
        items = datos["unidades"]
        unidades: dict[str, Unidad] = {}
        for item in items:
            unidad = Unidad(id=item["id"], equipo=item["equipo"])
            if unidad.id in unidades:
                raise ValueError(f"ID de unidad duplicado: {unidad.id}")
            unidades[unidad.id] = unidad
    except OSError as e:
        raise ErrorAlmacenamiento(f"No se pudo leer el inventario {ruta}: {e.strerror or e}") from e
    except (ValueError, KeyError, TypeError) as e:
        raise ErrorAlmacenamiento(f"Inventario inválido en {ruta}: {e}") from e
    return unidades
