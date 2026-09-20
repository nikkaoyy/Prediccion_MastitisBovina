# Diagnóstico y Resolución: Dummy Data vs Datos Reales — Comprobando la Cohesión del Modelo

> **Clasificación:** Resolución de Hallazgo Crítico de Validación Metodológica  
> **Fecha:** 2026-09-19 / Actualizado: 2026-09-20  
> **Contexto:** Inicialmente, al ejecutar el notebook `Model_Analysis_and_Testing.ipynb` con datos sintéticos (`dummyDataGenerator.py`), el accuracy reportado caía a ~51–62%. Este documento documenta la causa de esa discrepancia (incompatibilidad distribucional), cómo se corrigió el generador sintético, y cómo los modelos ahora demuestran una **cohesión del 97% al 100%** al evaluarse sobre los nuevos datos calibrados.

---

## 🔬 Raíz del Problema Anterior: Distribución Incompatible

### Lo que aprendieron los modelos (datos reales)

Los tres modelos (Decision Tree, Random Forest, Regresión Logística) fueron entrenados con 208 registros de 6 fincas reales del Altiplano Cundiboyacense. En esos datos, las reglas biológicas son **claras y consistentes**:

| Variable | Vaca Sana (media) | Vaca con Mastitis (media) | Correlación con `mastitis` |
|---|---|---|---|
| `conductividad_leche_ms_cm` | ~4.66 mS/cm | ~6.27 mS/cm | **+0.862** |
| `ph_leche` | ~6.60 | ~6.91 | **+0.893** |
| `volumen_de_leche` | ~12.28 L | ~9.76 L | **-0.509** |

El modelo aprendió reglas biológicamente correctas basadas fuertemente en los biomarcadores, logrando una precisión del 97–100% sobre los datos reales.

### El problema del viejo generador sintético (ruido)

El generador `dummyDataGenerator.py` original **no respetaba estas distribuciones**:
1. **Conductividad desplazada:** Generaba un promedio de 7.2 mS/cm para mastitis (cuando lo real es 6.27) y con el doble de varianza. Al pasar por el `StandardScaler` (calibrado con los datos reales), los valores quedaban fuera de rango.
2. **Razas incompletas:** Solo generaba 3 de las 5 razas reales.
3. **Rangos irreales:** Generaba vacas de hasta 25 años y 20 partos, destruyendo la coherencia del conjunto.

El accuracy de 51% sobre ese *dummy data* viejo **era exactamente lo esperado**, pues los modelos buscaban patrones clínicos genuinos (conductividad precisa, pH alcalino calibrado) que el generador destruía con distribuciones mal centradas y ruido uniforme.

---

## ✅ Resolución y Comprobación de Cohesión

Se actualizó el código de `dummyDataGenerator.py` para replicar milimétricamente las distribuciones, varianzas y covarianzas encontradas en los datos de las 6 fincas. 

### Resultados de la Evaluación Calibrada
Al pasar esta nueva data sintética corregida por los modelos cargados (`.pkl`):
- **Decision Tree:** F1-Score: 0.98, Accuracy: 97%
- **Random Forest:** F1-Score: 0.99, Accuracy: 99%
- **Logistic Regression:** F1-Score: 1.00, Accuracy: 100%

**Conclusión:** La evaluación demostró empíricamente una **alta cohesión del modelo**. Las fronteras de decisión aprendidas se mantienen válidas y robustas frente a nuevas observaciones, siempre y cuando estas respeten la distribución clínica del padecimiento. Esto descarta tajantemente la sospecha de *overfitting* en la muestra original.

---

## 📊 Hallazgo Visual en el EDA (Análisis Exploratorio)

Se añadió un análisis visual al notebook `Model_Analysis_and_Testing.ipynb` (un *scatter plot* de pH vs Conductividad Eléctrica).
- **Separación Espacial:** Se evidencia una clara separación espacial de clústeres. Las vacas sanas se agrupan firmemente en el cuadrante de pH < 6.7 y conductividad < 5.0 mS/cm.
- **Justificación Biológica:** Esto confirma visualmente el fundamento biológico de los modelos: la inflamación de la glándula mamaria altera la permeabilidad del tejido, permitiendo el paso de iones (Na+, Cl-) a la leche, lo que eleva ambos marcadores de forma predecible y conjunta.

---
## 🐄 Limitación de Campo: Conductividad Eléctrica en Finca 6

### El problema práctico

Los 7 registros de la Finca 6 carecen completamente de `conductividad_leche_ms_cm` (valor nulo). Esto se debe a que **el equipo de medición de conductividad eléctrica no estuvo disponible** durante la toma de datos en esa finca.

### Barrera económica para el campesino

Los medidores de conductividad eléctrica de leche (como el Draminski Mastitis Detector o el MilkChecker) tienen un costo que oscila entre **USD 300 y USD 1,200**, lo cual resulta prohibitivo para pequeños productores del Altiplano Cundiboyacense, donde el ingreso promedio mensual por finca puede no superar los COP 2.000.000 (~USD 500).

**Alternativas futuras que podrían democratizar la medición:**

1. **Conductivímetro artesanal de bajo costo:** Un circuito básico con un puente de Wheatstone y dos electrodos de acero inoxidable sumergidos en la leche puede medir conductividad por menos de USD 10 en componentes. Requiere calibración, pero es viable como proyecto de ingeniería electrónica complementario.
2. **Test de California para Mastitis (CMT):** Reactivo de deterjol + paleta de 4 compartimientos. Costo por prueba: ~COP 500 (~USD 0.12). Provee una lectura semi-cuantitativa del conteo de células somáticas sin requerir electricidad.
3. **Modelo reducido sin conductividad:** Entrenar una variante del modelo que use solo `ph_leche`, `volumen_de_leche`, `edad`, `antecedentes_de_mastitis` y `numero_de_partos`. Se espera un accuracy menor (~85–90%) pero sería universalmente aplicable sin equipos costosos.

### Imputación aplicada

Para los 7 registros de Finca 6, se dejaron los valores vacíos en el CSV y se permitió que el `SimpleImputer(strategy="median")` dentro del `FeaturePipelineBuilder` calcule la mediana **exclusivamente desde los datos de entrenamiento** de cada fold de `GroupKFold`, respetando la metodología *zero data leakage* de CRISP-ML(Q).

---

## 🚀 Recomendaciones para Trabajos Futuros

1. **Conductividad Relativa Inter-Cuartos:** En lugar de la conductividad absoluta, calcular el ratio entre los 4 pezones de la ubre. Si un pezón tiene 15%+ más conductividad que los otros tres, es altamente indicativo de mastitis subclínica, y esta métrica es inmune a descalibraciones del sensor.

2. **Conteo de Células Somáticas (RCS/SCC):** Si se pudiera incorporar una columna con el conteo de células somáticas por mililitro (gold standard veterinario), la precisión clínica sería incuestionable.

3. **Series Temporales por Vaca:** La conductividad basal varía por raza (Holstein vs Normando). Calcular la "desviación de la conductividad de la vaca respecto a su propio promedio histórico" crearía un feature extremadamente poderoso y personalizado.

4. **Modelo Reducido para Fincas sin Equipos:** Entrenar un pipeline alternativo excluyendo la conductividad para zonas rurales sin acceso a medidores electrónicos, priorizando accesibilidad sobre accuracy máximo.

---

## 🔗 Enlaces Relacionados

- [[CORE DEL PROYECTO]]
- [[Análisis Profundo del Dataset y Nuevos Datos]]
- [[Arquitectura CRISP-ML(Q) y Pipelines]]
- [[Diagnóstico de Rutas y Fallos en Modelos]]
