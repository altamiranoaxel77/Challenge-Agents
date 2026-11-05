"""CA-13: consulta de disponibilidad (R2, RN10)."""
import pytest

from reservas.errores import ErrorValidacion, Superposicion, UnidadDesconocida


def test_ca_13_no_disponible_informa_conflicto(svc_con_mic01):
    """CA-13: MIC-01 10:00–11:00; MIC-01 10:30–11:30 no está disponible e
    informa el conflicto R-0001 (R2)."""
    d = svc_con_mic01.disponibilidad("MIC-01", "2026-12-01 10:30", "2026-12-01 11:30")
    assert d.disponible is False
    assert [c.id for c in d.conflictos] == ["R-0001"]


def test_ca_13_consecutivo_disponible(svc_con_mic01):
    """CA-13: MIC-01 11:00–12:00 está disponible (RN8, RN10)."""
    d = svc_con_mic01.disponibilidad("MIC-01", "2026-12-01 11:00", "2026-12-01 12:00")
    assert d.disponible is True
    assert d.conflictos == []


def test_ca_13_otra_unidad_disponible(svc_con_mic01):
    """CA-13: MIC-02 10:00–11:00 está disponible (RN9, RN10)."""
    d = svc_con_mic01.disponibilidad("MIC-02", "2026-12-01 10:00", "2026-12-01 11:00")
    assert d.disponible is True
    assert d.conflictos == []


def test_ca_13_disponibilidad_no_crea_reservas(svc_con_mic01):
    """CA-13: consultar disponibilidad no modifica la BD."""
    svc = svc_con_mic01
    svc.disponibilidad("MIC-01", "2026-12-01 11:00", "2026-12-01 12:00")
    assert [r.id for r in svc.listar()] == ["R-0001"]


@pytest.mark.parametrize(
    "inicio, fin",
    [
        ("2026-12-01 11:00", "2026-12-01 12:00"),
        ("2026-12-01 09:00", "2026-12-01 10:00"),
        ("2026-12-01 10:30", "2026-12-01 11:30"),
        ("2026-12-01 09:00", "2026-12-01 12:00"),
    ],
)
def test_ca_13_disponible_equivale_a_reserva_aceptada(svc_con_mic01, inicio, fin):
    """CA-13 / RN10: si la consulta informa "disponible", la reserva equivalente
    se acepta; si no, se rechaza."""
    svc = svc_con_mic01
    d = svc.disponibilidad("MIC-01", inicio, fin)
    if d.disponible:
        assert svc.reservar("MIC-01", "Beto Ficticio", inicio, fin).estado == "activa"
    else:
        # Auditoría de pruebas: antes era pytest.raises(Exception), demasiado amplio.
        with pytest.raises(Superposicion):
            svc.reservar("MIC-01", "Beto Ficticio", inicio, fin)


ENTRADAS_INVALIDAS = [
    ("XYZ-99", "2026-12-01 10:00", "2026-12-01 11:00"),
    ("mic-01", "2026-12-01 10:00", "2026-12-01 11:00"),
    ("MIC-01", "2026-02-30 10:00", "2026-12-01 11:00"),
    ("MIC-01", "2026-12-01 25:00", "2026-12-01 11:00"),
    ("MIC-01", "01/12/2026 10:00", "2026-12-01 11:00"),
    ("MIC-01", "abc", "2026-12-01 11:00"),
    ("MIC-01", "2026-12-01 10:00", "2026-12-01 10:00"),
    ("MIC-01", "2026-12-01 11:00", "2026-12-01 10:00"),
    ("MIC-01", "2026-11-29 10:00", "2026-11-29 11:00"),
    ("MIC-01", "2026-12-01 08:00", "2026-12-01 20:01"),
]


@pytest.mark.parametrize("unidad, inicio, fin", ENTRADAS_INVALIDAS)
def test_ca_13_entrada_invalida_mismo_error_que_creacion(svc, unidad, inicio, fin):
    """CA-13: una entrada inválida en disponibilidad produce el mismo error que
    en la creación (RN10: RN1, RN3, RN4, S3, S4)."""
    with pytest.raises(ErrorValidacion) as e_disp:
        svc.disponibilidad(unidad, inicio, fin)
    with pytest.raises(ErrorValidacion) as e_crear:
        svc.reservar(unidad, "Ana Ficticia", inicio, fin)
    assert type(e_disp.value) is type(e_crear.value)
    assert str(e_disp.value) == str(e_crear.value)


@pytest.mark.parametrize("unidad", ["XYZ-99", "mic-01"])
def test_ca_13_unidad_desconocida_en_disponibilidad(svc, unidad):
    """CA-13 / RN10 + RN1: unidad desconocida lanza UnidadDesconocida también al consultar."""
    with pytest.raises(UnidadDesconocida):
        svc.disponibilidad(unidad, "2026-12-01 10:00", "2026-12-01 11:00")
