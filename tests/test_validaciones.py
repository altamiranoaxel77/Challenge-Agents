"""CA-07 a CA-10: solicitante, fechas, inicio<fin, pasado y duración."""
import pytest

from reservas.errores import ErrorValidacion

VALIDO_I = "2026-12-01 10:00"
VALIDO_F = "2026-12-01 11:00"


# ---------------- CA-07 (RN2, S7) ----------------

@pytest.mark.parametrize("solicitante", ["", "   ", "\t", " \n "], ids=["vacio", "espacios", "tab", "mixto"])
def test_ca_07_solicitante_vacio_se_rechaza(svc, solicitante):
    """CA-07: el solicitante "" o "   " se rechaza (RN2)."""
    with pytest.raises(ErrorValidacion):
        svc.reservar("MIC-01", solicitante, VALIDO_I, VALIDO_F)
    assert svc.listar() == []


def test_ca_07_solicitante_se_guarda_sin_espacios(svc):
    """CA-07: con "  Ana Ficticia  " se guarda "Ana Ficticia" (RN2)."""
    r = svc.reservar("MIC-01", "  Ana Ficticia  ", VALIDO_I, VALIDO_F)
    assert r.solicitante == "Ana Ficticia"
    assert svc.obtener(r.id).solicitante == "Ana Ficticia"


def test_ca_07_solicitante_largo_maximo(svc):
    """CA-07 / S7: hasta 100 caracteres tras strip() se acepta; 101 se rechaza."""
    ok = svc.reservar("MIC-01", "  " + "A" * 100 + "  ", VALIDO_I, VALIDO_F)
    assert len(ok.solicitante) == 100
    with pytest.raises(ErrorValidacion):
        svc.reservar("MIC-02", "A" * 101, VALIDO_I, VALIDO_F)


# ---------------- CA-08 (RN3, S2) ----------------

FECHAS_INVALIDAS = [
    "2026-02-30 10:00",
    "2026-12-01 25:00",
    "01/12/2026 10:00",
    "abc",
    "10:00",
    "2026-12-01",
    "2026-12-01 10:00:00",
    "",
]


@pytest.mark.parametrize("fecha", FECHAS_INVALIDAS)
def test_ca_08_inicio_mal_formado(svc, fecha):
    """CA-08: inicio 2026-02-30 10:00, 2026-12-01 25:00, 01/12/2026 10:00 o abc
    se rechaza por fecha inválida (RN3; variantes extra por RN3/S2)."""
    with pytest.raises(ErrorValidacion):
        svc.reservar("MIC-01", "Ana Ficticia", fecha, "2026-12-01 11:00")
    assert svc.listar() == []


@pytest.mark.parametrize("fecha", FECHAS_INVALIDAS)
def test_ca_08_fin_mal_formado(svc, fecha):
    """CA-08: las mismas fechas inválidas en `fin` se rechazan (RN3)."""
    with pytest.raises(ErrorValidacion):
        svc.reservar("MIC-01", "Ana Ficticia", "2026-12-01 10:00", fecha)
    assert svc.listar() == []


# ---------------- CA-09 (RN4) ----------------

@pytest.mark.parametrize(
    "inicio, fin",
    [("2026-12-01 10:00", "2026-12-01 10:00"), ("2026-12-01 11:00", "2026-12-01 10:00")],
    ids=["inicio-igual-fin", "inicio-mayor-fin"],
)
def test_ca_09_inicio_no_anterior_a_fin(svc, inicio, fin):
    """CA-09: inicio == fin o inicio > fin se rechaza (RN4)."""
    with pytest.raises(ErrorValidacion):
        svc.reservar("MIC-01", "Ana Ficticia", inicio, fin)
    assert svc.listar() == []


def test_ca_09_duracion_minima_un_minuto(svc):
    """CA-09 / S4: la duración mínima de 1 minuto se acepta."""
    r = svc.reservar("MIC-01", "Ana Ficticia", "2026-12-01 10:00", "2026-12-01 10:01")
    assert r.estado == "activa"


# ---------------- CA-10 (S3, S4) ----------------

@pytest.mark.parametrize(
    "inicio, fin",
    [
        ("2026-11-29 10:00", "2026-11-29 11:00"),  # inicio en el pasado
        ("2026-11-30 07:59", "2026-11-30 09:00"),  # un minuto antes de ahora
        ("2026-12-01 08:00", "2026-12-01 20:01"),  # 12 h 01 min
    ],
    ids=["pasado", "un-minuto-antes", "12h01"],
)
def test_ca_10_pasado_o_duracion_excedida(svc, inicio, fin):
    """CA-10: ahora=2026-11-30 08:00; inicio 2026-11-29 10:00 o duración de
    12 h 01 min se rechaza (S3, S4)."""
    with pytest.raises(ErrorValidacion):
        svc.reservar("MIC-01", "Ana Ficticia", inicio, fin)
    assert svc.listar() == []


def test_ca_10_duracion_exacta_12h_se_acepta(svc):
    """CA-10: una duración de exactamente 12 h se acepta (S4)."""
    r = svc.reservar("MIC-01", "Ana Ficticia", "2026-12-01 08:00", "2026-12-01 20:00")
    assert r.estado == "activa"


def test_ca_10_inicio_igual_a_ahora_se_acepta(svc):
    """CA-10 / S3: se rechaza solo si inicio es *anterior* a ahora; inicio == ahora se acepta."""
    r = svc.reservar("MIC-01", "Ana Ficticia", "2026-11-30 08:00", "2026-11-30 09:00")
    assert r.estado == "activa"


def test_ca_10_sin_limite_de_anticipacion(svc):
    """CA-10 / S5: no hay límite máximo de anticipación."""
    r = svc.reservar("MIC-01", "Ana Ficticia", "2030-01-15 10:00", "2030-01-15 11:00")
    assert r.estado == "activa"
