# Implementación — Pruebas y verificación

Parte de [[Implementación 2026-11-01 — Índice]].

| Suite | Comando | Resultado |
|---|---|---|
| Python (ML + servidor) | `.venv/bin/python -m pytest -q` | 45 pasan |
| Dart (app) | `cd mobile && flutter test` | 35 pasan, 1 omitida (E2E) |
| Análisis estático Dart | `flutter analyze` | Sin problemas |
| E2E servidor real + cliente Dart | `.venv/bin/python scripts/e2e_local.py` | 12 registros exactamente una vez |
| Compilación | `flutter build apk --debug` / `--release` | OK |

## Qué cubre cada grupo
- **ML:** contrato de variables A/B, imputación sin fuga, raza vacía, bootstrap determinista y por fincas, umbrales reales sin redondeo, paridad con ONNX y lite (incluye casos límite).
- **Servidor:** autenticación, idempotencia, conflictos, aislamiento por finca, dependencias (`retry`), paginación, lotes grandes, fechas extremas, carreras simuladas, monitoreo, línea base ausente.
- **App:** paridad del modelo Dart, validación de entrada, repositorio, sincronización con cortes de red, reenvío sin duplicados, mismo arete en dos teléfonos, modelo descargado con hash incorrecto o dañado, widgets del formulario y del resultado.

## Lo que no está verificado
- Dispositivo Android físico y emulador (solo compilación).
- PostgreSQL y concurrencia real.
- Validez clínica (no hay datos nuevos).
- HTTPS en producción.

## Cómo se encontraron los errores
Una revisión independiente (subagente) leyó el código y reprodujo casos: permiso INTERNET en release, arete duplicado entre teléfonos, carreras y fechas extremas en el servidor, NaN en el formulario, sesgo de los umbrales y el comparador solo-pH. Todos se corrigieron y tienen prueba, salvo los pendientes listados en [[Implementación — Pendientes y decisiones abiertas]].
