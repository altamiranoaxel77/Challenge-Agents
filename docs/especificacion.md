# Especificación — Sistema de reservas de laboratorio

**Versión:** v1 · **Estado:** borrador para revisión humana · La evolución de este archivo se recupera con
`git log -p docs/especificacion.md`.

## 1. Problema
La coordinación de un laboratorio registra pedidos en mensajes y en una planilla. Esto produce dos fallas:
- **Doble confirmación:** la misma unidad física se confirma para horarios superpuestos.
- **Cancelaciones fantasma:** una reserva cancelada sigue bloqueando el horario.

Se necesita una herramienta local para consultar disponibilidad, reservar y cancelar sin perder el historial.

## 2. Alcance
**Dentro del alcance**
- Inventario precargado de solo lectura.
- Consulta de disponibilidad por unidad e intervalo.
- Creación y cancelación de reservas.
- Listado e historial.
- Persistencia local.
- Interfaz de consola (CLI).

**Fuera del alcance**
- Administración del inventario.
- Autenticación y roles.
- Notificaciones, pagos e integraciones externas.
- Interfaz gráfica y despliegue.
- Concurrencia distribuida.
- Edición o reprogramación de reservas: para cambiar una reserva se cancela y se crea otra.
- Reservas de varias unidades a la vez.

## 3. Inventario inicial
Archivo `data/inventario.json`. Cada ID corresponde a una unidad física distinta.

| ID | Equipo |
|---|---|
| MIC-01 | Microscopio digital |
| MIC-02 | Microscopio digital |
| OSC-01 | Osciloscopio |
| MUL-01 | Multímetro |
| FUE-01 | Fuente de alimentación |

## 4. Requisitos funcionales
| ID | Requisito |
|---|---|
| R1 | El sistema carga el inventario precargado y lo muestra con el comando `inventario`. |
| R2 | El sistema informa si una unidad está disponible en un intervalo y, si no lo está, con qué reservas activas entra en conflicto. |
| R3 | El sistema crea una reserva con unidad, solicitante, inicio y fin. Le asigna un identificador único `R-NNNN` y el estado `activa`. |
| R4 | El sistema cancela una reserva por su ID. Conserva el ID y todos los datos, cambia el estado a `cancelada`, registra `cancelada_en` y libera el intervalo. |
| R5 | Las reservas y sus estados persisten en disco y se recuperan al reiniciar la aplicación. |
| R6 | El sistema lista las reservas, activas y canceladas, con filtros opcionales por unidad y por estado. |

## 5. Reglas de negocio
| ID | Regla |
|---|---|
| RN1 | La unidad debe existir en el inventario. La comparación distingue mayúsculas: `mic-01` se rechaza. |
| RN2 | El solicitante es obligatorio y se le quitan los espacios de los extremos. Si queda vacío, se rechaza. |
| RN3 | `inicio` y `fin` deben ser fechas y horas válidas con formato `YYYY-MM-DD HH:MM`. Se rechazan casos como `2026-02-30 10:00`, `25:00` o `10:00` sin fecha. |
| RN4 | `inicio` debe ser **estrictamente** anterior a `fin`. Si `inicio == fin`, se rechaza. |
| RN5 | Los intervalos son **semiabiertos** `[inicio, fin)`. Dos reservas A y B se superponen si y solo si `A.inicio < B.fin` y `B.inicio < A.fin`. |
| RN6 | Se rechaza una reserva que se superpone con otra reserva **activa** de la **misma** unidad. |
| RN7 | Una reserva **cancelada** nunca bloquea. |
| RN8 | Se permiten los límites consecutivos: una reserva puede empezar a la hora exacta en que termina otra. |
| RN9 | Se permiten reservas simultáneas de unidades distintas. |
| RN10 | La consulta de disponibilidad aplica **las mismas reglas** que la creación: RN1, RN3–RN7 y los supuestos S3 y S4. Si informa "disponible", la reserva equivalente se acepta. |
| RN11 | Solo se puede cancelar una reserva existente que esté en estado `activa`. Cancelar una inexistente o una ya cancelada produce un error y no cambia nada. |

## 6. Supuestos
Resuelven aspectos que la consigna no especifica.

| ID | Supuesto | Motivo |
|---|---|---|
| S1 | **Zona horaria:** todas las fechas son hora local del laboratorio (America/Argentina/Buenos_Aires, UTC−3, sin horario de verano). Se guardan sin offset. | Es un único laboratorio y una única sede. Evita conversiones innecesarias. |
| S2 | **Formato:** `YYYY-MM-DD HH:MM`, con el minuto como resolución. No se aceptan segundos ni otros formatos. | No es ambiguo y se ordena bien como texto. |
| S3 | **Fechas pasadas:** se rechaza crear una reserva, o consultar disponibilidad, cuando `inicio` es anterior al momento actual. Una reserva que ya pasó se puede listar y cancelar. | No tiene sentido reservar hacia atrás. Cancelar una reserva vencida no perjudica a nadie. |
| S4 | **Duración máxima:** 12 horas. La mínima es de 1 minuto, porque `inicio < fin`. | Evita bloqueos accidentales de días enteros. |
| S5 | **Anticipación:** no hay límite máximo. | La consigna no lo pide. |
| S6 | **IDs:** `R-0001`, `R-0002`, …, secuenciales y nunca reutilizados, porque las reservas no se borran. | Son legibles y estables. |
| S7 | **Solicitante:** texto libre de hasta 100 caracteres después del `strip()`. Siempre se usan nombres ficticios. | Evita datos reales. El límite sirve para validar algo razonable. |
| S8 | **El "ahora"** sale del reloj del sistema. Puede fijarse con la variable de entorno `RESERVAS_AHORA` (`YYYY-MM-DD HH:MM`) para pruebas reproducibles. | Las pruebas deben ser deterministas. |
| S9 | **Reinicio de datos:** `reiniciar-datos --confirmar` **borra todas las reservas**. Sin `--confirmar` no hace nada. | Es la única operación destructiva y debe ser explícita. |

## 7. Criterios de aceptación
Salvo que se indique otra cosa, en todos los casos el "ahora" es `2026-11-30 08:00` y la base de datos arranca vacía.

| ID | Dado | Cuando | Entonces | Reglas |
|---|---|---|---|---|
| CA-01 | BD vacía | se reserva MIC-01, "Ana Ficticia", 2026-12-01 10:00–11:00 | se crea `R-0001` con estado `activa` y los datos ingresados | R3 |
| CA-02 | MIC-01 reservado 10:00–11:00 | se reserva MIC-01 10:30–11:30 | se rechaza por superposición y no se crea nada | RN6 |
| CA-03 | MIC-01 reservado 10:00–11:00 | se reserva MIC-01 09:00–12:00 (contiene la reserva) o 10:15–10:45 (está contenida) | se rechaza en ambos casos | RN5, RN6 |
| CA-04 | MIC-01 reservado 10:00–11:00 | se reserva MIC-01 11:00–12:00 y MIC-01 09:00–10:00 | se aceptan las dos | RN8 |
| CA-05 | MIC-01 reservado 10:00–11:00 | se reserva MIC-02 10:00–11:00 | se acepta | RN9 |
| CA-06 | — | se reserva la unidad `XYZ-99` o `mic-01` | se rechaza por unidad desconocida | RN1 |
| CA-07 | — | el solicitante es `""` o `"   "` | se rechaza. Con `"  Ana Ficticia  "` se guarda `"Ana Ficticia"` | RN2 |
| CA-08 | — | la fecha es `2026-02-30 10:00`, `2026-12-01 25:00`, `01/12/2026 10:00` o `abc` | se rechaza por fecha inválida | RN3 |
| CA-09 | — | el intervalo es `inicio == fin` o `inicio > fin` | se rechaza | RN4 |
| CA-10 | ahora = 2026-11-30 08:00 | se reserva con inicio 2026-11-29 10:00 o con una duración de 12 h 01 min | se rechaza en ambos casos. Una duración de exactamente 12 h se acepta | S3, S4 |
| CA-11 | `R-0001` activa en MIC-01 10:00–11:00 | se cancela `R-0001` | `R-0001` pasa a `cancelada` con sus datos intactos y `cancelada_en` registrado. MIC-01 10:00–11:00 queda disponible y puede reservarse otra vez como `R-0002` | R4, RN7 |
| CA-12 | `R-0001` cancelada | se cancela `R-0001` otra vez, o se cancela `R-9999` | se produce un error y no cambia nada | RN11 |
| CA-13 | MIC-01 reservado 10:00–11:00 | se consulta la disponibilidad de MIC-01 en 10:30–11:30, 11:00–12:00, y de MIC-02 en 10:00–11:00 | MIC-01 10:30–11:30 no está disponible e informa el conflicto `R-0001`. MIC-01 11:00–12:00 está disponible. MIC-02 10:00–11:00 está disponible. Una entrada inválida produce el mismo error que en la creación | R2, RN10 |
| CA-14 | Hay reservas activas y canceladas creadas con el CLI | el proceso termina y se ejecuta un **nuevo proceso** con `listar` sobre la misma BD | aparecen todas las reservas con su mismo ID, datos y estado. El intervalo cancelado sigue disponible | R5, R6 |
| CA-15 | Hay reservas | se ejecuta `reiniciar-datos` sin `--confirmar` | no se borra nada. Con `--confirmar`, se borran todas | S9 |

## 8. Requisitos no funcionales
- Funciona sin red y sin la cuenta de modelo del autor. Solo necesita Python ≥ 3.12 y pytest para las pruebas.
- El CLI devuelve el código de salida `0` si la operación sale bien, `1` ante un error de negocio o de validación, y `2` ante un uso incorrecto de argumentos.
- Escribir en la BD es atómico: la verificación de superposición y la inserción ocurren en la misma transacción.
