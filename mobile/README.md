# App móvil (Flutter, Android)

Cliente offline-first: registra vacas y mediciones en SQLite, estima el riesgo con el modelo lite embebido (`assets/model_lite.json`) y sincroniza cuando hay conexión.

- Configure el servidor en **Configuración** (URL `https://…` y el código del dispositivo que imprime `server.scripts.create_device`).
- El asset `assets/model_lite.json` se regenera con `python -m src.export.export_model`; una prueba verifica que sea idéntico a `models/model_lite.json`.
- Pruebas: `flutter analyze && flutter test`. El E2E contra un servidor real está en `../scripts/e2e_local.py`.
- Arquitectura: `lib/models` (modelo lite y entidades), `lib/data` (SQLite y repositorio), `lib/sync` (API HTTP, servicio y controlador), `lib/state`, `lib/ui`.
