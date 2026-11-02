# Implementación — Hallazgos de la revisión

Parte de [[Implementación 2026-11-01 — Índice]].

## Hallazgos sobre el modelo (importantes para el artículo)
1. **Un modelo solo con pH es igual o mejor.** Regresión logística solo-pH, GroupKFold 5, umbral 0,5: Recall, precisión y AUC = 1,00. El Modelo B (9 variables): Recall 0,964, AUC 0,981. Las variables adicionales no tienen justificación empírica con esta muestra.
2. **Umbrales optimistas.** Se eligen sobre OOF y se reportan sobre el mismo OOF. El IC bootstrap fija el umbral y remuestrea solo 6 fincas.
3. **Un positivo con pH 6,96** recibió puntaje bajo en el Modelo B; el pH solo lo clasifica bien.
4. **Recall sin pH ≈ 0,72**: el pH es indispensable.
5. Duplicar la prueba sintética como validación fue un error ya retirado del artículo (§10.3.1).

## Hallazgos sobre la app y el servidor (corregidos)
| Hallazgo | Severidad | Corrección |
|---|---|---|
| Falta permiso INTERNET en release | Alta | Añadido al manifest principal |
| Dos teléfonos con el mismo arete: se perdía el historial | Alta | Adopción del id del servidor y reenvío |
| Carreras de inserción en push → 500 | Media | Re-consulta y respuesta `duplicate`/`rejected` |
| Fechas extremas → 500 | Baja | Validación de rango |
| Recall observado con confirmaciones no ciegas | Media | Solo `ciego_al_ph = true` |
| NaN pasaba el formulario | Media | `isFinite` en validación y parseo |
| Modelo descargado tapaba una actualización de la app | Baja | Se compara con el asset de la versión |
| Cliente HTTP sin cerrar | Baja | `close()` por sincronización |
| Raza vacía rompía el ajuste | Baja | Valores faltantes como `np.nan` |

## Pendientes de la revisión (no corregidos)
- Cursor de pull en PostgreSQL (concurrencia).
- Modo ciego en la app.
- Probar en dispositivo físico.
- Token en almacén seguro.

Ver [[Implementación — Pendientes y decisiones abiertas]].
