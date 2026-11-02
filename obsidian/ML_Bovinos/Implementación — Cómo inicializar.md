# Implementación — Cómo inicializar

Parte de [[Implementación 2026-11-01 — Índice]]. Versión completa en `CONTEXT.md` del repositorio.

## 1. Python
```bash
cd Prediccion_MastitisBovina
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q          # 45 pasan
```

## 2. Modelo
```bash
.venv/bin/python main.py --feature-set B        # entrenamiento y reportes
.venv/bin/python -m src.export.export_model     # regenera models/ y mobile/assets/
```
Ejecutar `export_model` después de cualquier cambio en datos o en el modelo.

## 3. Servidor
```bash
.venv/bin/python -m server.scripts.create_device --finca "Mi finca" --nombre "Celular 1"
ADMIN_TOKEN=cambiar-esto .venv/bin/uvicorn server.app.main:app --port 8000
```
El token del dispositivo se muestra una sola vez.

## 4. App
```bash
export PATH=$PATH:~/development/flutter/bin ANDROID_HOME=~/Android/Sdk
cd mobile && flutter pub get && flutter test && flutter build apk --debug
```
En la app: Configuración → URL y código del dispositivo → Guardar y sincronizar.

## 5. Prueba de extremo a extremo
```bash
.venv/bin/python scripts/e2e_local.py
```
