"""Casos de uso: inventario, disponibilidad, reservar, cancelar, listar (R1-R6).

RN10: `disponibilidad` y `reservar` comparten `_validar_consulta` y `dominio.conflictos`
(que usa `se_superpone`), así ambas aplican exactamente las mismas reglas.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

from reservas import dominio
from reservas.dominio import ACTIVA, CANCELADA, ESTADOS, Disponibilidad, Reserva, Unidad
from reservas.errores import (
    ErrorValidacion,
    ReservaNoEncontrada,
    ReservaYaCancelada,
    Superposicion,
    UnidadDesconocida,
)
from reservas.inventario import RAIZ_PROYECTO, cargar_inventario
from reservas.repositorio import Repositorio

DB_POR_DEFECTO = RAIZ_PROYECTO / "data" / "reservas.db"


class ServicioReservas:
    def __init__(
        self,
        db_path: str | Path = DB_POR_DEFECTO,
        inventario_path: str | Path | None = None,
        ahora: Callable[[], datetime] | None = None,
    ):
        self._unidades = cargar_inventario(inventario_path)
        self._repo = Repositorio(db_path)
        self._reloj = ahora or dominio.ahora_laboratorio  # S1: UTC-3 fijo

    def _ahora(self) -> datetime:
        # Resolución de minutos (S2): se descartan segundos del reloj.
        return self._reloj().replace(second=0, microsecond=0)

    # --- validación compartida (RN10) ---
    def _validar_unidad(self, unidad: str) -> str:
        if unidad not in self._unidades:  # RN1: coincidencia exacta
            conocidas = ", ".join(self._unidades)
            raise UnidadDesconocida(f"Unidad desconocida: {unidad!r}. Unidades: {conocidas}")
        return unidad

    def _validar_consulta(self, unidad: str, inicio: str, fin: str) -> tuple[datetime, datetime]:
        self._validar_unidad(unidad)
        ini = dominio.parsear_fecha(inicio, "inicio")
        fi = dominio.parsear_fecha(fin, "fin")
        dominio.validar_intervalo(ini, fi, self._ahora())
        return ini, fi

    # --- casos de uso ---
    def inventario(self) -> list[Unidad]:
        return list(self._unidades.values())

    def disponibilidad(self, unidad: str, inicio: str, fin: str) -> Disponibilidad:
        ini, fi = self._validar_consulta(unidad, inicio, fin)
        with self._repo.lectura() as con:
            activas = self._repo.reservas_de_unidad(con, unidad, ACTIVA)
        return Disponibilidad(unidad, ini, fi, dominio.conflictos(ini, fi, activas))

    def reservar(self, unidad: str, solicitante: str, inicio: str, fin: str) -> Reserva:
        ini, fi = self._validar_consulta(unidad, inicio, fin)
        nombre = dominio.normalizar_solicitante(solicitante)
        with self._repo.transaccion() as con:
            # Chequeo e inserción en la misma transacción (procedimiento de persistencia).
            activas = self._repo.reservas_de_unidad(con, unidad, ACTIVA)
            choques = dominio.conflictos(ini, fi, activas)
            if choques:
                ids = ", ".join(r.id for r in choques)
                raise Superposicion(
                    f"{unidad} ya está reservada en ese intervalo (conflicto con {ids})", choques
                )
            nuevo_id = self._repo.insertar(con, unidad, nombre, ini, fi, self._reloj())
            return self._repo.obtener(con, nuevo_id)

    def cancelar(self, reserva_id: str) -> Reserva:
        with self._repo.transaccion() as con:
            reserva = self._repo.obtener(con, reserva_id)
            if reserva is None:
                raise ReservaNoEncontrada(f"No existe la reserva {reserva_id!r}")
            if reserva.estado == CANCELADA:
                raise ReservaYaCancelada(f"La reserva {reserva.id} ya estaba cancelada")
            self._repo.marcar_cancelada(con, reserva.id, self._reloj())
            return self._repo.obtener(con, reserva.id)

    def obtener(self, reserva_id: str) -> Reserva:
        with self._repo.lectura() as con:
            reserva = self._repo.obtener(con, reserva_id)
        if reserva is None:
            raise ReservaNoEncontrada(f"No existe la reserva {reserva_id!r}")
        return reserva

    def listar(self, unidad: str | None = None, estado: str | None = None) -> list[Reserva]:
        # S10: el filtro de unidad aplica RN1 (unidad exacta del inventario).
        if unidad is not None:
            self._validar_unidad(unidad)
        if estado is not None and estado not in ESTADOS:
            raise ErrorValidacion(f"Estado inválido: {estado!r}. Use: {', '.join(ESTADOS)}")
        with self._repo.lectura() as con:
            return self._repo.listar(con, unidad, estado)

    def reiniciar_datos(self) -> int:
        """S9: borra TODAS las reservas. El CLI exige --confirmar."""
        with self._repo.transaccion() as con:
            return self._repo.borrar_todo(con)
