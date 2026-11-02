# Requisitos del MVP (app + servidor)

Estado: **✔ implementado y probado** · **◐ parcial** · **✘ pendiente**.

## Funcionales

| ID | Requisito | Estado | Verificación |
|---|---|:-:|---|
| RF1 | Registrar vacas (arete único, nombre opcional) sin conexión | ✔ | `repository_test`, `widget_test` |
| RF2 | Registrar una medición con las variables del Modelo B; pH obligatorio y validado por rango | ✔ | `widget_test` (pH vacío / fuera de rango) |
| RF3 | Estimar riesgo bajo/medio/alto **localmente** al instante, con recomendación y aviso de apoyo a la decisión | ✔ | `lite_model_test`, `widget_test` |
| RF4 | Mostrar historial por vaca con estado de sincronización | ✔ | UI |
| RF5 | Registrar la prueba CMT (N, T, 1, 2, 3) y si el evaluador desconocía el pH | ✔ | `repository_test`, API |
| RF6 | Sincronizar en lotes de forma asíncrona al detectar conexión, al abrir y periódicamente | ✔ | `sync_service_test` |
| RF7 | Reintentos seguros: cero pérdidas y cero duplicados tras cortes de red (también si dos teléfonos crean el mismo arete: la app adopta la vaca del servidor y reenvía el historial) | ✔ | `sync_service_test`, `test_sync.py`, E2E |
| RF8 | Descargar nueva versión del modelo y verificar su hash antes de usarla | ✔ | `sync_service_test`, `test_sync.py` |
| RF9 | Servidor con identidad por dispositivo y aislamiento por finca | ✔ | `test_sync.py::test_farms_are_isolated` |
| RF10 | Informe de drift (PSI) y Recall observado | ◐ (informativo; sin disparador) | `test_monitoring.py` |
| RF11 | Reentrenamiento y publicación de nuevas versiones | ✘ (manual: `python -m src.export.export_model`) | — |
| RF14 | Modo de validación ciega (ocultar el riesgo hasta registrar el CMT, según el protocolo §2) | ✘ (la app muestra el riesgo de inmediato; solo cuentan las confirmaciones marcadas `ciego_al_ph`) | — |
| RF12 | Edición/borrado de registros y resolución de conflictos entre teléfonos | ✘ | — |
| RF13 | Gestión de usuarios/roles de la finca (veterinario, productor) | ✘ | — |

## No funcionales

| ID | Requisito | Estado | Nota |
|---|---|:-:|---|
| RNF1 | Operación 100 % offline (registro y estimación) | ✔ | Modelo empaquetado como asset |
| RNF2 | Modelo ligero sin runtime nativo (apto Android de gama baja) | ✔ | Regresión logística en Dart, ~13 coeficientes |
| RNF3 | Equivalencia numérica con el modelo entrenado | ✔ | Diferencia ≤ 1e-5 (ONNX), ≤ 1e-9 (Python/Dart) |
| RNF4 | Usabilidad en el corral: botones ≥ 52 dp, alto contraste, riesgo por texto + icono + color | ◐ | Sin prueba con usuarios (SUS > 75 pendiente) |
| RNF5 | Seguridad de transporte | ◐ | Requiere HTTPS en el despliegue |
| RNF6 | Almacenamiento seguro del token | ◐ | Hoy en la base local privada de la app; mejorar con almacén seguro del sistema |
| RNF7 | Privacidad (Ley 1581 de 2012) | ◐ | No se guardan datos personales de productores; falta política y consentimiento |
| RNF8 | Trazabilidad del modelo | ✔ | Cada medición guarda `model_version` |
| RNF10 | Cursor de `pull` correcto con escrituras concurrentes | ◐ | Correcto en SQLite; en PostgreSQL una transacción con `seq` menor que confirme tarde podría omitirse (pendiente: margen de seguridad o cursor por commit) |
| RNF9 | Pruebas en dispositivo físico con desconexión real | ✘ | No había dispositivo Android; solo pruebas automáticas |

## Reglas de negocio

1. El sistema **no diagnostica**: estima riesgo como apoyo a la decisión (aviso en cada resultado).
2. Sin pH no hay estimación (Recall sin pH ≈ 0,72 < meta 0,80).
3. Un resultado “bajo” no descarta mastitis (3 de 112 positivos cayeron en “bajo” en la validación).
4. Umbrales: “alto” ⇒ Recall OOF ≥ 0,95; “medio” ⇒ Recall OOF ≥ 0,97 (ver `src/models/evaluation.py::select_thresholds`). Se eligen y se reportan sobre las mismas predicciones OOF (optimistas).
5. Un modelo solo con pH iguala o supera al Modelo B en esta muestra (ver `docs/cambios_articulo.md` §1).
6. El Recall observado en el servidor solo usa confirmaciones ciegas y tiene sesgo de verificación si el CMT se hace sobre todo a vacas de riesgo medio/alto.
