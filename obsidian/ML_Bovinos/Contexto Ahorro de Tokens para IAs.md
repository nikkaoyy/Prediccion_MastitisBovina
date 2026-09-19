# Contexto Ahorro de Tokens para IAs

> **Propósito:** Esta nota condensa todo el contexto técnico, contratos y trampas del repositorio en formato de alta densidad para que cualquier agente de IA pueda entender el proyecto en **< 800 tokens**, evitando lecturas costosas de código fuente.

---

## 📌 Resumen de una Línea
Sistema de Machine Learning bajo CRISP-ML(Q) para clasificar mastitis subclínica en vacas lecheras de Cundinamarca/Boyacá usando `GroupKFold` por finca, árbol de decisión, Random Forest y Regresión Logística.

---

## 📂 Mapa de Archivos Clave
- `data/raw/datos_entrenamiento_mastitis-v3.csv`: Dataset real (208 filas, 14 cols, Fincas 1 a 6).
- `src/data/dataValidation.py`: Clase `DataValidator`. Valida tipos, rangos clínicos y grupos.
- `src/data/featureEngineer.py`: Clase `FeaturePipelineBuilder`. `StandardScaler` + `OneHotEncoder` + `SimpleImputer`.
- `src/models/DecisionTreeTraining.py`: Clase `DecisionTreeModelTrainer`. GridSearch con GroupKFold anidado.
- `src/models/RandomForest.py`: Clase `RandomForestModelTrainer`.
- `src/models/LogisticalRegresion.py`: Clase `LogisticRegressionModelTrainer`.
- `main.py`: Orquestador principal que ejecuta validación, entrenamiento de los 3 modelos y guarda reportes.
- `notebooks/Model_Analysis_and_Testing.ipynb`: Notebook de testeo (actualmente con dummy data, migrando a real).
- `artículo.md`: Documento académico completo del anteproyecto de grado (Univ. Distrital, 2026).
- `obsidian/ML_Bovinos/`: Bóveda con la documentación viva del proyecto.

---

## 📋 Contrato de Datos (`DataValidator.FEATURE_COLUMNS`)
- **Numéricas Continuas:** `volumen_de_leche`, `humedad`, `temperatura`, `ph_leche`, `conductividad_leche_ms_cm`.
- **Numéricas Discretas/Ordinales:** `edad`, `numero_de_partos`.
- **Binarias (0/1):** `etapa_de_lactancia`, `frecuencia_de_ordeno` (constante 2), `estado_de_vacunacion` (constante 0), `antecedentes_de_mastitis`.
- **Categórica:** `raza` (Holstein, Normando, Jersey, Pardo_Suizo, Cruzado).
- **Grupo:** `finca` (Finca_1 a Finca_6).
- **Target:** `mastitis` (0 = Sana, 1 = Positiva a CMT).

---

## ⚠️ Trampas Conocidas y Reglas de Oro para IAs
1. **NO ejecutes `python src/models/*.py` directamente:** Fallará con `ModuleNotFoundError: No module named 'src'`.
2. **Ejecuta siempre desde la raíz:** Usa `python main.py` o añade `sys.path.insert(0, str(PROJECT_ROOT))`.
3. **Cuidado con Finca 6 en el CSV:** Tiene errores ortotipográficos (`finca_6` minúscula, `Hounstein`, `Normanda`) y 7 nulos en conductividad.
4. **Finca 6 tiene 0 casos positivos:** Provoca advertencias en `f1_score` cuando queda como fold de test único.
5. **No asumas que mastitis aumenta la leche:** En los datos reales, las vacas con mastitis dan $-20.5\%$ menos leche ($9.76\text{ L}$ vs $12.28\text{ L}$).

---

## 🔗 Enlaces Relacionados
- [[CORE DEL PROYECTO]]
- [[Análisis Profundo del Dataset y Nuevos Datos]]
- [[Diagnóstico de Rutas y Fallos en Modelos]]
- [[Hoja de Ruta y Próximos Pasos]]