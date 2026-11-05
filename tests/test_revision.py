"""Pruebas de regresión de los hallazgos de `revisor-reglas` aceptados por el autor (Episodio 3).

Escritas por el agente principal después de aplicar las correcciones.
Cada test cita el número de hallazgo (#N) de docs/decisiones.md.
"""
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest

from conftest import RAIZ, _env_cli
from reservas import dominio
from reservas.errores import ErrorAlmacenamiento, ErrorValidacion, ReservaNoEncontrada
from reservas.servicio import ServicioReservas


# ---------- Grupo A: errores de almacenamiento sin traceback (#1, #2) ----------

def test_rev_01_inventario_ausente_es_error_controlado(tmp_path):
    with pytest.raises(ErrorAlmacenamiento):
        ServicioReservas(tmp_path / "r.db", inventario_path=tmp_path / "no-existe.json")


@pytest.mark.parametrize("contenido", ["no es json", '{"otra": []}', '{"unidades": [{"id": "A", "equipo": "x"}, {"id": "A", "equipo": "y"}]}'])
def test_rev_01_inventario_invalido_es_error_controlado(tmp_path, contenido):
    ruta = tmp_path / "inv.json"
    ruta.write_text(contenido, encoding="utf-8")
    with pytest.raises(ErrorAlmacenamiento):
        ServicioReservas(tmp_path / "r.db", inventario_path=ruta)


def test_rev_01_cli_inventario_ausente_muestra_error_sin_traceback(tmp_path):
    env = _env_cli()
    env["RESERVAS_INVENTARIO"] = str(tmp_path / "no-existe.json")
    res = subprocess.run([sys.executable, "-m", "reservas", "--db", str(tmp_path / "r.db"), "inventario"],
                         capture_output=True, text=True, encoding="utf-8", env=env, cwd=str(RAIZ), timeout=60)
    assert res.returncode == 1
    assert res.stderr.startswith("ERROR:")
    assert "Traceback" not in res.stderr


def test_rev_02_cli_bd_corrupta_muestra_error_sin_traceback(tmp_path, cli):
    corrupta = tmp_path / "corrupta.db"
    corrupta.write_bytes(b"esto no es una base sqlite" * 10)
    res = cli("listar", db_path=corrupta)
    assert res.returncode == 1
    assert res.stderr.startswith("ERROR:")
    assert "Traceback" not in res.stderr


# ---------- Grupo B: entradas estrictas (#7, #8, #13) ----------

@pytest.mark.parametrize("fecha", [" 2026-12-01 10:00", "2026-12-01 10:00 ", "٢٠٢٦-١٢-٠١ ١٠:٠٠"])
def test_rev_07_fecha_con_espacios_o_digitos_no_ascii_se_rechaza(svc, fecha):
    with pytest.raises(ErrorValidacion, match="Formato esperado"):
        svc.reservar("MIC-01", "Ana Ficticia", fecha, "2026-12-01 11:00")


@pytest.mark.parametrize("variante", ["R-1", "R-00001", " R-0001", "R-0001 ", "r-0001"])
def test_rev_08_id_no_canonico_no_existe(svc_con_mic01, variante):
    with pytest.raises(ReservaNoEncontrada):
        svc_con_mic01.cancelar(variante)
    assert svc_con_mic01.obtener("R-0001").estado == dominio.ACTIVA


@pytest.mark.parametrize("nombre", ["Ana\nFicticia", "Ana\tFicticia", "Ana\x00Ficticia"])
def test_rev_13_solicitante_con_caracteres_de_control_se_rechaza(svc, nombre):
    with pytest.raises(ErrorValidacion):
        svc.reservar("MIC-01", nombre, "2026-12-01 10:00", "2026-12-01 11:00")


def test_rev_13_espacios_internos_se_colapsan(svc):
    r = svc.reservar("MIC-01", "  Ana    Ficticia ", "2026-12-01 10:00", "2026-12-01 11:00")
    assert r.solicitante == "Ana Ficticia"


# ---------- Grupo C: interfaz (#4, #6, #9) ----------

def test_rev_04_listar_separa_columnas_con_dos_espacios(cli):
    cli("reservar", "MIC-01", "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 11:00")
    linea = cli("listar").stdout.strip()
    assert linea == "R-0001  MIC-01  2026-12-01 10:00  2026-12-01 11:00  activa  Ana Ficticia"


def test_rev_06_reiniciar_sin_confirmar_no_crea_la_bd(tmp_path, cli):
    nueva = tmp_path / "sub" / "nunca.db"
    res = cli("reiniciar-datos", db_path=nueva)
    assert res.returncode == 1
    assert not nueva.exists()


def test_rev_06_inventario_no_crea_la_bd(tmp_path, cli):
    nueva = tmp_path / "sub" / "nunca.db"
    assert cli("inventario", db_path=nueva).returncode == 0
    assert not nueva.exists()


def test_rev_09_listar_con_unidad_desconocida_es_error(cli):
    res = cli("listar", "--unidad", "mic-01")
    assert res.returncode == 1
    assert res.stderr.startswith("ERROR:")


# ---------- Grupo D: zona horaria (#10) ----------

def test_rev_10_ahora_es_utc_menos_3_independiente_de_la_pc():
    esperado = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=3)
    obtenido = dominio.ahora_laboratorio()
    assert obtenido.tzinfo is None
    assert abs(obtenido - esperado) < timedelta(seconds=5)
