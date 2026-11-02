# Implementación — Servidor de sincronización

Parte de [[Implementación 2026-11-01 — Índice]].

## Componentes
- `server/app/main.py`: `create_app()`; crea tablas al arrancar; monta routers `sync`, `model`, `monitoring`.
- `server/app/config.py`: `DATABASE_URL`, `MODELS_DIR`, `ADMIN_TOKEN`.
- `server/app/db.py`: fincas, dispositivos, vacas (`seq` PK + `id` UUID), mediciones, confirmaciones_cmt.
- `server/app/security.py`: token de dispositivo (32 bytes, se guarda su SHA-256); admin con `hmac.compare_digest`.
- `server/app/schemas.py`: `extra=forbid`, lote ≤ 500, fechas con zona horaria y dentro de 2020…+1 día.
- `server/app/routers/sync.py`: push idempotente, pull por cursores.
- `server/app/routers/model.py`: manifest y descarga verificada por hash.
- `server/app/monitoring.py`: PSI (drift) y Recall observado.
- `server/scripts/create_device.py`: alta de finca y dispositivo.

## Semántica del push
| Estado | Cuándo | Acción del cliente |
|---|---|---|
| accepted | Guardado | Marcar sincronizado |
| duplicate | Ya existía igual | Marcar sincronizado |
| rejected | Validación, conflicto, otra finca, fecha inválida | Marcar rechazado |
| retry | Falta la vaca o la medición padre | Reintentar después |

- Carreras de inserción: se consulta de nuevo y se responde `duplicate` o `rejected`; nunca 500.
- Monitoreo: el Recall observado solo cuenta confirmaciones con `ciego_al_ph = true`.
- Sin `drift_baseline.json` → 503.

## Límites conocidos
- Cursor `seq` en PostgreSQL: con escrituras concurrentes, una fila con `seq` menor que confirme tarde podría omitirse. Correcto en SQLite. Pendiente.
- Producción: HTTPS obligatorio; no hay pruebas contra PostgreSQL real.
- No hay gestión de usuarios ni roles.

Ver `docs/api.md` y `docs/esquema_datos.md` en el repositorio.
