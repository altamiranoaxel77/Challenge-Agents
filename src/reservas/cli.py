"""Interfaz de consola (ver docs/interfaz.md).

Códigos de salida: 0 éxito · 1 error de negocio/validación · 2 uso incorrecto (argparse).
"""
from __future__ import annotations

import argparse
import os
import sys

from reservas import dominio
from reservas.errores import ReservaError
from reservas.inventario import cargar_inventario
from reservas.servicio import DB_POR_DEFECTO, ServicioReservas


def _linea(r: dominio.Reserva) -> str:
    return (
        f"{r.id}  {r.unidad}  {dominio.formatear_fecha(r.inicio)}  "
        f"{dominio.formatear_fecha(r.fin)}  {r.estado}  {r.solicitante}"
    )


def _crear_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="reservas", description="Reservas de unidades de laboratorio")
    p.add_argument("--db", help=f"ruta de la base SQLite (por defecto RESERVAS_DB o {DB_POR_DEFECTO})")
    sub = p.add_subparsers(dest="comando", required=True)

    sub.add_parser("inventario", help="lista las unidades precargadas")

    d = sub.add_parser("disponibilidad", help="consulta si una unidad está libre en un intervalo")
    d.add_argument("unidad")
    d.add_argument("inicio", help="YYYY-MM-DD HH:MM")
    d.add_argument("fin", help="YYYY-MM-DD HH:MM")

    r = sub.add_parser("reservar", help="crea una reserva")
    r.add_argument("unidad")
    r.add_argument("solicitante")
    r.add_argument("inicio", help="YYYY-MM-DD HH:MM")
    r.add_argument("fin", help="YYYY-MM-DD HH:MM")

    c = sub.add_parser("cancelar", help="cancela una reserva conservando su registro")
    c.add_argument("id")

    l = sub.add_parser("listar", help="lista reservas (activas y canceladas)")
    l.add_argument("--unidad")
    l.add_argument("--estado", choices=dominio.ESTADOS)

    z = sub.add_parser("reiniciar-datos", help="BORRA todas las reservas (requiere --confirmar)")
    z.add_argument("--confirmar", action="store_true")
    return p


def _reloj_desde_entorno():
    """S8: RESERVAS_AHORA fija el 'ahora' para pruebas reproducibles."""
    valor = os.environ.get("RESERVAS_AHORA")
    if not valor:
        return None
    fijo = dominio.parsear_fecha(valor, "RESERVAS_AHORA")
    return lambda: fijo


def ejecutar(args: argparse.Namespace) -> int:
    db = args.db or os.environ.get("RESERVAS_DB") or DB_POR_DEFECTO
    fmt = dominio.formatear_fecha

    # Episodio 3 (#6): comandos que no deben tocar la BD se resuelven antes de abrirla.
    if args.comando == "inventario":
        for u in cargar_inventario().values():
            print(f"{u.id}  {u.equipo}")
        return 0
    if args.comando == "reiniciar-datos" and not args.confirmar:
        print(
            "ERROR: reiniciar-datos BORRA todas las reservas. "
            "Repita con --confirmar para continuar. No se borró nada.",
            file=sys.stderr,
        )
        return 1

    svc = ServicioReservas(db, ahora=_reloj_desde_entorno())
    if args.comando == "disponibilidad":
        disp = svc.disponibilidad(args.unidad, args.inicio, args.fin)
        rango = f"{disp.unidad} {fmt(disp.inicio)} -> {fmt(disp.fin)}"
        if disp.disponible:
            print(f"DISPONIBLE {rango}")
        else:
            print(f"NO DISPONIBLE {rango}")
            for r in disp.conflictos:
                print(f"  conflicto: {_linea(r)}")
    elif args.comando == "reservar":
        r = svc.reservar(args.unidad, args.solicitante, args.inicio, args.fin)
        print(f"CREADA {_linea(r)}")
    elif args.comando == "cancelar":
        r = svc.cancelar(args.id)
        print(f"CANCELADA {_linea(r)}  (cancelada_en {r.cancelada_en:%Y-%m-%d %H:%M:%S})")
    elif args.comando == "listar":
        reservas = svc.listar(args.unidad, args.estado)
        for r in reservas:
            print(_linea(r))
        if not reservas:
            print("(sin reservas)")
    elif args.comando == "reiniciar-datos":
        borradas = svc.reiniciar_datos()
        print(f"REINICIADO: se borraron {borradas} reservas de {db}")
    return 0


def main(argv: list[str] | None = None) -> int:
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(errors="replace")
        except AttributeError:
            pass
    args = _crear_parser().parse_args(argv)
    try:
        return ejecutar(args)
    except ReservaError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
