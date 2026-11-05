"""Persistencia en SQLite (R5).

Procedimiento (CLAUDE.md):
- toda escritura en `BEGIN IMMEDIATE`;
- nunca DELETE de reservas salvo `borrar_todo` (reiniciar-datos --confirmar);
- cancelar = UPDATE de estado + cancelada_en.
El ID visible `R-NNNN` deriva de la clave AUTOINCREMENT, que SQLite nunca reutiliza (S6).
"""
from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from reservas.dominio import ACTIVA, CANCELADA, Reserva

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS reservas (
    num          INTEGER PRIMARY KEY AUTOINCREMENT,
    unidad       TEXT NOT NULL,
    solicitante  TEXT NOT NULL,
    inicio       TEXT NOT NULL,
    fin          TEXT NOT NULL,
    estado       TEXT NOT NULL CHECK (estado IN ('activa', 'cancelada')),
    creada_en    TEXT NOT NULL,
    cancelada_en TEXT,
    CHECK (inicio < fin)
);
CREATE INDEX IF NOT EXISTS ix_reservas_unidad_estado ON reservas (unidad, estado);
"""

_FMT = "%Y-%m-%d %H:%M:%S"
_PATRON_ID = re.compile(r"R-(\d+)")


def id_a_num(reserva_id: str) -> int | None:
    m = _PATRON_ID.fullmatch(reserva_id.strip()) if isinstance(reserva_id, str) else None
    return int(m.group(1)) if m else None


def num_a_id(num: int) -> str:
    return f"R-{num:04d}"


def _a_texto(valor: datetime | None) -> str | None:
    return valor.strftime(_FMT) if valor else None


def _de_texto(valor: str | None) -> datetime | None:
    return datetime.strptime(valor, _FMT) if valor else None


def _a_reserva(fila: sqlite3.Row) -> Reserva:
    return Reserva(
        id=num_a_id(fila["num"]),
        unidad=fila["unidad"],
        solicitante=fila["solicitante"],
        inicio=_de_texto(fila["inicio"]),
        fin=_de_texto(fila["fin"]),
        estado=fila["estado"],
        creada_en=_de_texto(fila["creada_en"]),
        cancelada_en=_de_texto(fila["cancelada_en"]),
    )


class Repositorio:
    def __init__(self, ruta_db: str | Path):
        self.ruta_db = Path(ruta_db)
        self.ruta_db.parent.mkdir(parents=True, exist_ok=True)
        with self._conectar() as con:
            con.executescript(_ESQUEMA)

    def _conectar(self) -> sqlite3.Connection:
        # isolation_level=None: control manual de transacciones.
        con = sqlite3.connect(self.ruta_db, isolation_level=None, timeout=5)
        con.row_factory = sqlite3.Row
        return con

    @contextmanager
    def transaccion(self):
        """Transacción de escritura: BEGIN IMMEDIATE ... COMMIT / ROLLBACK."""
        con = self._conectar()
        try:
            con.execute("BEGIN IMMEDIATE")
            yield con
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
        finally:
            con.close()

    @contextmanager
    def lectura(self):
        con = self._conectar()
        try:
            yield con
        finally:
            con.close()

    # --- consultas (reciben una conexión para participar de la transacción) ---
    @staticmethod
    def reservas_de_unidad(con, unidad: str, estado: str | None = None) -> list[Reserva]:
        sql, params = "SELECT * FROM reservas WHERE unidad = ?", [unidad]
        if estado:
            sql += " AND estado = ?"
            params.append(estado)
        return [_a_reserva(f) for f in con.execute(sql + " ORDER BY inicio, num", params)]

    @staticmethod
    def obtener(con, reserva_id: str) -> Reserva | None:
        num = id_a_num(reserva_id)
        if num is None:
            return None
        fila = con.execute("SELECT * FROM reservas WHERE num = ?", (num,)).fetchone()
        return _a_reserva(fila) if fila else None

    @staticmethod
    def listar(con, unidad: str | None = None, estado: str | None = None) -> list[Reserva]:
        condiciones, params = [], []
        if unidad:
            condiciones.append("unidad = ?")
            params.append(unidad)
        if estado:
            condiciones.append("estado = ?")
            params.append(estado)
        where = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""
        filas = con.execute(f"SELECT * FROM reservas{where} ORDER BY inicio, num", params)
        return [_a_reserva(f) for f in filas]

    # --- escrituras ---
    @staticmethod
    def insertar(con, unidad, solicitante, inicio, fin, creada_en) -> str:
        cur = con.execute(
            "INSERT INTO reservas (unidad, solicitante, inicio, fin, estado, creada_en) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (unidad, solicitante, _a_texto(inicio), _a_texto(fin), ACTIVA, _a_texto(creada_en)),
        )
        return num_a_id(cur.lastrowid)

    @staticmethod
    def marcar_cancelada(con, reserva_id: str, cuando: datetime) -> None:
        con.execute(
            "UPDATE reservas SET estado = ?, cancelada_en = ? WHERE num = ? AND estado = ?",
            (CANCELADA, _a_texto(cuando), id_a_num(reserva_id), ACTIVA),
        )

    @staticmethod
    def borrar_todo(con) -> int:
        """ÚNICO borrado permitido (S9). La secuencia de IDs no se reinicia."""
        return con.execute("DELETE FROM reservas").rowcount
