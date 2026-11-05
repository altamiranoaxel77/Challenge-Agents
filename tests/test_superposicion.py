"""CA-02 y CA-03: rechazo de superposición (RN5, RN6)."""
import pytest

from reservas.errores import ReservaError, Superposicion


def test_ca_02_rechaza_superposicion_parcial(svc_con_mic01):
    """CA-02: MIC-01 10:00–11:00; reservar MIC-01 10:30–11:30 se rechaza
    por superposición y no se crea nada (RN6)."""
    svc = svc_con_mic01
    with pytest.raises(Superposicion) as exc:
        svc.reservar("MIC-01", "Beto Ficticio", "2026-12-01 10:30", "2026-12-01 11:30")
    assert [c.id for c in exc.value.conflictos] == ["R-0001"]
    assert [r.id for r in svc.listar()] == ["R-0001"]


def test_ca_02_superposicion_es_reservaerror(svc_con_mic01):
    """CA-02: Superposicion hereda de ReservaError (contrato de interfaz)."""
    with pytest.raises(ReservaError):
        svc_con_mic01.reservar("MIC-01", "Beto Ficticio", "2026-12-01 10:30", "2026-12-01 11:30")


def test_ca_02_rechazo_no_consume_id(svc_con_mic01):
    """CA-02: "no se crea nada": la próxima reserva válida es R-0002."""
    svc = svc_con_mic01
    with pytest.raises(Superposicion):
        svc.reservar("MIC-01", "Beto Ficticio", "2026-12-01 10:30", "2026-12-01 11:30")
    r = svc.reservar("MIC-01", "Beto Ficticio", "2026-12-01 11:00", "2026-12-01 12:00")
    assert r.id == "R-0002"


@pytest.mark.parametrize(
    "inicio, fin",
    [
        ("2026-12-01 09:00", "2026-12-01 12:00"),  # contiene la reserva
        ("2026-12-01 10:15", "2026-12-01 10:45"),  # está contenida
        ("2026-12-01 10:00", "2026-12-01 11:00"),  # idéntica
        ("2026-12-01 09:30", "2026-12-01 10:01"),  # se solapa 1 minuto al inicio
        ("2026-12-01 10:59", "2026-12-01 11:30"),  # se solapa 1 minuto al final
    ],
    ids=["contiene", "contenida", "identica", "solapa-inicio", "solapa-fin"],
)
def test_ca_03_rechaza_contenida_y_contenedora(svc_con_mic01, inicio, fin):
    """CA-03: MIC-01 10:00–11:00; 09:00–12:00 (contiene) y 10:15–10:45 (contenida)
    se rechazan (RN5, RN6). Variantes adicionales de solapamiento por RN5."""
    svc = svc_con_mic01
    with pytest.raises(Superposicion):
        svc.reservar("MIC-01", "Beto Ficticio", inicio, fin)
    assert len(svc.listar()) == 1
