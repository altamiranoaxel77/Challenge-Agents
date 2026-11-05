"""CA-04: límites consecutivos permitidos (RN5, RN8)."""


def test_ca_04_limites_consecutivos_se_aceptan(svc_con_mic01):
    """CA-04: MIC-01 10:00–11:00; reservar MIC-01 11:00–12:00 y 09:00–10:00
    se aceptan las dos (RN8)."""
    svc = svc_con_mic01
    despues = svc.reservar("MIC-01", "Beto Ficticio", "2026-12-01 11:00", "2026-12-01 12:00")
    antes = svc.reservar("MIC-01", "Carla Ficticia", "2026-12-01 09:00", "2026-12-01 10:00")
    assert despues.estado == "activa" and antes.estado == "activa"
    assert {r.id for r in svc.listar(unidad="MIC-01", estado="activa")} == {
        "R-0001", "R-0002", "R-0003"}


def test_ca_04_listar_ordena_por_inicio(svc_con_mic01):
    """CA-04 / interfaz: listar ordena por inicio, id."""
    svc = svc_con_mic01
    svc.reservar("MIC-01", "Beto Ficticio", "2026-12-01 11:00", "2026-12-01 12:00")
    svc.reservar("MIC-01", "Carla Ficticia", "2026-12-01 09:00", "2026-12-01 10:00")
    assert [r.id for r in svc.listar()] == ["R-0003", "R-0001", "R-0002"]
