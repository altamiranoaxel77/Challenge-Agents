# Auditoría de las pruebas contra la consigna

**Fecha:** 2026-11-05.
**Ejecutada por:** el agente principal, a pedido del autor ("vuelve a revisar todos los test y verifica que cumpla con las consignas").
**Qué incluye:**
1. Lectura completa de los 11 archivos de `tests/`.
2. Una prueba de mutantes que inyecta defectos en el código.
3. Una corrida completa de la suite.

## 1. Verificaciones exigidas por la consigna y pruebas que las cubren
La consigna, página 2, pide: *"pruebas automáticas de creación válida, rechazo de superposición, límites consecutivos, unidades distintas simultáneas, entradas inválidas y cancelación que conserva el registro y libera el horario. Comprobar persistencia [...] tras detener y reiniciar"*.

| # | Verificación exigida | Pruebas principales | Qué afirman (no solo "no falla") |
|---|---|---|---|
| 1 | Creación válida | `test_crear.py::test_ca_01_crear_reserva_valida`, `test_ca_01_ids_secuenciales`, `test_cli.py::test_ca_01_cli_reservar_salida_creada` | Comparan el ID `R-0001`, el estado `activa`, la unidad, el solicitante, el inicio y el fin exactos, `cancelada_en is None` y la salida `CREADA` con exit 0 |
| 2 | Rechazo de superposición | `test_superposicion.py`: CA-02 y 5 variantes de CA-03 (contiene, contenida, idéntica, solapamiento de 1 min al inicio y al final). También `test_ca_02_cli_superposicion_codigo_1` | Esperan `Superposicion` con el conflicto `R-0001`, que **no se cree nada** (el listado no cambia y el ID siguiente sigue siendo `R-0002`) y exit 1 con `ERROR:` |
| 3 | Límites consecutivos | `test_limites.py`: 11:00–12:00 y 09:00–10:00 contra 10:00–11:00, cruce de medianoche y año bisiesto. También `test_dominio.py::test_dominio_se_superpone_semiabierto` y `test_ca_13_consecutivo_disponible` | Las dos reservas quedan activas, la disponibilidad responde `True` y `se_superpone` devuelve `False` en el borde, en ambos sentidos |
| 4 | Unidades distintas simultáneas | `test_unidades.py::test_ca_05_unidades_distintas_simultaneas`, `test_ca_13_otra_unidad_disponible`, `test_persistencia.py` (MIC-01 y MIC-02 a la misma hora) | MIC-02 de 10:00 a 11:00 se crea como `R-0002` activa, con MIC-01 ocupado |
| 5 | Entradas inválidas | `test_validaciones.py` (31 pruebas), `test_unidades.py::test_ca_06_*`, `test_cli.py::test_ca_06_a_13_cli_errores_codigo_1` (12 casos), `test_revision.py` (grupo B) | Cubren unidad desconocida o en minúsculas, solicitante vacío, solo espacios, más de 100 caracteres o con caracteres de control, 8 fechas mal formadas en inicio y en fin, inicio igual o posterior al fin, fecha pasada y duración de más de 12 h. En cada caso esperan el error tipado y que **no se cree nada** |
| 6 | Cancelación que conserva el registro y libera el horario | `test_cancelacion.py`: CA-11 y CA-12, más `test_dominio.py::test_dominio_conflictos_ignora_canceladas` | Después de cancelar, ID, unidad, solicitante, inicio, fin y `creada_en` siguen iguales, el estado es `cancelada` y `cancelada_en` queda cargado. La reserva sigue apareciendo con `listar --estado cancelada`, el intervalo vuelve a estar disponible y se puede reservar como `R-0002`. Cancelar dos veces o un ID inexistente da error y no cambia nada |
| 7 | Persistencia tras detener y reiniciar | `test_persistencia.py` (6 pruebas, CA-14), `test_ca_16_*` | Cada comando del CLI corre en un **proceso nuevo** (`subprocess`) sobre la misma BD. El listado posterior compara campo por campo las reservas activas y canceladas. La cancelada sigue liberando su horario y la activa sigue bloqueando. Además, dos instancias distintas del servicio ven los mismos datos |

**Conclusión de la matriz:** las 7 verificaciones exigidas tienen pruebas automáticas con aserciones sobre el resultado concreto. La persistencia, además, tiene un procedimiento manual reproducible en [verificacion.md](verificacion.md).

## 2. Huecos encontrados en la lectura y qué se hizo
| Hueco | Corrección |
|---|---|
| `test_ca_13_disponible_equivale_a_reserva_aceptada` usaba `pytest.raises(Exception)`, demasiado amplio: habría pasado con cualquier error | Ahora espera `Superposicion` |
| Los límites consecutivos **cruzando la medianoche** y el **año bisiesto** solo se habían revisado leyendo el código, no ejecutándolo | Se agregaron `test_ca_04_consecutivos_cruzando_medianoche` y `test_ca_04_fecha_bisiesta_valida` |
| El mutante M2 sobrevivió en la primera corrida (ver §3) | Se agregó `tests/test_dominio.py`, con 8 pruebas unitarias de `se_superpone` y `conflictos` |

## 3. Prueba de mutantes
El script es [`tools/auditoria/mutantes.py`](../tools/auditoria/mutantes.py). Para cada defecto copia el proyecto a un directorio temporal, inyecta **un** defecto y corre `pytest -x`. Usa `PYTHONPATH` apuntando a la copia, y verifica que los subprocesos del CLI también ejecuten el código mutado. El `src/` real no se modifica.

**Primera corrida: 8 de 9 detectados.** El M2 sobrevivió con `140 passed`.
- **Análisis:** el servicio ya pide a SQLite solo las reservas activas, así que el filtro `r.bloquea` de `dominio.conflictos` es redundante a nivel de sistema. Eso hace que el mutante sea equivalente desde la API y desde el CLI.
- **Por qué igual es un hueco:** la regla RN7 dentro de la función de dominio no tenía ninguna prueba propia.
- **Qué se hizo:** se agregaron pruebas unitarias del dominio.

**Segunda corrida** (`.venv/Scripts/python tools/auditoria/mutantes.py`):

| Mutante | Defecto inyectado | Resultado | Primera prueba que lo detectó |
|---|---|---|---|
| M1 | `se_superpone` con `<=` (rompe los límites consecutivos) | DETECTADO | `test_cli.py::test_ca_13_cli_disponibilidad_ambas_respuestas_codigo_0` |
| M2 | `conflictos` ignora el estado (una cancelada sigue bloqueando) | DETECTADO | `test_dominio.py::test_dominio_conflictos_ignora_canceladas` |
| M3 | Acepta `inicio == fin` | DETECTADO | `test_disponibilidad.py::test_ca_13_entrada_invalida_mismo_error_que_creacion[...10:00-...10:00]` |
| M4 | Acepta un solicitante vacío o solo con espacios | DETECTADO | `test_cli.py::test_ca_06_a_13_cli_errores_codigo_1[args2]` |
| M5 | `reservar` no rechaza superposiciones | DETECTADO | `test_cli.py::test_ca_02_cli_superposicion_codigo_1` |
| M6 | Cancelar borra la reserva con `DELETE` | DETECTADO | `test_cancelacion.py::test_ca_11_cancelar_conserva_datos_y_registra_cancelada_en` |
| M7 | No valida que la unidad exista | DETECTADO | `test_cli.py::test_ca_06_a_13_cli_errores_codigo_1[args0]` |
| M8 | Las escrituras no se confirman (`ROLLBACK` en lugar de `COMMIT`) | DETECTADO | `test_cancelacion.py::test_ca_11_cancelar_conserva_datos_y_registra_cancelada_en` |
| M9 | La disponibilidad ignora las reservas activas | DETECTADO | `test_cli.py::test_ca_13_cli_disponibilidad_ambas_respuestas_codigo_0` |

```
RESULTADO: 9/9 mutantes detectados por las pruebas
```

## 4. Corrida completa después de la auditoría
```
$ .venv/Scripts/python -m pytest -q
148 passed in 131.18s (0:02:11)
```
Hay 148 pruebas en 11 archivos:

| Archivo | Pruebas |
|---|---|
| `test_validaciones` | 31 |
| `test_cli` | 29 |
| `test_revision` | 23 |
| `test_disponibilidad` | 20 |
| `test_cancelacion` | 8 |
| `test_dominio` | 8 |
| `test_superposicion` | 8 |
| `test_unidades` | 7 |
| `test_persistencia` | 6 |
| `test_crear` | 4 |
| `test_limites` | 4 |

El entorno fue Python 3.14.2 y pytest 9.2.0 sobre Windows 10.

## 5. Qué no cubren las pruebas
- **Varios procesos escribiendo a la vez sobre la misma BD.** `BEGIN IMMEDIATE` serializa las escrituras, pero esa situación no se ejercita. La consigna deja fuera del alcance la concurrencia distribuida.
- **Fallas físicas:** disco lleno o un proceso cortado a mitad de un `COMMIT`.
- **Otros sistemas operativos.** Todo se ejecutó solo en Windows 10.
- **El reloj real en UTC−3 sin `RESERVAS_AHORA`.** Solo hay una prueba que compara contra UTC con 5 s de tolerancia (`test_rev_10`).
