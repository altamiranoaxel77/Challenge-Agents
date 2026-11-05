"""CA-05 y CA-06: unidades distintas (RN9) y unidad desconocida (RN1)."""
import pytest

from reservas.errores import ErrorValidacion, UnidadDesconocida


def test_ca_05_unidades_distintas_simultaneas(svc_con_mic01):
    """CA-05: MIC-01 10:00–11:00; reservar MIC-02 10:00–11:00 se acepta (RN9)."""
    r = svc_con_mic01.reservar("MIC-02", "Beto Ficticio", "2026-12-01 10:00", "2026-12-01 11:00")
    assert r.id == "R-0002"
    assert r.unidad == "MIC-02"
    assert r.estado == "activa"


@pytest.mark.parametrize("unidad", ["XYZ-99", "mic-01", "", "MIC-01 ", "Mic-01"])
def test_ca_06_unidad_desconocida(svc, unidad):
    """CA-06: reservar XYZ-99 o mic-01 se rechaza por unidad desconocida (RN1,
    la comparación distingue mayúsculas)."""
    with pytest.raises(UnidadDesconocida):
        svc.reservar(unidad, "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 11:00")
    assert svc.listar() == []


def test_ca_06_unidad_desconocida_es_error_validacion(svc):
    """CA-06: UnidadDesconocida es subclase de ErrorValidacion (interfaz)."""
    with pytest.raises(ErrorValidacion):
        svc.reservar("XYZ-99", "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 11:00")
