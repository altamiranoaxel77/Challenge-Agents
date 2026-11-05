"""CA-01: creación válida de una reserva (R3) e inventario (R1)."""
from datetime import datetime

from conftest import AHORA


def test_ca_01_crear_reserva_valida(svc):
    """CA-01: BD vacía; se reserva MIC-01 "Ana Ficticia" 2026-12-01 10:00–11:00
    -> se crea R-0001 activa con los datos ingresados (R3)."""
    r = svc.reservar("MIC-01", "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 11:00")
    assert r.id == "R-0001"
    assert r.estado == "activa"
    assert r.unidad == "MIC-01"
    assert r.solicitante == "Ana Ficticia"
    assert r.inicio == datetime(2026, 12, 1, 10, 0)
    assert r.fin == datetime(2026, 12, 1, 11, 0)
    assert r.cancelada_en is None
    assert isinstance(r.creada_en, datetime)


def test_ca_01_reserva_creada_se_puede_obtener_y_listar(svc):
    """CA-01: la reserva creada queda registrada y se recupera por ID y en el listado."""
    svc.reservar("MIC-01", "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 11:00")
    r = svc.obtener("R-0001")
    assert (r.unidad, r.solicitante, r.estado) == ("MIC-01", "Ana Ficticia", "activa")
    assert [x.id for x in svc.listar()] == ["R-0001"]


def test_ca_01_ids_secuenciales(svc):
    """CA-01 / S6: los IDs son R-0001, R-0002, ... secuenciales."""
    a = svc.reservar("MIC-01", "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 11:00")
    b = svc.reservar("OSC-01", "Beto Ficticio", "2026-12-01 10:00", "2026-12-01 11:00")
    assert (a.id, b.id) == ("R-0001", "R-0002")


def test_ca_01_inventario_precargado(svc):
    """CA-01 (precondición R1): el inventario precargado contiene las 5 unidades."""
    unidades = {u.id: u.equipo for u in svc.inventario()}
    assert set(unidades) == {"MIC-01", "MIC-02", "OSC-01", "MUL-01", "FUE-01"}
    assert unidades["OSC-01"] == "Osciloscopio"
