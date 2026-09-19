# Hoja de Ruta y Próximos Pasos

> **Fase:** Transición de ordenamiento y auditoría hacia ejecución experimental real.  
> **Meta:** Culminación del artículo académico y despliegue del pipeline con el dataset CSV real.

---

## 🎯 Plan de Trabajo Inmediato (Paso a Paso)

Habiendo culminado la organización del proyecto en Obsidian y el diagnóstico técnico de rutas y datos, a continuación se desglosan las tareas para la siguiente fase:

### Etapa 1: Curación y Limpieza del Dataset Real (`data/raw/`)
1. **Normalización de Fincas:** Corregir las etiquetas de Finca 6 en `data/raw/datos_entrenamiento_mastitis-v3.csv` para que todas aparezcan uniformemente como `Finca_6` (evitando la fragmentación en 7 grupos).
2. **Corrección Ortotipográfica de Razas:** Reemplazar `Hounstein` $\to$ `Holstein` y `Normanda` $\to$ `Normando`.
3. **Decisión sobre Conductividad Faltante:** Confirmar la estrategia de imputación (mediana por grupo/hato vs mediana global) para los 7 registros de Finca 6.

---

### Etapa 2: Reparación de Rutas y Ejecución del Entrenamiento Real
1. **Normalización de Paths en `main.py` y `src/models/`:**
   - Asegurar que todas las rutas a `artifacts/`, `demo_reports/` y datasets utilicen rutas absolutas ancladas a `PROJECT_ROOT`.
   - Implementar `sys.path.insert(0, ...)` en los módulos de modelos para permitir tanto ejecución modular como scripts directos.
2. **Optimización de Hiperparámetros:** Ajustar el grid de hiperparámetros para que `GroupKFold` anidado concluya de forma ágil y robusta.
3. **Entrenamiento y Persistencia Real:**
   - Ejecutar `main.py` con el CSV real curado.
   - Generar y persistir los artefactos en `src/data/artifacts/`:
     - `mastitis_decision_tree_pipeline.pkl`
     - `mastitis_random_forest_pipeline.pkl`
     - `mastitis_logistic_regression_pipeline.pkl`
   - Generar matrices de confusión y diagramas en `demo_reports/`.

---

### Etapa 3: Migración del Jupyter Notebook (`Model_Analysis_and_Testing.ipynb`)
1. **Eliminar Dependencia de Dummy Data:** Sustituir la llamada a `dummyDataGenerator.py` por la carga y preprocesamiento de `datos_entrenamiento_mastitis-v3.csv`.
2. **Visualizaciones con Datos Reales:**
   - Gráficas de caja: Conductividad vs Mastitis, pH vs Mastitis, Volumen de leche vs Mastitis (evidenciando la caída real de producción).
   - Matriz de correlación anotada con Seaborn.
3. **Evaluación de Modelos Guardados:** Cargar los pipelines `.pkl` reales y mostrar el reporte de clasificación cruzada por finca.

---

### Etapa 4: Finalización del Artículo Académico (`artículo.md`)
1. **Consolidación de Métricas:** Incorporar en las secciones metodológica y de resultados del anteproyecto las métricas de rendimiento reales ($F_1$-score, Sensibilidad/Recall, Precisión, Balanced Accuracy y ROC-AUC).
2. **Interpretación Clínica y Zootécnica:** Exponer las reglas de decisión del árbol final (`arbol_decision_mastitis.png`) y la importancia de variables del Random Forest en el contexto ganadero de Sora (Boyacá) y la Sabana de Bogotá.
3. **Cierre de Brechas Teóricas:** Actualizar la discusión respecto a la merma de volumen de leche observada empíricamente en contraste con las pruebas sintéticas preliminares.

---

## 🔗 Enlaces Relacionados
- [[CORE DEL PROYECTO]]
- [[Análisis Profundo del Dataset y Nuevos Datos]]
- [[Diagnóstico de Rutas y Fallos en Modelos]]
- [[Contexto Ahorro de Tokens para IAs]]