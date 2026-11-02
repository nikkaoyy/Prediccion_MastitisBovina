# CONTEXT.md — Estado del proyecto y guía de inicio

Última actualización: 2026-11-01.

Proyecto: estimación de **riesgo** de mastitis subclínica bovina en hatos de doble propósito (altiplano cundiboyacense), bajo CRISP-ML(Q). Tiene tres partes: pipeline de ML (Python), servidor de sincronización (FastAPI) y app móvil offline-first (Flutter + SQLite).

> Es apoyo a la decisión. No es diagnóstico. Los resultados son **preliminares**: 209 registros, 6 fincas, sin validación externa.

---

## 1. Cómo inicializar

### Requisitos
- Python 3.10+ (probado con 3.14).
- Flutter 3.47+ y Android SDK (`~/Android/Sdk`, con platform-tools, platforms;android-36, build-tools;36.0.0 y NDK) para la app.
- Java 17+ (probado con 25) para Gradle.

### 1.1 Entorno Python
```bash
cd Prediccion_MastitisBovina
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```
Ya existe un `.venv/` en esta máquina; basta con reinstalar si cambian dependencias.

### 1.2 Verificar ML y servidor
```bash
.venv/bin/python -m pytest -q          # esperado: 94 passed (~3 min)
```

### 1.3 Entrenar y evaluar
```bash
.venv/bin/python main.py --feature-set B    # Modelo desplegable (default)
.venv/bin/python main.py --feature-set A    # Modelo de laboratorio (con conductividad)
```
Salidas: `artifacts/reports/` (métricas JSON, matrices de confusión, árbol) y `artifacts/models/` (pipelines `.pkl`). Las figuras antiguas que cita el artículo siguen en `demo_reports/`, que ya no se regenera.

Cada modelo también corre por separado desde la raíz, con el conjunto A por defecto:
```bash
.venv/bin/python -m src.models.DecisionTreeTraining
.venv/bin/python -m src.models.RandomForest
.venv/bin/python -m src.models.LogisticalRegresion
```

### 1.4 Exportar el modelo desplegable
```bash
.venv/bin/python -m src.export.export_model
```
Regenera `models/` (model.onnx, model_lite.json, manifest.json, model_card.json, parity_fixtures.json, drift_baseline.json) y copia `model_lite.json` a `mobile/assets/`. **Ejecutar siempre tras cambiar datos o código del modelo**, porque la app y el servidor leen estos archivos.

Para exportar el árbol de decisión (conjunto A) a JSON autocontenido, sin ONNX:
```bash
.venv/bin/python -m src.models.DecisionTreeTraining
.venv/bin/python -m src.export.export_tree     # artifacts/models/model.json
```
El intérprete de referencia es `src/export/tree_eval.py`. Un cliente debe comparar `float32(valor) <= umbral`, porque scikit-learn hace lo mismo. `model.json` no reemplaza a `model_lite.json`: la app y el servidor siguen usando el Modelo B.

Para comparar el modelo completo con el de campo (8 variables, sin pH ni conductividad):
```bash
.venv/bin/python -m src.models.compare_variants   # docs/TABLA_TRANSPARENCIA_METRICAS.md
```

### 1.5 Servidor
```bash
# 1) Registrar una finca y un dispositivo (el token se muestra una sola vez)
.venv/bin/python -m server.scripts.create_device --finca "Finca El Roble" --nombre "Celular 1"

# 2) Arrancar (desarrollo: SQLite; producción: DATABASE_URL=postgresql+psycopg://...)
ADMIN_TOKEN=cambiar-esto .venv/bin/uvicorn server.app.main:app --host 0.0.0.0 --port 8000
```
- Documentación interactiva: `http://localhost:8000/docs`.
- Variables: `DATABASE_URL` (por defecto `sqlite:///./server_data.db`), `MODELS_DIR` (por defecto `models/`), `ADMIN_TOKEN` (sin él, `/v1/monitoring/*` queda deshabilitado).
- En producción debe ir detrás de HTTPS.

### 1.6 App móvil
```bash
export PATH=$PATH:~/development/flutter/bin ANDROID_HOME=~/Android/Sdk
cd mobile
flutter pub get
flutter analyze          # esperado: No issues found
flutter test             # esperado: 35 passed (1 skipped = E2E)
flutter build apk --debug      # build/app/outputs/flutter-apk/app-debug.apk
flutter build apk --release    # app-release.apk (52 MB, con permiso INTERNET)
```
En la app: **Configuración** → URL del servidor (`https://…`) y código del dispositivo → "Guardar y sincronizar".

### 1.7 Prueba de extremo a extremo
```bash
.venv/bin/python scripts/e2e_local.py
```
Levanta un servidor real, ejecuta el cliente Dart real (offline → online → reenvío → segundo teléfono) y verifica que cada registro existe exactamente una vez.

---

## 2. Estructura del repositorio

```
main.py                         CLI de entrenamiento/evaluación (--feature-set A|B)
src/data/
  dataValidation.py             DataValidator, FEATURE_SETS A/B, contrato de calidad
  featureEngineer.py            Preprocesamiento sin fuga (ColumnTransformer dentro del Pipeline)
  dummyDataGenerator.py         Generador sintético (solo para consistencia, no validación)
src/models/
  DecisionTreeTraining.py       Entrenador árbol (GroupKFold anidado)
  RandomForest.py               Entrenador Random Forest
  LogisticalRegresion.py        Entrenador regresión logística
  evaluation.py                 Bootstrap por finca, umbrales OOF, leave-one-farm-out, baseline pH
src/export/
  export_model.py              Entrena Modelo B final y exporta artefactos a models/
  lite_eval.py                 Evaluador Python del modelo lite (referencia de paridad)
models/                         Artefactos versionados del modelo desplegable
server/
  app/main.py                  create_app() y routers
  app/config.py                Settings desde variables de entorno
  app/db.py                    Modelo SQLAlchemy (fincas, dispositivos, vacas, mediciones, confirmaciones_cmt)
  app/security.py              Tokens de dispositivo (hash SHA-256) y token admin (compare_digest)
  app/schemas.py               Validación de entrada (extra=forbid, lote ≤ 500, fechas con zona)
  app/routers/sync.py          push idempotente y pull por cursores seq
  app/routers/model.py         manifest y descarga de model_lite.json con hash
  app/monitoring.py            PSI de drift y Recall observado (solo CMT ciegos)
  scripts/create_device.py     Registro de finca/dispositivo
  tests/                       Pruebas del servidor
mobile/                         App Flutter (Android)
  lib/models/                  LiteModel (regresión logística en Dart), entidades
  lib/data/                    AppDatabase (SQLite), Repository
  lib/sync/                    SyncApi (HTTP), SyncService, SyncController, ModelStore
  lib/state/app_state.dart     Estado global (Provider)
  lib/ui/                      Pantallas en español (inicio, vaca, medición, resultado, CMT, configuración)
  assets/model_lite.json       Modelo empaquetado
  test/                        Pruebas unitarias, de repositorio, sync, widgets, E2E
docs/                           Requisitos, esquema, API, protocolo CMT, cambios del artículo
data/templates/                 Plantilla CSV de recolección de datos nuevos
data/raw/                       Dataset (209 filas)
scripts/e2e_local.py            Prueba E2E servidor real + cliente Dart
tests/                          Pruebas de ML (features A/B, sin fuga, bootstrap, paridad)
obsidian/ML_Bovinos/            Bóveda de Obsidian (ver sección 6)
```

---

## 3. Modelo desplegable (Modelo B)

- **Algoritmo:** regresión logística (`class_weight=balanced`, C=1, GroupKFold 5). Versión actual: `mastitis-B-lr-d4ae0119`.
- **Variables (9):** edad, raza, número de partos, volumen de leche (opc.), etapa de lactancia, antecedentes de mastitis, humedad (opc.), temperatura **ambiental** (opc.), **pH de la leche (obligatorio)**.
- **Umbrales:** alto = 0,579; medio = 0,415 (elegidos sobre OOF; ver sesgo abajo).
- **Métricas OOF (GroupKFold 5):** accuracy 0,971 · precisión 0,982 · recall 0,964 · F1 0,973 · ROC-AUC 0,981.
- **Recall al umbral de alerta:** 0,955 (IC 95 % bootstrap por finca: 0,906–0,993).
- **Riesgo por nivel (OOF):** de 112 positivos, 107 alto, 2 medio, 3 bajo.

### Hallazgos que deben conocerse
1. **Un modelo solo con pH rinde igual o mejor:** regresión logística solo-pH, mismo esquema, Recall/Precisión/AUC = 1,00. Las 8 variables adicionales no están justificadas empíricamente con esta muestra.
2. **Sesgo optimista:** los umbrales se eligen y se reportan sobre las mismas predicciones OOF. El bootstrap fija el umbral y remuestrea solo 6 fincas, así que subestima la incertidumbre.
3. **Separación casi perfecta:** sanos ≤ pH 6,72; enfermos ≥ pH 6,75. Puede ser efecto biológico o circularidad de la etiqueta CMT. No hay forma de saberlo sin protocolo ciego.
4. **Sin pH no hay estimación viable:** Recall ≈ 0,71–0,73 sin pH ni conductividad.
5. **Modelo A** (con conductividad, 12 variables): solo laboratorio, no se despliega.

---

## 4. Servidor (resumen de API)

| Método y ruta | Auth | Función |
|---|---|---|
| `GET /health` | — | Estado y versión del modelo |
| `POST /v1/sync/push` | Bearer dispositivo | Lote ≤ 500: vacas, mediciones, confirmaciones |
| `GET /v1/sync/pull` | Bearer dispositivo | Cambios de la finca desde cursores `seq` |
| `GET /v1/model/manifest` | Bearer dispositivo | Versión y SHA-256 |
| `GET /v1/model/lite` | Bearer dispositivo | model_lite.json (cabecera `X-Model-Sha256`) |
| `GET /v1/monitoring/drift` | Admin | PSI por variable y Recall observado (solo CMT ciegos) |

**Estados por ítem en push:** `accepted`, `duplicate` (éxito idempotente), `rejected` (no reintentar), `retry` (falta dependencia, p. ej. la vaca).

**Reglas:**
- IDs son UUID generados en el cliente → reintentos seguros.
- Registros append-only: un id con contenido distinto se rechaza como conflicto.
- Aislamiento por finca: un dispositivo nunca ve ni escribe datos de otra finca.
- Fechas con zona horaria obligatoria, entre 2020 y 1 día en el futuro.
- Campos extra se rechazan (no se acepta conductividad).
- Carreras de inserción simultánea se resuelven como `duplicate` o `rejected`, nunca 500.

Detalle en `docs/api.md` y `docs/esquema_datos.md`.

---

## 5. App móvil (resumen)

- **Offline-first:** todo se guarda en SQLite local. Ningún registro se borra por fallo de red; cambia de estado (`pending` → `synced` / `rejected`) solo con respuesta del servidor por ese id.
- **Sincronización:** al abrir, al recuperar conexión y cada 15 min. Orden: push (vacas → mediciones → confirmaciones) → pull por cursores → actualización del modelo con verificación de hash.
- **Mismo arete en dos teléfonos:** la app adopta el id de la vaca del servidor, reasigna el historial local y lo reenvía.
- **Modelo:** se usa el descargado solo si fue guardado sobre el mismo asset de la app; si la app se actualiza, vuelve al empaquetado.
- **Validación:** pH obligatorio y finito; rangos fisiológicos; coma o punto decimal.
- **Textos:** cada resultado muestra el aviso de apoyo a la decisión y una recomendación por nivel.

### Pendiente en la app
- **Modo ciego:** la app muestra el riesgo de inmediato. La casilla `ciego_al_ph` es declarativa.
- Edición o borrado de registros; gestión de usuarios y roles.
- Token guardado en la base local (debería ir a almacén seguro del sistema).
- Probar en dispositivo físico (no se tuvo teléfono; solo compilación y pruebas automáticas).

---

## 6. Vault de Obsidian

Carpeta: `obsidian/ML_Bovinos/`. Notas nuevas de esta fase:
- `Implementación 2026-11-01 — Índice.md`: mapa de la fase.
- Notas por componente (ML, servidor, app, documentación) enlazadas al índice.

Las notas anteriores (p. ej. `CORE DEL PROYECTO.md`) se actualizaron en su tabla de estado.

---

## 7. Problemas conocidos y decisiones abiertas

| Tema | Estado |
|---|---|
| Validación con datos nuevos de campo | Pendiente. Protocolo en `docs/protocolo_verdad_referencia.md` y plantilla en `data/templates/` |
| Modo ciego en la app | Pendiente |
| Modelo solo-pH vs Modelo B | Decisión de los autores (ver §3) |
| Umbrales con sesgo optimista | Requiere CV anidada o datos nuevos |
| Cursor de pull en PostgreSQL | Pendiente: podría omitir filas con escrituras concurrentes (correcto en SQLite) |
| Reentrenamiento automático | No implementado (manual con `export_model`) |
| Permiso de notificaciones / cifrado del token | Pendiente |
| Artículo (.docx) | No modificado; correcciones en `docs/cambios_articulo.md` |
| Commits | Ninguno realizado; hay cambios sin commitear |
| Notas de Obsidian antiguas (208/7 filas) | Corregir en cualquier nota que aún lo diga |
| `demo_reports/` | Figuras antiguas citadas por el artículo; ya no se regeneran (`main.py` escribe en `artifacts/reports/`) |

---

## 8. Historial de la fase (2026-11-01)

1. Auditoría de datos y del código existente; se detectó que el artículo no coincide con el código ni con los datos.
2. Plan aprobado: congelar el modelo, exportar, documentar, servidor, app Flutter, cierre y revisión independiente.
3. Modelo A/B parametrizado (`FEATURE_SETS`), `evaluation.py` (bootstrap por finca, umbrales, LOFO, baseline pH).
4. Exportación ONNX y `model_lite.json`; paridad verificada.
5. Servidor FastAPI con sync idempotente, monitoreo y pruebas.
6. App Flutter con SQLite, sincronización, UI y pruebas; APKs compilados.
7. E2E con servidor real.
8. Documentación (`docs/`, README, este archivo).
9. Revisión independiente (subagente): se corrigieron el permiso INTERNET, la carrera de aretes, las carreras del servidor, fechas extremas, NaN, el sesgo del Recall observado, la prioridad del modelo y la raza vacía.
