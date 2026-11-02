# API del servidor (v1)

Servidor FastAPI en `server/`. Documentación interactiva: `GET /docs` (OpenAPI). Arranque local:

```bash
.venv/bin/python -m server.scripts.create_device --finca "Finca El Roble" --nombre "Celular Juan"   # imprime el token una sola vez
ADMIN_TOKEN=cambiar-esto .venv/bin/uvicorn server.app.main:app --host 0.0.0.0 --port 8000
```

Variables de entorno: `DATABASE_URL` (por defecto `sqlite:///./server_data.db`; para PostgreSQL usar `postgresql+psycopg://…` e instalar el driver), `MODELS_DIR` (por defecto `models/`), `ADMIN_TOKEN` (sin él, el monitoreo queda deshabilitado).

> La transmisión debe ir sobre **HTTPS** (terminación TLS en el proxy del despliegue). El token viaja en `Authorization: Bearer <token>`.

## Autenticación

- **Dispositivo:** token aleatorio (32 bytes) emitido por `create_device`. El servidor guarda solo su SHA-256. Cada dispositivo pertenece a **una finca** y solo ve/escribe datos de esa finca.
- **Administrador:** `ADMIN_TOKEN` para `/v1/monitoring/*`.

## Endpoints

| Método y ruta | Auth | Descripción |
|---|---|---|
| `GET /health` | — | Estado y versión del modelo |
| `POST /v1/sync/push` | dispositivo | Envía un lote (≤ 500 registros) |
| `GET /v1/sync/pull` | dispositivo | Cambios de la finca posteriores a los cursores |
| `GET /v1/model/manifest` | dispositivo | `{model_version, files{nombre: sha256}}` |
| `GET /v1/model/lite` | dispositivo | `model_lite.json` (cabecera `X-Model-Sha256`) |
| `GET /v1/monitoring/drift` | admin | PSI por variable y Recall observado con CMT |

### `POST /v1/sync/push`

```json
{
  "vacas":          [{"id": "uuid", "arete": "A-001", "nombre": "Lola"}],
  "mediciones":     [{"id": "uuid", "vaca_id": "uuid", "fecha_medicion": "2026-11-01T10:30:00Z",
                      "edad": 5, "raza": "Holstein", "numero_de_partos": 3, "volumen_de_leche": 11.0,
                      "etapa_de_lactancia": 1, "antecedentes_de_mastitis": 0, "humedad": 70.0,
                      "temperatura": 12.0, "ph_leche": 6.9, "probabilidad": 0.8,
                      "nivel_riesgo": "alto", "model_version": "mastitis-B-lr-xxxx"}],
  "confirmaciones": [{"id": "uuid", "medicion_id": "uuid", "fecha": "2026-11-01T10:40:00Z",
                      "resultado_positivo": true, "grado": "2", "evaluador": "Vet", "ciego_al_ph": true}]
}
```

- Los `id` son UUID **generados en el cliente**: el reintento de un lote es seguro (idempotente).
- Fechas con **zona horaria** obligatoria (ISO 8601); no se aceptan fechas > 1 día en el futuro ni anteriores a 2020.
- Opcionales (pueden ser `null`): `volumen_de_leche`, `humedad`, `temperatura`. Obligatorios: pH, edad, raza, partos, lactancia, antecedentes.
- Campos desconocidos se rechazan (`extra=forbid`): p. ej. no se acepta conductividad.
- Rangos de calidad de datos: los de `model_lite.json → ranges` (edad 1–25, partos 0–20, volumen 0–100, humedad 0–100, temperatura −20–50, pH 5,5–8,0).
- Confirmaciones: `grado` ∈ {N, T, 1, 2, 3}; debe ser coherente con `resultado_positivo` (positivo = 1, 2, 3).

**Respuesta (200)** — aceptación **parcial**: cada ítem recibe su propio estado.

```json
{"results": {"vacas": [{"id": "…", "status": "accepted"}],
             "mediciones": [{"id": "…", "status": "rejected", "reason": "ph_leche: fuera de rango [5.5, 8.0]"}],
             "confirmaciones": [{"id": "…", "status": "retry", "reason": "medición desconocida en el servidor"}]},
 "server_time": "…", "model_version": "…"}
```

| Estado | Significado | Acción del cliente |
|---|---|---|
| `accepted` | Guardado | Marcar sincronizado |
| `duplicate` | Ya existía idéntico | Marcar sincronizado (éxito) |
| `rejected` | Error permanente (validación, conflicto, otra finca) | Marcar rechazado, no reintentar |
| `retry` | Falta una dependencia (p. ej. la vaca) | Dejar pendiente y reintentar luego |

Los registros son **append-only**: reenviar un id existente con contenido distinto se rechaza (`conflicto`) y **no** sobrescribe. Las vacas son inmutables en el MVP (arete único por finca).

### `GET /v1/sync/pull?cursor_vacas=0&cursor_mediciones=0&cursor_confirmaciones=0&limit=500`

Devuelve `vacas`, `mediciones`, `confirmaciones` de **su finca** con `seq` mayor al cursor, `cursors` nuevos y `has_more`. El cliente repite hasta `has_more = false` y guarda los cursores.

> Límite conocido: con PostgreSQL y escrituras concurrentes, una fila con `seq` menor que se confirme después de otra mayor ya leída podría omitirse. En SQLite (escrituras serializadas) no ocurre. Pendiente antes de producción.

### Errores

`401` token de dispositivo inválido/ausente · `403` token de administrador inválido o administración deshabilitada · `422` cuerpo no válido (p. ej. lote > 500) · `503` modelo o línea base de drift no disponibles · `500` el modelo en disco no coincide con el manifiesto.

## Monitoreo (`GET /v1/monitoring/drift`)

- **Data drift:** PSI por variable frente a `models/drift_baseline.json` (< 0,10 estable; 0,10–0,25 moderado; ≥ 0,25 alto). Requiere ≥ 30 mediciones recientes (`window`, `min_rows`).
- **Recall observado:** solo con confirmaciones CMT **ciegas al pH** (`ciego_al_ph = true`); se informa con ≥ 20 positivos confirmados. Se calcula para “alto” y para “medio o alto”; se reporta cuántas confirmaciones fueron ciegas al pH.
- `revisar_reentrenamiento.recomendado` es **informativo**; el reentrenamiento exige decisión humana.
