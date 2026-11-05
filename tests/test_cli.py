"""CLI: CA-15 (reiniciar-datos), códigos de salida 0/1/2 y formato de salida."""
import re

import pytest


def _ids_listados(stdout):
    return [l.split()[0] for l in stdout.splitlines() if l.strip().startswith("R-")]


def _con_reservas(cli):
    assert cli("reservar", "MIC-01", "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 11:00").returncode == 0
    assert cli("reservar", "OSC-01", "Beto Ficticio", "2026-12-01 10:00", "2026-12-01 11:00").returncode == 0
    assert cli("cancelar", "R-0002").returncode == 0


# ---------------- CA-15 (S9) ----------------

def test_ca_15_reiniciar_sin_confirmar_no_borra(cli):
    """CA-15: con reservas, `reiniciar-datos` sin --confirmar no borra nada
    (S9); escribe ERROR: en stderr y sale con 1 (interfaz)."""
    _con_reservas(cli)
    res = cli("reiniciar-datos")
    assert res.returncode == 1
    assert res.stderr.strip().startswith("ERROR:")
    assert _ids_listados(cli("listar").stdout) == ["R-0001", "R-0002"]


def test_ca_15_reiniciar_con_confirmar_borra_todo(cli):
    """CA-15: `reiniciar-datos --confirmar` borra todas las reservas (S9)."""
    _con_reservas(cli)
    res = cli("reiniciar-datos", "--confirmar")
    assert res.returncode == 0, res.stderr
    lst = cli("listar")
    assert lst.returncode == 0
    assert _ids_listados(lst.stdout) == []
    d = cli("disponibilidad", "MIC-01", "2026-12-01 10:00", "2026-12-01 11:00")
    assert d.stdout.strip().startswith("DISPONIBLE")


# ---------------- Código 0: operaciones exitosas ----------------

def test_ca_01_cli_reservar_salida_creada(cli):
    """CA-01 por CLI: reservar sale con 0 y la línea empieza con `CREADA R-0001`."""
    res = cli("reservar", "MIC-01", "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 11:00")
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip().split()[:2] == ["CREADA", "R-0001"]


def test_ca_11_cli_cancelar_salida_cancelada(cli):
    """CA-11 por CLI: cancelar sale con 0 y la línea empieza con `CANCELADA R-0001`."""
    cli("reservar", "MIC-01", "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 11:00")
    res = cli("cancelar", "R-0001")
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip().split()[:2] == ["CANCELADA", "R-0001"]
    assert "cancelada" in cli("listar").stdout


def test_ca_13_cli_disponibilidad_ambas_respuestas_codigo_0(cli):
    """CA-13 por CLI: DISPONIBLE y NO DISPONIBLE son consultas exitosas (código 0);
    NO DISPONIBLE informa el conflicto R-0001."""
    cli("reservar", "MIC-01", "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 11:00")
    no = cli("disponibilidad", "MIC-01", "2026-12-01 10:30", "2026-12-01 11:30")
    assert no.returncode == 0
    assert no.stdout.strip().startswith("NO DISPONIBLE")
    assert "R-0001" in no.stdout
    si = cli("disponibilidad", "MIC-01", "2026-12-01 11:00", "2026-12-01 12:00")
    assert si.returncode == 0
    assert si.stdout.strip().startswith("DISPONIBLE")
    otra = cli("disponibilidad", "MIC-02", "2026-12-01 10:00", "2026-12-01 11:00")
    assert otra.returncode == 0
    assert otra.stdout.strip().startswith("DISPONIBLE")


def test_ca_01_cli_inventario(cli):
    """CA-01 (precondición R1): `inventario` lista las 5 unidades y sale con 0."""
    res = cli("inventario")
    assert res.returncode == 0, res.stderr
    for uid in ["MIC-01", "MIC-02", "OSC-01", "MUL-01", "FUE-01"]:
        assert uid in res.stdout


def test_ca_14_cli_formato_listar(cli):
    """CA-14 / interfaz: `listar` escribe una línea por reserva con el formato
    `R-0001  MIC-01  2026-12-01 10:00  2026-12-01 11:00  activa  Ana Ficticia`."""
    cli("reservar", "MIC-01", "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 11:00")
    res = cli("listar")
    assert res.returncode == 0
    lineas = [l for l in res.stdout.splitlines() if l.strip().startswith("R-")]
    assert len(lineas) == 1
    assert re.split(r"\s{2,}", lineas[0].strip()) == [
        "R-0001", "MIC-01", "2026-12-01 10:00", "2026-12-01 11:00", "activa", "Ana Ficticia"]


def test_ca_07_cli_solicitante_con_espacios_se_guarda_sin_ellos(cli):
    """CA-07 por CLI: "  Ana Ficticia  " se guarda como "Ana Ficticia"."""
    assert cli("reservar", "MIC-01", "  Ana Ficticia  ", "2026-12-01 10:00", "2026-12-01 11:00").returncode == 0
    linea = [l for l in cli("listar").stdout.splitlines() if l.strip().startswith("R-")][0]
    assert re.split(r"\s{2,}", linea.strip())[-1] == "Ana Ficticia"


# ---------------- Código 1: errores de negocio / validación ----------------

@pytest.mark.parametrize(
    "args",
    [
        ("reservar", "XYZ-99", "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 11:00"),   # CA-06
        ("reservar", "mic-01", "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 11:00"),   # CA-06
        ("reservar", "MIC-01", "   ", "2026-12-01 10:00", "2026-12-01 11:00"),            # CA-07
        ("reservar", "MIC-01", "", "2026-12-01 10:00", "2026-12-01 11:00"),               # CA-07
        ("reservar", "MIC-01", "Ana Ficticia", "2026-02-30 10:00", "2026-12-01 11:00"),   # CA-08
        ("reservar", "MIC-01", "Ana Ficticia", "abc", "2026-12-01 11:00"),                # CA-08
        ("reservar", "MIC-01", "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 10:00"),   # CA-09
        ("reservar", "MIC-01", "Ana Ficticia", "2026-11-29 10:00", "2026-11-29 11:00"),   # CA-10
        ("reservar", "MIC-01", "Ana Ficticia", "2026-12-01 08:00", "2026-12-01 20:01"),   # CA-10
        ("disponibilidad", "XYZ-99", "2026-12-01 10:00", "2026-12-01 11:00"),             # CA-13
        ("disponibilidad", "MIC-01", "01/12/2026 10:00", "2026-12-01 11:00"),             # CA-13
        ("cancelar", "R-9999"),                                                            # CA-12
    ],
)
def test_ca_06_a_13_cli_errores_codigo_1(cli, args):
    """CA-06..CA-13 por CLI: errores de validación o negocio salen con código 1,
    mensaje en stderr que empieza con `ERROR:` y no crean reservas."""
    res = cli(*args)
    assert res.returncode == 1, (res.stdout, res.stderr)
    assert res.stderr.strip().startswith("ERROR:")
    assert _ids_listados(cli("listar").stdout) == []


def test_ca_02_cli_superposicion_codigo_1(cli):
    """CA-02 por CLI: la superposición sale con 1 y no crea nada."""
    cli("reservar", "MIC-01", "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 11:00")
    res = cli("reservar", "MIC-01", "Beto Ficticio", "2026-12-01 10:30", "2026-12-01 11:30")
    assert res.returncode == 1
    assert res.stderr.strip().startswith("ERROR:")
    assert _ids_listados(cli("listar").stdout) == ["R-0001"]


def test_ca_12_cli_cancelar_dos_veces_codigo_1(cli):
    """CA-12 por CLI: cancelar una reserva ya cancelada sale con 1."""
    cli("reservar", "MIC-01", "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 11:00")
    assert cli("cancelar", "R-0001").returncode == 0
    res = cli("cancelar", "R-0001")
    assert res.returncode == 1
    assert res.stderr.strip().startswith("ERROR:")


# ---------------- Código 2: uso incorrecto de argumentos ----------------

@pytest.mark.parametrize(
    "args",
    [
        (),                                                  # sin comando
        ("comando-inexistente",),
        ("reservar", "MIC-01", "Ana Ficticia"),              # faltan argumentos
        ("cancelar",),
        ("disponibilidad", "MIC-01", "2026-12-01 10:00"),
        ("reiniciar-datos", "--opcion-rara"),
    ],
    ids=["sin-comando", "inexistente", "reservar-incompleto", "cancelar-sin-id",
         "disponibilidad-incompleta", "opcion-desconocida"],
)
def test_ca_cli_uso_incorrecto_codigo_2(cli, args):
    """Sección 8 / interfaz: uso incorrecto de argumentos sale con código 2 (argparse)."""
    res = cli(*args)
    assert res.returncode == 2, (res.stdout, res.stderr)
