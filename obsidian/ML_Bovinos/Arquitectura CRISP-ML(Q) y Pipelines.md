# Arquitectura CRISP-ML(Q) y Pipelines

> **Metodología:** CRISP-ML(Q) (*Cross-Industry Standard Process for Machine Learning with Quality Assurance*)  
> **Garantía de Calidad:** Prevención estricta de *Data Leakage* y reproducibilidad experimental.

---

## 📐 Fases CRISP-ML(Q) Implementadas en el Repositorio

El diseño del software sigue las cuatro fases operativas de CRISP-ML(Q):

```
+-------------------------------------------------------------+
| 1. Comprensión del Negocio y los Datos                      |
|    - Mastitis subclínica en hatos lecheros                  |
|    - Dataset tabular con 14 variables (clínicas y clima)    |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| 2. Ingeniería de Datos y Aseguramiento de Calidad           |
|    - src/data/dataValidation.py  -> DataValidator           |
|    - src/data/featureEngineer.py -> FeaturePipelineBuilder  |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| 3. Modelado y Validación Robusta                            |
|    - GroupKFold anidado por Finca (Cero Data Leakage)       |
|    - Modelos: Decision Tree, Random Forest, Reg. Logística  |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| 4. Evaluación, Empaquetado y Persistencia                   |
|    - Serialización de Pipelines completos (*.pkl)           |
|    - Reportes auditables (Matrices de confusión y JSON)     |
+-------------------------------------------------------------+
```

---

## 🛡️ Control de Calidad de Datos (`DataValidator`)

Ubicado en `src/data/dataValidation.py`. Establece un **contrato estricto** antes de permitir que cualquier dato toque los algoritmos de Machine Learning:

- **Validación de Esquema:** Verifica la presencia de las 14 columnas estructurales.
- **Coerción Numérica Segura:** Detecta separadores decimales latinoamericanos (comas por puntos) y espacios de no separación (`\u00a0`). Si hay texto no numérico no recuperable, lanza `DataValidationError`.
- **Rangos Clínicos:** 
  - `edad`: $[1.0, 25.0]$ años
  - `numero_de_partos`: $[0.0, 20.0]$
  - `volumen_de_leche`: $[0.0, 100.0]	ext{ L}$
  - `humedad`: $[0.0, 100.0]\%$
  - `temperatura`: $[-20.0, 50.0]^\circ	ext{C}$
  - `ph_leche`: $[5.5, 8.0]$
  - `conductividad_leche_ms_cm`: $[2.0, 15.0]	ext{ mS/cm}$
- **Valores Permitidos:** Exige que variables binarias y discretas pertenezcan a los conjuntos válidos (`etapa_de_lactancia` $\in \{0, 1\}$, `frecuencia_de_ordeno` $\in \{2\}$, etc.).

---

## ⚙️ Preprocesamiento Desacoplado (`FeaturePipelineBuilder`)

Ubicado en `src/data/featureEngineer.py`. Garantiza la ausencia total de fuga de información entre entrenamiento y prueba:

- **Rama Numérica:**
  - `SimpleImputer(strategy="median")`: Imputa nulos usando únicamente la mediana del conjunto de entrenamiento de cada pliegue.
  - `StandardScaler()`: Normaliza a media 0 y varianza 1.
- **Rama Categórica:**
  - `SimpleImputer(strategy="most_frequent")`: Imputa valores faltantes con la moda.
  - `OneHotEncoder(handle_unknown="ignore", sparse_output=False)`: Codifica razas sin colapsar si en producción aparece una raza desconocida.
- **Pipeline Integral:** Encapsula el `ColumnTransformer` junto al estimador clasificador, asegurando que cualquier transformación se ajuste *exclusivamente* con datos de entrenamiento.

---

## 🚜 Protocolo de Validación: `GroupKFold` por Hato

En la industria ganadera, los animales de una misma finca comparten:
1. Prácticas de higiene del ordeñador y mantenimiento de pezoneras.
2. Cepa bacteriana endémica en el establo.
3. Tipo de pastoreo, suplementación mineral y condiciones microclimáticas.

Si se utilizara una partición aleatoria estándar (`train_test_split` o `KFold` tradicional), registros de vacas de la misma finca quedarían en entrenamiento y prueba simultáneamente, generando **fuga de datos por correlación de grupo** y métricas falsamente optimistas.

**La Solución Implementada:**  
Se utiliza `GroupKFold(n_splits=5)` agrupando estrictamente por la columna `finca`. De esta forma, el modelo es evaluado en fincas completas que **nunca vio durante el entrenamiento**, simulando con fidelidad su despliegue real en un nuevo hato de la Sabana de Bogotá o Boyacá.

---

## 🔗 Enlaces Relacionados
- [[CORE DEL PROYECTO]]
- [[Análisis Profundo del Dataset y Nuevos Datos]]
- [[Diagnóstico de Rutas y Fallos en Modelos]]
- [[Hoja de Ruta y Próximos Pasos]]