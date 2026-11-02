# Implementación — App móvil Flutter

Parte de [[Implementación 2026-11-01 — Índice]].

## Arquitectura (`mobile/lib/`)
- `models/lite_model.dart`: regresión logística en Dart; `predict`, `levelFor`, `validate`; rechaza NaN e infinito.
- `models/entities.dart`: Vaca, Medicion, Confirmacion (escala CMT N/T/1/2/3), MedicionInput.
- `data/app_database.dart`: SQLite con tablas vacas, mediciones, confirmaciones, meta. Sin claves foráneas (el pull puede llegar desordenado).
- `data/repository.dart`: CRUD local, lote pendiente en orden vacas → mediciones → confirmaciones, `applyResults`, `mergeFromServer` (adopta id del servidor ante arete repetido).
- `sync/sync_api.dart`: cliente HTTP con timeouts y errores tipados (`NetworkException`, `ApiException`); `close()`.
- `sync/sync_service.dart`: push → pull → actualización del modelo (verifica hash y versión).
- `sync/sync_controller.dart`: sincroniza al abrir, al recuperar conexión y cada 15 min.
- `sync/model_store.dart`: modelo descargado solo si coincide con el asset de esta versión de la app.
- `state/app_state.dart`: estado global con Provider.
- `ui/`: inicio (lista de vacas con banner de sync), vaca (historial), formulario de medición, resultado (riesgo, recomendación, aviso), CMT, configuración.

## Reglas de UI
- pH obligatorio; coma o punto decimal; "NaN" rechazado.
- Opcionales (volumen, humedad, temperatura) pueden quedar vacíos; el modelo imputa.
- Riesgo mostrado con texto + icono + color.
- Aviso de apoyo a la decisión en cada resultado.

## Estado
- `flutter analyze`: sin problemas.
- `flutter test`: 35 pruebas (paridad del modelo, repositorio, sincronización con servidor simulado con cortes, ModelStore, widgets).
- E2E con servidor real: 12 registros exactamente una vez.
- APKs: `app-debug.apk` (174 MB) y `app-release.apk` (52 MB), con permiso INTERNET.

## Pendiente
- [ ] Modo ciego (ocultar riesgo hasta registrar CMT).
- [ ] Token en almacén seguro del sistema.
- [ ] Prueba en teléfono físico (desconexión real).
- [ ] Edición y borrado de registros.
- [ ] Textos en el manifest: `android:label="Mastitis"`, paquete `co.edu.udistrital.mastitis_app`.
