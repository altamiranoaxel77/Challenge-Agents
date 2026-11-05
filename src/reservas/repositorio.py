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
from reservas.errores import ErrorAlmacenamiento

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
_PATRON_ID = re.compile(r"R-([0-9]{4,})")


def id_a_num(reserva_id: str) -> int | None:
    """S6 / Episodio 3 (#8): solo la forma canónica exacta (`R-0001`); `R-1` o ` R-0001 ` no existen."""
    m = _PATRON_ID.fullmatch(reserva_id) if isinstance(reserva_id, str) else None
    if not m:
        return None
    num = int(m.group(1))
    return num if num_a_id(num) == reserva_id else None


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


@contextmanager
def _traducir_errores(ruta_db: Path):
    """Episodio 3 (#2): errores de E/S o SQLite -> ErrorAlmacenamiento (CLI: 'ERROR:' + exit 1)."""
    try:
        yield
    except sqlite3.Error as e:
        raise ErrorAlmacenamiento(f"Base de datos inaccesible o corrupta ({ruta_db}): {e}") from e
    except OSError as e:
        raise ErrorAlmacenamiento(f"No se pudo acceder a {ruta_db}: {e.strerror or e}") from e


class Repositorio:
    def __init__(self, ruta_db: str | Path):
        self.ruta_db = Path(ruta_db)
        with _traducir_errores(self.ruta_db):
            self.ruta_db.parent.mkdir(parents=True, exist_ok=True)
            con = self._conectar()
            try:
                con.executescript(_ESQUEMA)
            finally:
                con.close()  # Episodio 3 (#12): cierre explícito

    def _conectar(self) -> sqlite3.Connection:
        # isolation_level=None: control manual de transacciones.
        con = sqlite3.connect(self.ruta_db, isolation_level=None, timeout=5)
        con.row_factory = sqlite3.Row
        return con

    @contextmanager
    def transaccion(self):
        """Transacción de escritura: BEGIN IMMEDIATE ... COMMIT / ROLLBACK."""
        with _traducir_errores(self.ruta_db):
            con = self._conectar()
            try:
                # Episodio 3 (#3): BEGIN fuera del try del ROLLBACK; si falla, no hay nada que deshacer.
                con.execute("BEGIN IMMEDIATE")
                try:
                    yield con
                    con.execute("COMMIT")
                except BaseException:
                    if con.in_transaction:
                        con.execute("ROLLBACK")
                    raise
            finally:
                con.close()

    @contextmanager
    def lectura(self):
        with _traducir_errores(self.ruta_db):
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
