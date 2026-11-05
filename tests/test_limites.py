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


# --- Agregadas en la auditoría de pruebas (agente principal) ---

def test_ca_04_consecutivos_cruzando_medianoche(svc):
    """CA-04 / RN8: 23:00–00:00 y 00:00–01:00 del día siguiente son consecutivos;
    23:30–00:30 se superpone con ambos."""
    a = svc.reservar("MIC-01", "Ana Ficticia", "2026-12-01 23:00", "2026-12-02 00:00")
    b = svc.reservar("MIC-01", "Beto Ficticio", "2026-12-02 00:00", "2026-12-02 01:00")
    assert (a.estado, b.estado) == ("activa", "activa")
    d = svc.disponibilidad("MIC-01", "2026-12-01 23:30", "2026-12-02 00:30")
    assert [c.id for c in d.conflictos] == [a.id, b.id]


def test_ca_04_fecha_bisiesta_valida(svc):
    """RN3: 2028-02-29 es una fecha real (año bisiesto) y se acepta."""
    r = svc.reservar("FUE-01", "Ana Ficticia", "2028-02-29 10:00", "2028-02-29 11:00")
    assert r.inicio.day == 29
