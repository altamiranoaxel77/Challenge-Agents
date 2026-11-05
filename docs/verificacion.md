# Verificación

> Evidencia **ejecutada** por el subagente `verificador` (definición en `.claude/agents/verificador.md`) el **2026-11-05 17:08** (hora local de la PC, Git Bash `date`: `Thu Nov  5 17:08:23 2026`), sobre el commit **`7f502bd`**. Nada de lo que sigue es supuesto: cada salida se copió de la ejecución real.

## Entorno y versiones

| Elemento | Valor |
|---|---|
| Sistema operativo | Windows 10 Pro 10.0.19045, Git Bash |
| Intérprete | `.venv/Scripts/python --version` → `Python 3.14.2` |
| pytest | `.venv/Scripts/python -m pytest --version` → `pytest 9.2.0` |
| Commit | `git rev-parse --short HEAD` → `7f502bd` |
| Árbol de trabajo | `git status --short` → salida vacía (árbol limpio al momento de verificar, antes de crear este archivo) |

## Pruebas automáticas

Comando (desde la raíz del repo):

```
.venv/Scripts/python -m pytest -v
```

Resumen final textual:

```
======================= 138 passed in 141.63s (0:02:21) =======================
```

Código de salida: `0`. Fallidas: ninguna.

Cantidad de tests por archivo (`pytest --collect-only -q`, 138 en total):

| Archivo | Tests |
|---|---|
| `tests/test_cancelacion.py` | 8 |
| `tests/test_cli.py` | 29 |
| `tests/test_crear.py` | 4 |
| `tests/test_disponibilidad.py` | 20 |
| `tests/test_limites.py` | 2 |
| `tests/test_persistencia.py` | 6 |
| `tests/test_revision.py` | 23 |
| `tests/test_superposicion.py` | 8 |
| `tests/test_unidades.py` | 7 |
| `tests/test_validaciones.py` | 31 |

### Mapeo a las verificaciones requeridas por la consigna

| Verificación requerida | Dónde se cubre (tests) |
|---|---|
| Creación válida | `test_crear.py` (`test_ca_01_*`), `test_cli.py::test_ca_01_cli_reservar_salida_creada` |
| Rechazo de superposición | `test_superposicion.py` (`test_ca_02_*`, `test_ca_03_*`: parcial, contenida, contenedora, idéntica, solapa inicio/fin; el rechazo no consume ID), `test_cli.py::test_ca_02_cli_superposicion_codigo_1` |
| Límites consecutivos | `test_limites.py::test_ca_04_limites_consecutivos_se_aceptan`, `test_disponibilidad.py::test_ca_13_consecutivo_disponible` |
| Unidades distintas simultáneas | `test_unidades.py::test_ca_05_unidades_distintas_simultaneas`, `test_disponibilidad.py::test_ca_13_otra_unidad_disponible` |
| Entradas inválidas | `test_unidades.py` (`test_ca_06_*`, unidad desconocida), `test_validaciones.py` (`test_ca_07`..`test_ca_10`: solicitante, formato de fecha, orden/duración, pasado), `test_revision.py` (`rev_07`, `rev_08`, `rev_13`, inventario/BD corruptos), `test_cli.py::test_ca_06_a_13_cli_errores_codigo_1`, `test_cli.py::test_ca_cli_uso_incorrecto_codigo_2` |
| Cancelación que conserva registro y libera horario | `test_cancelacion.py::test_ca_11_cancelar_conserva_datos_y_registra_cancelada_en`, `test_ca_11_cancelar_libera_el_intervalo`, `test_ca_12_*` (doble cancelación / inexistente sin cambios), `test_cli.py::test_ca_11_*`, `test_ca_12_*` |
| Persistencia | `test_persistencia.py` (`test_ca_14_*`: nuevo proceso recupera todo, cancelado sigue disponible y activa sigue bloqueando tras reinicio, filtros, dos instancias, servicio lee lo creado por CLI), `test_cli.py::test_ca_15_*`, `test_ca_16_*` (reinicio de datos) |

## Procedimiento manual de persistencia (CA-14)

Preparación (BD nueva en directorio temporal; nunca `data/reservas.db`):

```
export RESERVAS_AHORA="2026-11-30 08:00" PYTHONIOENCODING=utf-8
TMP=$(mktemp -d)        # → /tmp/tmp.kg5lSUpulK (no existía verif.db antes del paso a)
```

Cada comando se ejecutó como `.venv/Scripts/python -m reservas --db $TMP/verif.db <subcomando>`, es decir, **cada paso es un proceso Python distinto** (equivale a detener y reiniciar la aplicación). El código de salida se tomó con `echo $?`.

| Paso | Comando (subcomando) | Esperado | Observado | ✔/✘ |
|---|---|---|---|---|
| a | `reservar MIC-01 "Ana Ficticia" "2026-12-01 10:00" "2026-12-01 11:00"` | creada R-0001, exit 0 | `CREADA R-0001 ...`, exit 0 | ✔ |
| b | `reservar MIC-01 "Bruno Ficticio" "2026-12-01 10:30" "2026-12-01 11:30"` | rechazo por superposición, exit 1 | `ERROR: ... (conflicto con R-0001)` en stderr, exit 1 | ✔ |
| c | `reservar MIC-01 "Carla Ficticia" "2026-12-01 11:00" "2026-12-01 12:00"` | creada (consecutiva), exit 0 | `CREADA R-0002 ...`, exit 0 | ✔ |
| d | `reservar MIC-02 "Dario Ficticio" "2026-12-01 10:00" "2026-12-01 11:00"` | creada (otra unidad, mismo horario), exit 0 | `CREADA R-0003 ...`, exit 0 | ✔ |
| e | `cancelar R-0001` | estado cancelada, exit 0 | `CANCELADA R-0001 ... cancelada ... (cancelada_en 2026-11-30 08:00:00)`, exit 0 | ✔ |
| f | `listar` (nuevo proceso) | 3 reservas: R-0001 cancelada, R-0002 y R-0003 activas; el intento rechazado no se persiste | exactamente esas 3 líneas, exit 0 | ✔ |
| g | `disponibilidad MIC-01 "2026-12-01 10:00" "2026-12-01 11:00"` (nuevo proceso) | disponible, exit 0 | `DISPONIBLE ...`, exit 0 | ✔ |
| h1 | `listar --estado cancelada` (nuevo proceso) | sólo R-0001 | sólo R-0001, exit 0 | ✔ |
| h2 | `listar --estado activa` (nuevo proceso) | R-0002 y R-0003 | R-0003 y R-0002 (orden por inicio), exit 0 | ✔ |
| i1 | `reiniciar-datos` (sin `--confirmar`) | `ERROR:` en stderr, exit 1, no borra | `ERROR: ... No se borró nada.`, exit 1 | ✔ |
| i2 | `listar` (nuevo proceso) | siguen las 3 reservas | las 3 reservas, exit 0 | ✔ |

### Salidas textuales

```
$ python -m reservas --db $TMP/verif.db reservar MIC-01 "Ana Ficticia" "2026-12-01 10:00" "2026-12-01 11:00"
CREADA R-0001  MIC-01  2026-12-01 10:00  2026-12-01 11:00  activa  Ana Ficticia
[exit=0]

$ python -m reservas --db $TMP/verif.db reservar MIC-01 "Bruno Ficticio" "2026-12-01 10:30" "2026-12-01 11:30"
ERROR: MIC-01 ya está reservada en ese intervalo (conflicto con R-0001)
[exit=1]

$ python -m reservas --db $TMP/verif.db reservar MIC-01 "Carla Ficticia" "2026-12-01 11:00" "2026-12-01 12:00"
CREADA R-0002  MIC-01  2026-12-01 11:00  2026-12-01 12:00  activa  Carla Ficticia
[exit=0]

$ python -m reservas --db $TMP/verif.db reservar MIC-02 "Dario Ficticio" "2026-12-01 10:00" "2026-12-01 11:00"
CREADA R-0003  MIC-02  2026-12-01 10:00  2026-12-01 11:00  activa  Dario Ficticio
[exit=0]

$ python -m reservas --db $TMP/verif.db cancelar R-0001
CANCELADA R-0001  MIC-01  2026-12-01 10:00  2026-12-01 11:00  cancelada  Ana Ficticia  (cancelada_en 2026-11-30 08:00:00)
[exit=0]

$ python -m reservas --db $TMP/verif.db listar
R-0001  MIC-01  2026-12-01 10:00  2026-12-01 11:00  cancelada  Ana Ficticia
R-0003  MIC-02  2026-12-01 10:00  2026-12-01 11:00  activa  Dario Ficticio
R-0002  MIC-01  2026-12-01 11:00  2026-12-01 12:00  activa  Carla Ficticia
[exit=0]

$ python -m reservas --db $TMP/verif.db disponibilidad MIC-01 "2026-12-01 10:00" "2026-12-01 11:00"
DISPONIBLE MIC-01 2026-12-01 10:00 -> 2026-12-01 11:00
[exit=0]

$ python -m reservas --db $TMP/verif.db listar --estado cancelada
R-0001  MIC-01  2026-12-01 10:00  2026-12-01 11:00  cancelada  Ana Ficticia
[exit=0]

$ python -m reservas --db $TMP/verif.db listar --estado activa
R-0003  MIC-02  2026-12-01 10:00  2026-12-01 11:00  activa  Dario Ficticio
R-0002  MIC-01  2026-12-01 11:00  2026-12-01 12:00  activa  Carla Ficticia
[exit=0]

$ python -m reservas --db $TMP/verif.db reiniciar-datos
ERROR: reiniciar-datos BORRA todas las reservas. Repita con --confirmar para continuar. No se borró nada.
[exit=1]

$ python -m reservas --db $TMP/verif.db listar
R-0001  MIC-01  2026-12-01 10:00  2026-12-01 11:00  cancelada  Ana Ficticia
R-0003  MIC-02  2026-12-01 10:00  2026-12-01 11:00  activa  Dario Ficticio
R-0002  MIC-01  2026-12-01 11:00  2026-12-01 12:00  activa  Carla Ficticia
[exit=0]
```

Al final, el directorio temporal contenía sólo `verif.db` (16384 bytes). Los IDs son R-0001..R-0003 sin huecos: el intento rechazado (paso b) no consumió ID ni quedó registrado.

## Cómo reproducir

Desde la raíz del repo, en Git Bash:

```bash
.venv/Scripts/python --version
.venv/Scripts/python -m pytest --version
git rev-parse --short HEAD
.venv/Scripts/python -m pytest -v          # ~2-3 min

export RESERVAS_AHORA="2026-11-30 08:00" PYTHONIOENCODING=utf-8
TMP=$(mktemp -d); P=.venv/Scripts/python
$P -m reservas --db "$TMP/verif.db" reservar MIC-01 "Ana Ficticia"   "2026-12-01 10:00" "2026-12-01 11:00"; echo $?
$P -m reservas --db "$TMP/verif.db" reservar MIC-01 "Bruno Ficticio" "2026-12-01 10:30" "2026-12-01 11:30"; echo $?
$P -m reservas --db "$TMP/verif.db" reservar MIC-01 "Carla Ficticia" "2026-12-01 11:00" "2026-12-01 12:00"; echo $?
$P -m reservas --db "$TMP/verif.db" reservar MIC-02 "Dario Ficticio" "2026-12-01 10:00" "2026-12-01 11:00"; echo $?
$P -m reservas --db "$TMP/verif.db" cancelar R-0001; echo $?
$P -m reservas --db "$TMP/verif.db" listar; echo $?
$P -m reservas --db "$TMP/verif.db" disponibilidad MIC-01 "2026-12-01 10:00" "2026-12-01 11:00"; echo $?
$P -m reservas --db "$TMP/verif.db" listar --estado cancelada; echo $?
$P -m reservas --db "$TMP/verif.db" listar --estado activa; echo $?
$P -m reservas --db "$TMP/verif.db" reiniciar-datos; echo $?
$P -m reservas --db "$TMP/verif.db" listar; echo $?
```

## Qué NO se verificó

- **Otros sistemas operativos**: sólo Windows 10 con Git Bash. No se ejecutó en Linux ni macOS, ni desde `cmd.exe`/PowerShell (codificación de consola sin `PYTHONIOENCODING=utf-8` no probada en este procedimiento).
- **Otras versiones de Python**: sólo 3.14.2.
- **Concurrencia real**: no se lanzaron procesos simultáneos compitiendo por la misma BD (p. ej. dos `reservar` superpuestos en paralelo). Los procesos del procedimiento fueron secuenciales; `test_ca_14_dos_instancias_del_servicio` usa dos instancias en un mismo proceso, no carreras reales.
- **Fallos físicos**: corte de energía, disco lleno, permisos de solo lectura o kill del proceso a mitad de una escritura.
- **"Ahora" real**: el procedimiento manual fijó `RESERVAS_AHORA`; el cálculo de UTC−3 sin esa variable sólo lo cubre `test_rev_10_*`, no se probó a mano.
- **`reiniciar-datos --confirmar`** no se ejecutó en el procedimiento manual (sólo lo cubren `test_ca_15_*`/`test_ca_16_*`).
- **Volumen**: no se probaron BD con muchas reservas ni rendimiento.
- **BD por defecto `data/reservas.db`**: deliberadamente no se usó.
