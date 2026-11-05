# Interfaz pública (contrato para pruebas)

Este documento es el contrato que usa el subagente `redactor-pruebas`. Si la implementación cambia algo de lo que figura acá, este documento se actualiza en el mismo commit.

## API Python: `reservas.servicio`

```python
from datetime import datetime
from reservas.servicio import ServicioReservas
from reservas.errores import (ReservaError, ErrorValidacion, UnidadDesconocida,
                              Superposicion, ReservaNoEncontrada, ReservaYaCancelada)

svc = ServicioReservas(db_path, ahora=lambda: datetime(2026, 11, 30, 8, 0))
# inventario_path es opcional; por defecto usa data/inventario.json

svc.inventario()                      -> list[Unidad]        # Unidad(id, equipo)
svc.disponibilidad(unidad, inicio, fin) -> Disponibilidad    # .disponible: bool, .conflictos: list[Reserva]
svc.reservar(unidad, solicitante, inicio, fin) -> Reserva
svc.cancelar(reserva_id)              -> Reserva
svc.obtener(reserva_id)               -> Reserva             # lanza ReservaNoEncontrada
svc.listar(unidad=None, estado=None)  -> list[Reserva]       # orden: inicio, id
```

- `inicio` y `fin` son **strings** con formato `YYYY-MM-DD HH:MM`.
- Campos de `Reserva`:
  - `id: str` (`"R-0001"`)
  - `unidad: str`
  - `solicitante: str`
  - `inicio: datetime`
  - `fin: datetime`
  - `estado: str` (`"activa"` o `"cancelada"`)
  - `creada_en: datetime`
  - `cancelada_en: datetime | None`
- Jerarquía de errores:
  - `ReservaError` es la base.
  - `ErrorValidacion` y `UnidadDesconocida` heredan de `ReservaError`. `UnidadDesconocida` además es subclase de `ErrorValidacion`.
  - `Superposicion` hereda de `ReservaError` y expone `.conflictos`.
  - `ReservaNoEncontrada` y `ReservaYaCancelada` heredan de `ReservaError`.
  - `ErrorAlmacenamiento` hereda de `ReservaError`: inventario o base de datos ausente, ilegible o corrupta.

## CLI: `python -m reservas`

| Comando | Ejemplo |
|---|---|
| `inventario` | `python -m reservas inventario` |
| `disponibilidad UNIDAD INICIO FIN` | `python -m reservas disponibilidad MIC-01 "2026-12-01 10:00" "2026-12-01 11:00"` |
| `reservar UNIDAD SOLICITANTE INICIO FIN` | `python -m reservas reservar MIC-01 "Ana Ficticia" "2026-12-01 10:00" "2026-12-01 11:00"` |
| `cancelar ID` | `python -m reservas cancelar R-0001` |
| `listar [--unidad U] [--estado activa\|cancelada]` | `python -m reservas listar --estado activa` |
| `reiniciar-datos [--confirmar]` | `python -m reservas reiniciar-datos --confirmar` |

**Opciones globales y variables de entorno**
- `--db RUTA`, o la variable de entorno `RESERVAS_DB`. Valor por defecto: `data/reservas.db`.
- `RESERVAS_AHORA="YYYY-MM-DD HH:MM"` fija el "ahora". Sin ella, el "ahora" es la hora actual en UTC−3.
- `RESERVAS_INVENTARIO=RUTA` cambia el inventario. Valor por defecto: `data/inventario.json`.

**Salida y códigos de salida**
- `0`: la operación salió bien. El primer token de la línea de resultado es:
  - `CREADA R-0001 ...` al reservar.
  - `CANCELADA R-0001 ...` al cancelar.
  - `DISPONIBLE ...` o `NO DISPONIBLE ...` al consultar disponibilidad. Las dos respuestas son una consulta exitosa y salen con código `0`.
- `1`: error de negocio o de validación. El mensaje se escribe en stderr y empieza con `ERROR:`.
- `2`: uso incorrecto de argumentos (lo maneja argparse).
- `reiniciar-datos` sin `--confirmar` no borra nada, escribe `ERROR:` en stderr y sale con código `1`.
- `listar`: escribe una línea por reserva con el formato `R-0001  MIC-01  2026-12-01 10:00  2026-12-01 11:00  activa  Ana Ficticia` (campos separados por exactamente dos espacios). Si no hay reservas, escribe `(sin reservas)`. `--unidad` desconocida produce `ERROR:` y código `1`.
- `inventario`: una línea por unidad, `MIC-01  Microscopio digital`. No abre ni crea la BD.
- `disponibilidad` con conflictos: después de `NO DISPONIBLE ...`, una línea `  conflicto: <línea de listar>` por cada reserva activa en conflicto.
- `cancelar`: `CANCELADA <línea de listar>  (cancelada_en YYYY-MM-DD HH:MM:SS)`.
- `reiniciar-datos --confirmar`: `REINICIADO: se borraron N reservas de <ruta>`. Sin `--confirmar` no abre ni crea la BD.
