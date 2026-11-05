"""Modelo y reglas de dominio puras (sin E/S).

Regla central (CLAUDE.md, RN5): intervalos semiabiertos [inicio, fin).
`se_superpone` es la ÚNICA comparación de intervalos del sistema.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

FORMATO_FECHA = "%Y-%m-%d %H:%M"  # S2
# Episodio 3 (#7): dígitos ASCII explícitos y sin strip (" 2026-12-01 10:00 " se rechaza).
_PATRON_FECHA = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}")
# S1 / Episodio 3 (#10): hora del laboratorio = UTC-3 fijo (Argentina no aplica horario de verano),
# independiente de la zona horaria configurada en la PC. Solo biblioteca estándar.
ZONA_LABORATORIO = timezone(timedelta(hours=-3), "America/Argentina/Buenos_Aires")


def ahora_laboratorio() -> datetime:
    """Hora local del laboratorio, sin tzinfo (las fechas se guardan sin offset, S1)."""
    return datetime.now(ZONA_LABORATORIO).replace(tzinfo=None)
DURACION_MAXIMA = timedelta(hours=12)  # S4
MAX_LARGO_SOLICITANTE = 100  # S7

ACTIVA = "activa"
CANCELADA = "cancelada"
ESTADOS = (ACTIVA, CANCELADA)


@dataclass(frozen=True)
class Unidad:
    id: str
    equipo: str


@dataclass(frozen=True)
class Reserva:
    id: str
    unidad: str
    solicitante: str
    inicio: datetime
    fin: datetime
    estado: str
    creada_en: datetime
    cancelada_en: datetime | None = None

    @property
    def bloquea(self) -> bool:
        """RN7: solo una reserva activa ocupa su intervalo."""
        return self.estado == ACTIVA


@dataclass(frozen=True)
class Disponibilidad:
    unidad: str
    inicio: datetime
    fin: datetime
    conflictos: list[Reserva]  # contrato docs/interfaz.md (Episodio 2)

    @property
    def disponible(self) -> bool:
        return not self.conflictos


def formatear_fecha(valor: datetime) -> str:
    return valor.strftime(FORMATO_FECHA)


def parsear_fecha(texto: str, campo: str) -> datetime:
    """RN3/S2: exige exactamente 'YYYY-MM-DD HH:MM' y una fecha de calendario válida."""
    from reservas.errores import ErrorValidacion

    if not isinstance(texto, str) or not _PATRON_FECHA.fullmatch(texto):
        raise ErrorValidacion(
            f"{campo} inválido: {texto!r}. Formato esperado YYYY-MM-DD HH:MM"
        )
    try:
        return datetime.strptime(texto, FORMATO_FECHA)
    except ValueError:
        raise ErrorValidacion(f"{campo} inválido: {texto!r} no es una fecha/hora real") from None


def normalizar_solicitante(texto: str) -> str:
    """RN2/S7: strip; no vacío; sin caracteres de control; espacios internos colapsados; largo máximo."""
    from reservas.errores import ErrorValidacion

    if not isinstance(texto, str):
        raise ErrorValidacion("El solicitante es obligatorio")
    limpio = texto.strip()
    if not limpio:
        raise ErrorValidacion("El solicitante no puede estar vacío ni ser solo espacios")
    # Episodio 3 (#13): saltos de línea, tabs, etc. romperían el formato de una línea por reserva.
    if any(unicodedata.category(c).startswith("C") for c in limpio):
        raise ErrorValidacion("El solicitante no puede contener caracteres de control (saltos de línea, tabs)")
    limpio = re.sub(r" {2,}", " ", limpio)
    if len(limpio) > MAX_LARGO_SOLICITANTE:
        raise ErrorValidacion(
            f"El solicitante supera {MAX_LARGO_SOLICITANTE} caracteres"
        )
    return limpio


def validar_intervalo(inicio: datetime, fin: datetime, ahora: datetime) -> None:
    """RN4 (inicio < fin estricto), S3 (no en el pasado), S4 (duración máxima)."""
    from reservas.errores import ErrorValidacion

    if not inicio < fin:
        raise ErrorValidacion("El inicio debe ser estrictamente anterior al fin")
    if inicio < ahora:
        raise ErrorValidacion(
            f"El inicio {formatear_fecha(inicio)} es anterior al momento actual "
            f"{formatear_fecha(ahora)}"
        )
    if fin - inicio > DURACION_MAXIMA:
        raise ErrorValidacion("La duración máxima de una reserva es de 12 horas")


def se_superpone(a_inicio: datetime, a_fin: datetime, b_inicio: datetime, b_fin: datetime) -> bool:
    """RN5: [a_inicio, a_fin) y [b_inicio, b_fin) comparten algún instante.

    Límites consecutivos (a_fin == b_inicio) NO se superponen (RN8).
    """
    return a_inicio < b_fin and b_inicio < a_fin


def conflictos(inicio: datetime, fin: datetime, reservas) -> list[Reserva]:
    """Reservas que bloquean (activas) y se superponen con [inicio, fin)."""
    return [
        r for r in reservas if r.bloquea and se_superpone(inicio, fin, r.inicio, r.fin)
    ]
