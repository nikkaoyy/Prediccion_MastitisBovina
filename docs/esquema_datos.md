# Esquema de datos

## Servidor (SQLAlchemy; SQLite en desarrollo, PostgreSQL previsto) — `server/app/db.py`

| Tabla | Campos clave | Notas |
|---|---|---|
| `fincas` | `id` (uuid), `nombre` (único) | Creada por `create_device` |
| `dispositivos` | `id`, `nombre`, `finca_id`, `token_hash` (SHA-256), `activo` | Un dispositivo ↔ una finca |
| `vacas` | `seq` (PK autoincremental), `id` (uuid cliente, único), `finca_id`, `arete` (único por finca), `nombre`, `device_id`, `recibido_en` | Inmutable en el MVP |
| `mediciones` | `seq`, `id` (uuid cliente), `vaca_id`, `finca_id`, `device_id`, `fecha_medicion` (UTC), 9 variables del Modelo B, `probabilidad` (puntaje), `nivel_riesgo`, `model_version`, `recibido_en` | `volumen_de_leche`, `humedad`, `temperatura` admiten NULL. Cada medición guarda la **versión del modelo** que produjo la estimación |
| `confirmaciones_cmt` | `seq`, `id`, `medicion_id`, `finca_id`, `fecha`, `resultado_positivo`, `grado` (N/T/1/2/3), `evaluador`, `ciego_al_ph` | Evento aparte: la verdad de referencia nunca edita la medición |

`seq` es el cursor de `pull` (monótono por tabla). Se omite deliberadamente almacenar datos personales de productores.

## Cliente (SQLite local, `mobile/lib/data/app_database.dart`)

Mismas tablas `vacas`, `mediciones`, `confirmaciones` más:

- `sync_state` ∈ {`pending`, `synced`, `rejected`} y `sync_error` por registro.
- `meta(key, value)`: `server_url`, `device_token`, cursores (`cursor_vacas`…), `last_sync_at` y `lite_model` (modelo descargado).
- Sin claves foráneas: en `pull` una medición puede llegar antes que su vaca (cursores independientes).

**Garantía offline:** ningún registro se borra por un fallo de red; solo cambia de estado cuando el servidor responde por ese id.

## Modelo (`models/`)

| Archivo | Contenido |
|---|---|
| `model_lite.json` | Medianas, medias/escalas, categorías de raza, coeficientes, intercepto, umbrales (`alto`, `medio`), rangos válidos, entradas obligatorias, aviso, `model_version` (hash del contenido) |
| `model.onnx` | Pipeline completo (raza como texto). En ONNX la raza es obligatoria (el imputador de texto no es convertible); el JSON sí rellena la raza vacía |
| `manifest.json` | Versión y SHA-256 de cada archivo; el cliente verifica el hash antes de reemplazar el modelo |
| `model_card.json` | Métricas OOF, IC bootstrap por finca, validación dejando una finca fuera, umbrales y advertencias |
| `parity_fixtures.json` | Casos de paridad sklearn ↔ ONNX ↔ Python ↔ Dart (tolerancia 1e-5) |
| `drift_baseline.json` | Distribución de referencia (PSI) |

## Variables del Modelo B

`edad` (1–25), `raza` (Holstein, Normando, Jersey, Pardo_Suizo, Cruzado; otra → sin categoría), `numero_de_partos` (0–20), `volumen_de_leche` (L/día, opcional), `etapa_de_lactancia` (0 temprana, 1 tardía), `antecedentes_de_mastitis` (0/1), `humedad` (%, opcional), `temperatura` (°C ambiental, opcional), `ph_leche` (5,5–8,0, **obligatorio**).
