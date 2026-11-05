"""Jerarquía de errores de negocio (ver docs/interfaz.md)."""


class ReservaError(Exception):
    """Base de todos los errores de negocio y validación."""


class ErrorValidacion(ReservaError):
    """Entrada inválida: solicitante, fechas, intervalo, pasado o duración (RN2-RN4, S3, S4)."""


class UnidadDesconocida(ErrorValidacion):
    """La unidad no existe en el inventario (RN1)."""


class Superposicion(ReservaError):
    """El intervalo se superpone con reservas activas de la misma unidad (RN6)."""

    def __init__(self, mensaje, conflictos):
        super().__init__(mensaje)
        self.conflictos = list(conflictos)


class ErrorAlmacenamiento(ReservaError):
    """Inventario o base de datos ausente, ilegible o corrupta (Episodio 3, hallazgos #1/#2)."""


class ReservaNoEncontrada(ReservaError):
    """No existe una reserva con ese ID (RN11)."""


class ReservaYaCancelada(ReservaError):
    """La reserva ya estaba cancelada (RN11)."""
