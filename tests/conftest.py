"""Fixtures comunes derivadas de docs/interfaz.md y docs/especificacion.md.

Todas las pruebas usan una BD temporal (tmp_path), nunca data/reservas.db.
El "ahora" fijo es 2026-11-30 08:00 (sección 7 de la especificación).
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from reservas.servicio import ServicioReservas

RAIZ = Path(__file__).resolve().parent.parent
AHORA = datetime(2026, 11, 30, 8, 0)
AHORA_TXT = "2026-11-30 08:00"


@pytest.fixture
def db(tmp_path):
    return tmp_path / "r.db"


@pytest.fixture
def svc(db):
    return ServicioReservas(db, ahora=lambda: AHORA)


@pytest.fixture
def svc_con_mic01(svc):
    """MIC-01 reservado 2026-12-01 10:00–11:00 (precondición de varios CA)."""
    r = svc.reservar("MIC-01", "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 11:00")
    assert r.id == "R-0001"
    return svc


def _env_cli():
    env = os.environ.copy()
    env.pop("RESERVAS_DB", None)
    env["RESERVAS_AHORA"] = AHORA_TXT
    env["PYTHONIOENCODING"] = "utf-8"
    return env


@pytest.fixture
def cli(db):
    """Ejecuta `python -m reservas --db <tmp> ...` en un proceso separado."""

    def correr(*args, db_path=None):
        ruta = db_path if db_path is not None else db
        return subprocess.run(
            [sys.executable, "-m", "reservas", "--db", str(ruta), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=_env_cli(),
            cwd=str(RAIZ),
            timeout=60,
        )

    return correr
