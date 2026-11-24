# Predicción de Mastitis Subclínica Bovina — pipeline de ML, servidor y app offline-first

Estimación de **riesgo** de mastitis subclínica en hatos de doble propósito del altiplano cundiboyacense, bajo CRISP-ML(Q): pipeline de aprendizaje automático (Python), servidor de sincronización (FastAPI) y app móvil offline-first (Flutter + SQLite).

> **Es una herramienta de apoyo a la decisión. No es un diagnóstico y no sustituye la valoración veterinaria ni la prueba confirmatoria (CMT).**
> Estado de los resultados: **preliminares** (209 registros, 6 fincas, sin validación externa; el pH separa casi perfectamente las clases). Ver `docs/cambios_articulo.md` y `docs/protocolo_verdad_referencia.md`.

## Estructura

| Carpeta | Contenido |
|---|---|
| `src/data`, `src/models` | Validación de datos, features sin fuga, entrenadores (árbol, Random Forest, regresión logística), evaluación (bootstrap por finca, umbrales) |
| `src/export` | Entrena el **Modelo B** final y exporta ONNX + `model_lite.json` |
| `models/` | Artefactos versionados: `model_lite.json`, `model.onnx`, `manifest.json`, `model_card.json`, `parity_fixtures.json`, `drift_baseline.json` |
| `server/` | API FastAPI de sincronización, distribución del modelo y monitoreo |
| `mobile/` | App Flutter (Android) con SQLite local y modelo lite embebido |
| `docs/` | Requisitos, esquema de datos, API, protocolo CMT y lista de cambios del artículo |
| `tests/`, `server/tests`, `mobile/test` | Pruebas de ML, servidor y app |
| `obsidian/` | Bóveda de notas del proyecto |

## Modelos

- **Modelo A** (`--feature-set A`): incluye conductividad eléctrica; solo para análisis de laboratorio.
- **Modelo B** (`--feature-set B`, desplegable): edad, raza, partos, volumen, lactancia, antecedentes, humedad, temperatura ambiental y **pH (obligatorio)**. Sin conductividad.

## Uso

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt

# Entrenar y evaluar (validación agrupada por finca, IC bootstrap, leave-one-farm-out)
.venv/bin/python main.py --feature-set B        # reportes en demo_reports/, modelos en src/data/artifacts/

# Exportar el modelo desplegable (regenera models/ y mobile/assets/model_lite.json)
.venv/bin/python -m src.export.export_model

# Servidor
.venv/bin/python -m server.scripts.create_device --finca "Mi finca" --nombre "Celular 1"   # imprime el token
ADMIN_TOKEN=... .venv/bin/uvicorn server.app.main:app --host 0.0.0.0 --port 8000

# App (requiere Flutter; ver mobile/README.md)
cd mobile && flutter pub get && flutter test && flutter build apk --debug
```

## Pruebas

```bash
.venv/bin/python -m pytest                    # ML + servidor
cd mobile && flutter analyze && flutter test  # app (paridad del modelo, SQLite, sincronización, widgets)
.venv/bin/python scripts/e2e_local.py         # servidor real + cliente Dart real (offline → online → reenvío)
```

## Limitaciones conocidas

No hay validación externa ni pruebas en dispositivo físico; el reentrenamiento y la resolución de conflictos de edición no están implementados; el token del dispositivo se guarda en la base local de la app. Detalle en `docs/requisitos.md`.

## El baúl de información (Obsidian)

El conocimiento del proyecto no vive en la cabeza de nadie ni en un chat: vive en una bóveda de Obsidian que se
versiona junto al código, en `obsidian/ML_Bovinos/`. Cada decisión tiene su nota y su motivo —por qué GroupKFold y no
un split aleatorio, por qué el modelo de campo es la regla `pH ≤ 6.735`, qué se probó y no funcionó—, y las notas se
enlazan entre sí para que el contexto no se pierda al cambiar de etapa.

La regla es simple: **una sola fuente de verdad**. Lo que se decide se escribe allí en el momento, con fecha y con la
cifra que lo respalda; lo que se corrige no se borra, se anota. Así el informe, el artículo y la app beben del mismo
sitio, y quien retome el proyecto en seis meses entiende por qué está hecho como está sin tener que preguntar.

## Uso ético de la IA

- **Datos de terceros**, con cuidado: los registros de los hatos no llevan identificación de productores y lo que se
  publica son cifras agregadas.
- **El modelo no diagnostica.** Estima un riesgo que apoya la decisión del veterinario; el diagnóstico se hace con la
  prueba en campo. El repositorio lo dice donde se usa, no en letra pequeña.
- **Se declaran los límites**: 209 observaciones, seis fincas, una región. Un modelo así no se extrapola a otro clima
  ni a otra raza sin volver a medirlo.
- **Reproducibilidad** como forma de honestidad: el pipeline, las semillas y las pruebas de paridad están en el repo
  para que cualquiera pueda repetir las cifras y contradecirlas.

## La app móvil

En `mobile/`: Flutter con SQLite, pensada para el campo. Funciona **sin conexión** —el técnico registra en el potrero,
no en la oficina— y sincroniza cuando vuelve la red; el servidor de sincronización está en el mismo repositorio. Usa
`model_lite.json`, una versión reducida del modelo que corre en el teléfono sin depender de un servicio.
