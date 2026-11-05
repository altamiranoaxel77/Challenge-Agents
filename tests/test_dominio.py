"""Pruebas unitarias de las reglas puras de dominio (RN5, RN7, RN8).

Agregadas en la auditoría de pruebas: el mutante M2 (`conflictos` ignora el estado)
sobrevivía porque el servicio ya filtra las activas en SQL. Estas pruebas fijan la
regla en la propia función de dominio, independientemente de quién la llame.
"""
from datetime import datetime

import pytest

from reservas.dominio import ACTIVA, CANCELADA, Reserva, conflictos, se_superpone


def _r(id_, h_ini, h_fin, estado=ACTIVA):
    return Reserva(id=id_, unidad="MIC-01", solicitante="Ana Ficticia",
                   inicio=datetime(2026, 12, 1, h_ini), fin=datetime(2026, 12, 1, h_fin),
                   estado=estado, creada_en=datetime(2026, 11, 30, 8))


def _d(h, m=0):
    return datetime(2026, 12, 1, h, m)


@pytest.mark.parametrize(
    "a, b, esperado",
    [
        ((10, 11), (11, 12), False),   # consecutivo después (RN8)
        ((10, 11), (9, 10), False),    # consecutivo antes (RN8)
        ((10, 11), (10, 11), True),    # idéntico
        ((10, 12), (11, 13), True),    # parcial
        ((9, 13), (10, 11), True),     # contiene
        ((10, 11), (12, 13), False),   # disjunto
    ],
)
def test_dominio_se_superpone_semiabierto(a, b, esperado):
    """RN5: [inicio, fin) — y la relación es simétrica."""
    assert se_superpone(_d(a[0]), _d(a[1]), _d(b[0]), _d(b[1])) is esperado
    assert se_superpone(_d(b[0]), _d(b[1]), _d(a[0]), _d(a[1])) is esperado


def test_dominio_conflictos_ignora_canceladas():
    """RN7: aunque reciba reservas canceladas, `conflictos` solo devuelve las activas."""
    activa = _r("R-0001", 10, 11)
    cancelada = _r("R-0002", 10, 11, estado=CANCELADA)
    assert conflictos(_d(10, 30), _d(11, 30), [activa, cancelada]) == [activa]
    assert conflictos(_d(10, 30), _d(11, 30), [cancelada]) == []


def test_dominio_conflictos_respeta_limites_consecutivos():
    """RN8 a nivel de dominio: una reserva que termina justo al inicio no es conflicto."""
    assert conflictos(_d(11), _d(12), [_r("R-0001", 10, 11)]) == []
