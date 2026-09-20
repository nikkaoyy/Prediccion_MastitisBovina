# CORE DEL PROYECTO: Predicción de Mastitis Subclínica Bovina

> **Estándar:** CRISP-ML(Q) (*Cross-Industry Standard Process for Machine Learning with Quality Assurance*)  
> **Ámbito Geográfico:** Hatos lecheros especializados de Cundinamarca y la Sabana de Bogotá (Sora, Boyacá / Altiplano Cundiboyacense)  
> **Investigadores:** Nicolás Martínez Pineda, Laura Sofía Moreno Suárez, Daniel David Leal Lara  
> **Dirección Académica:** Carlos Andrés Martínez Alayón — *Universidad Distrital Francisco José de Caldas* (2026)  
> **Objetivo:** Detección temprana y clasificación de riesgo de mastitis subclínica bovina mediante aprendizaje automático interpretable y libre de fuga de datos (*Data Leakage*).

---

## 🗺️ Mapa de Contenidos (MOC) de la Bóveda

Esta bóveda de Obsidian está estructurada de manera modular y atómica para optimizar la navegación de agentes de IA y desarrolladores, **minimizando el consumo de tokens** sin perder profundidad técnica o biológica:

1. **[[Análisis Profundo del Dataset y Nuevos Datos]]**  
   Auditoría exploratoria y estadística completa de datos_entrenamiento_mastitis-v3.csv (208 registros, 14 variables). Incluye el desglose pormenorizado de las **7 nuevas filas agregadas** (Finca 6), detección de inconsistencias léxicas, valores nulos sistemáticos, correlaciones biológicas (conductividad, pH, volumen) y desacreditación empírica de hipótesis previas sobre el volumen de leche.

2. **[[Diagnóstico de Rutas y Fallos en Modelos]]**  
   *Testigo técnico formal* y análisis exhaustivo de los problemas de ejecución en src/models/ (DecisionTreeTraining.py, RandomForest.py, LogisticalRegresion.py). Detalla el origen del error ModuleNotFoundError: No module named 'src', la ambigüedad de rutas relativas frente a PROJECT_ROOT, la divergencia en el kernel de Jupyter (Model_Analysis_and_Testing.ipynb), el cuello de botella computacional en GridSearchCV anidado y la solución recomendada.

3. **[[Arquitectura CRISP-ML(Q) y Pipelines]]**  
   Diseño de ingeniería del software y flujo de Machine Learning. Descripción de la validación contractual (DataValidator), preprocesamiento desacoplado sin fuga de datos (FeaturePipelineBuilder), y la justificación metodológica de la validación cruzada por fincas (GroupKFold).

4. **[[Contexto Ahorro de Tokens para IAs]]**  
   Hoja de referencia ultra-condensada (< 800 tokens) para que futuras instancias de IA comprendan el repositorio en un solo vistazo: estructura de archivos, contratos de datos, comandos operativos y trampas conocidas.

5. **[[Hoja de Ruta y Próximos Pasos]]**  
   Plan de transición hacia la siguiente fase de desarrollo: curación y limpieza del CSV real, reestructuración de rutas, entrenamiento y persistencia de modelos reales, actualización del notebook Model_Analysis_and_Testing.ipynb (sustituyendo dummy data) y finalización del artículo científico y anteproyecto de grado.

6. **[[Diagnóstico Dummy Data vs Datos Reales]]**  
   Análisis exhaustivo de por qué los modelos entrenados con datos reales producen ~51% accuracy al evaluarse con dummy data generado por `dummyDataGenerator.py`. Explica la incompatibilidad distribucional (conductividad y pH no correlacionados en el generador sintético), la inversión del volumen de leche, la limitación económica de los medidores de conductividad eléctrica para pequeños productores del Altiplano Cundiboyacense, y las recomendaciones para trabajos futuros (conductividad relativa inter-cuartos, SCC, series temporales, modelo reducido sin equipos).

---

## 📊 Estado Actual del Proyecto (Semáforo de Progreso)

| Componente | Estado | Detalle Operativo |
| :--- | :---: | :--- |
| **Ingesta de Datos (data/raw)** | ⚠️ **En Revisión** | Dataset v3 con 208 filas. Contiene 7 registros nuevos de Finca 6 con valores nulos en conductividad y disparidad en tipografía (inca_6 vs Finca_6, Hounstein, Normanda). |
| **Validador de Datos (src/data)** | ✅ **Completado** | DataValidator audita tipos, rangos fisiológicos y columnas obligatorias. Requiere normalización de fincas y manejo de nulos en conductividad. |
| **Ingeniería de Features (src/data)** | ✅ **Completado** | FeaturePipelineBuilder con imputación mediana, escalado estándar y OneHotEncoder con manejo de categorías desconocidas. |
| **Módulos de Entrenamiento (src/models)** | ✅ **Completado** | Los scripts no se pueden ejecutar de forma aislada desde src/models/ debido a problemas de sys.path y rutas relativas. |
| **Notebook de Experimentación (
otebooks)** | ✅ **Completado** | Model_Analysis_and_Testing.ipynb actualmente opera con dummyDataGenerator.py. Próximo paso: migrar a datos reales. |
| **Documento Académico (rtículo.md)** | ✅ **Completado** | Protocolo completo estructurado. Pendiente incorporar métricas reales obtenidas del entrenamiento del dataset v3 curado. |

---

## 🧬 Resumen Bio-Técnico Clave

- **Variable Objetivo:** mastitis (0 = Sana, 1 = Mastitis Subclínica / Positiva a CMT).
- **Biomarcadores Primarios:** 
  - conductividad_leche_ms_cm: Correlación $+0.917$ con mastitis (filtración de ^+$ y ^-$ por daño epitelial).
  - ph_leche: Correlación $+0.851$ (desplazamiento alcalino de 6.6 hacia 7.0+).
- **Relación Volumen vs Mastitis:** Confirmada reducción productiva en vacas enfermas (Media: .76\text{ L}$ en mastitis vs .28\text{ L}$ en sanas, correlación $-0.385$).
- **Variables No Informativas:** recuencia_de_ordeno ($\\sigma = 0$, constante en 2) y estado_de_vacunacion ($\\sigma = 0$, constante en 0).

---

## 🔗 Enlaces Relacionados
- [[Análisis Profundo del Dataset y Nuevos Datos]]
- [[Diagnóstico de Rutas y Fallos en Modelos]]
- [[Arquitectura CRISP-ML(Q) y Pipelines]]
- [[Contexto Ahorro de Tokens para IAs]]
- [[Hoja de Ruta y Próximos Pasos]]
- [[Diagnóstico Dummy Data vs Datos Reales]]