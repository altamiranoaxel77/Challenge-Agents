"""CA-14: persistencia tras reinicio (R5) y listado con filtros (R6)."""
import re
from datetime import datetime

from conftest import AHORA
from reservas.servicio import ServicioReservas


def _filas(stdout):
    """Parsea las líneas de `listar` (campos separados por 2+ espacios)."""
    return [re.split(r"\s{2,}", l.strip()) for l in stdout.splitlines() if l.strip().startswith("R-")]


def _preparar_por_cli(cli):
    assert cli("reservar", "MIC-01", "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 11:00").returncode == 0
    assert cli("reservar", "MIC-02", "Beto Ficticio", "2026-12-01 10:00", "2026-12-01 11:00").returncode == 0
    assert cli("reservar", "OSC-01", "Carla Ficticia", "2026-12-02 14:00", "2026-12-02 15:30").returncode == 0
    assert cli("cancelar", "R-0001").returncode == 0


def test_ca_14_listar_en_nuevo_proceso_recupera_todo(cli):
    """CA-14: con reservas activas y canceladas creadas por CLI, un nuevo proceso
    `listar` sobre la misma BD muestra todas con mismo ID, datos y estado (R5, R6)."""
    _preparar_por_cli(cli)
    res = cli("listar")
    assert res.returncode == 0, res.stderr
    assert _filas(res.stdout) == [
        ["R-0001", "MIC-01", "2026-12-01 10:00", "2026-12-01 11:00", "cancelada", "Ana Ficticia"],
        ["R-0002", "MIC-02", "2026-12-01 10:00", "2026-12-01 11:00", "activa", "Beto Ficticio"],
        ["R-0003", "OSC-01", "2026-12-02 14:00", "2026-12-02 15:30", "activa", "Carla Ficticia"],
    ]


def test_ca_14_intervalo_cancelado_sigue_disponible_tras_reinicio(cli):
    """CA-14: en un nuevo proceso, el intervalo cancelado sigue disponible y se
    puede reservar; el nuevo ID no reutiliza los anteriores (R5, RN7, S6)."""
    _preparar_por_cli(cli)
    d = cli("disponibilidad", "MIC-01", "2026-12-01 10:00", "2026-12-01 11:00")
    assert d.returncode == 0, d.stderr
    assert d.stdout.strip().startswith("DISPONIBLE")
    r = cli("reservar", "MIC-01", "Dario Ficticio", "2026-12-01 10:00", "2026-12-01 11:00")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().split()[:2] == ["CREADA", "R-0004"]


def test_ca_14_activa_sigue_bloqueando_tras_reinicio(cli):
    """CA-14: tras reiniciar, una reserva activa sigue bloqueando su intervalo (R5, RN6)."""
    _preparar_por_cli(cli)
    d = cli("disponibilidad", "MIC-02", "2026-12-01 10:30", "2026-12-01 11:30")
    assert d.returncode == 0
    assert d.stdout.strip().startswith("NO DISPONIBLE")
    assert "R-0002" in d.stdout
    r = cli("reservar", "MIC-02", "Dario Ficticio", "2026-12-01 10:30", "2026-12-01 11:30")
    assert r.returncode == 1
    assert r.stderr.strip().startswith("ERROR:")


def test_ca_14_listar_filtros_en_nuevo_proceso(cli):
    """CA-14 / R6: listar filtra por unidad y por estado tras reinicio."""
    _preparar_por_cli(cli)
    act = _filas(cli("listar", "--estado", "activa").stdout)
    assert [f[0] for f in act] == ["R-0002", "R-0003"]
    canc = _filas(cli("listar", "--estado", "cancelada").stdout)
    assert [f[0] for f in canc] == ["R-0001"]
    mic = _filas(cli("listar", "--unidad", "MIC-01").stdout)
    assert [f[0] for f in mic] == ["R-0001"]
    combo = _filas(cli("listar", "--unidad", "MIC-02", "--estado", "cancelada").stdout)
    assert combo == []


def test_ca_14_dos_instancias_del_servicio(db):
    """CA-14: dos ServicioReservas distintos sobre la misma BD ven los mismos
    datos (R5): lo creado/cancelado por uno lo recupera el otro."""
    s1 = ServicioReservas(db, ahora=lambda: AHORA)
    s1.reservar("MIC-01", "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 11:00")
    s1.reservar("MIC-02", "Beto Ficticio", "2026-12-01 10:00", "2026-12-01 11:00")
    c = s1.cancelar("R-0001")
    del s1

    s2 = ServicioReservas(db, ahora=lambda: AHORA)
    r1 = s2.obtener("R-0001")
    assert (r1.unidad, r1.solicitante, r1.estado) == ("MIC-01", "Ana Ficticia", "cancelada")
    assert r1.inicio == datetime(2026, 12, 1, 10, 0) and r1.fin == datetime(2026, 12, 1, 11, 0)
    assert r1.cancelada_en == c.cancelada_en
    assert s2.obtener("R-0002").estado == "activa"
    assert s2.disponibilidad("MIC-01", "2026-12-01 10:00", "2026-12-01 11:00").disponible is True
    assert s2.disponibilidad("MIC-02", "2026-12-01 10:00", "2026-12-01 11:00").disponible is False
    assert s2.reservar("MIC-01", "Carla Ficticia", "2026-12-01 10:00", "2026-12-01 11:00").id == "R-0003"


def test_ca_14_servicio_lee_lo_creado_por_cli(cli, db):
    """CA-14: lo creado por CLI en otro proceso lo recupera la API sobre la misma BD."""
    _preparar_por_cli(cli)
    svc = ServicioReservas(db, ahora=lambda: AHORA)
    assert [(r.id, r.estado) for r in svc.listar()] == [
        ("R-0001", "cancelada"), ("R-0002", "activa"), ("R-0003", "activa")]
