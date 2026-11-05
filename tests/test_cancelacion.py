"""CA-11 y CA-12: cancelación (R4, RN7, RN11)."""
from datetime import datetime

import pytest

from reservas.errores import ReservaError, ReservaNoEncontrada, ReservaYaCancelada
from reservas.servicio import ServicioReservas


def _datos(r):
    return (r.id, r.unidad, r.solicitante, r.inicio, r.fin, r.estado, r.creada_en, r.cancelada_en)


def test_ca_11_cancelar_conserva_datos_y_registra_cancelada_en(svc_con_mic01):
    """CA-11: R-0001 activa en MIC-01 10:00–11:00; al cancelarla pasa a
    `cancelada` con sus datos intactos y `cancelada_en` registrado (R4)."""
    svc = svc_con_mic01
    antes = svc.obtener("R-0001")
    c = svc.cancelar("R-0001")
    assert c.id == "R-0001"
    assert c.estado == "cancelada"
    assert isinstance(c.cancelada_en, datetime)
    assert (c.unidad, c.solicitante, c.inicio, c.fin, c.creada_en) == (
        antes.unidad, antes.solicitante, antes.inicio, antes.fin, antes.creada_en)
    guardada = svc.obtener("R-0001")
    assert guardada.estado == "cancelada"
    assert guardada.cancelada_en is not None
    # el registro se conserva en el historial
    assert [r.id for r in svc.listar(estado="cancelada")] == ["R-0001"]


def test_ca_11_cancelar_libera_el_intervalo(svc_con_mic01):
    """CA-11: tras cancelar R-0001, MIC-01 10:00–11:00 queda disponible y se
    puede reservar de nuevo como R-0002 (R4, RN7)."""
    svc = svc_con_mic01
    svc.cancelar("R-0001")
    d = svc.disponibilidad("MIC-01", "2026-12-01 10:00", "2026-12-01 11:00")
    assert d.disponible is True
    assert d.conflictos == []
    nueva = svc.reservar("MIC-01", "Beto Ficticio", "2026-12-01 10:00", "2026-12-01 11:00")
    assert nueva.id == "R-0002"
    assert nueva.estado == "activa"
    assert {(r.id, r.estado) for r in svc.listar()} == {("R-0001", "cancelada"), ("R-0002", "activa")}


def test_ca_11_cancelar_reserva_pasada_permitido(db):
    """CA-11 / S3: una reserva que ya pasó se puede cancelar."""
    ahora = {"v": datetime(2026, 11, 30, 8, 0)}
    svc = ServicioReservas(db, ahora=lambda: ahora["v"])
    svc.reservar("MIC-01", "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 11:00")
    ahora["v"] = datetime(2026, 12, 2, 9, 0)
    c = svc.cancelar("R-0001")
    assert c.estado == "cancelada"


def test_ca_12_cancelar_ya_cancelada_falla_sin_cambios(svc_con_mic01):
    """CA-12: R-0001 cancelada; cancelarla otra vez produce un error y no cambia nada (RN11)."""
    svc = svc_con_mic01
    svc.cancelar("R-0001")
    antes = _datos(svc.obtener("R-0001"))
    with pytest.raises(ReservaYaCancelada):
        svc.cancelar("R-0001")
    assert _datos(svc.obtener("R-0001")) == antes
    assert len(svc.listar()) == 1


def test_ca_12_cancelar_inexistente_falla_sin_cambios(svc_con_mic01):
    """CA-12: cancelar R-9999 produce un error y no cambia nada (RN11)."""
    svc = svc_con_mic01
    antes = [_datos(r) for r in svc.listar()]
    with pytest.raises(ReservaNoEncontrada):
        svc.cancelar("R-9999")
    assert [_datos(r) for r in svc.listar()] == antes


@pytest.mark.parametrize("exc", [ReservaNoEncontrada, ReservaYaCancelada])
def test_ca_12_errores_heredan_de_reservaerror(exc):
    """CA-12: los errores de cancelación heredan de ReservaError (interfaz)."""
    assert issubclass(exc, ReservaError)


def test_ca_12_obtener_inexistente(svc):
    """CA-12 / interfaz: obtener un ID inexistente lanza ReservaNoEncontrada."""
    with pytest.raises(ReservaNoEncontrada):
        svc.obtener("R-9999")
