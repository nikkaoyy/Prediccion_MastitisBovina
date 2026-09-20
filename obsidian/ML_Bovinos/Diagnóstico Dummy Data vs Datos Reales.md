# Diagnóstico: Dummy Data vs Datos Reales — Por Qué los Modelos "Fallan" al 51%

> **Clasificación:** Hallazgo Crítico de Validación Metodológica  
> **Fecha:** 2026-09-19  
> **Contexto:** Al ejecutar el notebook `Model_Analysis_and_Testing.ipynb` con datos sintéticos (`dummyDataGenerator.py`) sobre los modelos entrenados con el CSV real (`datos_entrenamiento_mastitis-v3.csv`), el accuracy reportado cayó a ~51–62%. Este documento explica por qué esto ocurre, por qué **NO** es un defecto del modelo, y qué implicaciones tiene para la investigación.

---

## 🔬 Raíz del Problema: Distribución Incompatible

### Lo que aprendieron los modelos (datos reales)

Los tres modelos (Decision Tree, Random Forest, Regresión Logística) fueron entrenados con 208 registros de 6 fincas reales del Altiplano Cundiboyacense. En esos datos, las reglas biológicas son **claras y consistentes**:

| Variable | Vaca Sana (media) | Vaca con Mastitis (media) | Correlación con `mastitis` |
|---|---|---|---|
| `conductividad_leche_ms_cm` | ~4.5 mS/cm | ~7.2 mS/cm | **+0.917** |
| `ph_leche` | ~6.55 | ~6.95 | **+0.851** |
| `volumen_de_leche` | ~12.28 L | ~9.76 L | **-0.385** |

El modelo aprendió: **"Si conductividad > 6.5 y pH > 6.8 → Mastitis"**. Esta regla es biológicamente correcta y funciona con precisión del 97–100% sobre los datos reales.

### Lo que genera el dummy data (ruido aleatorio)

El generador `dummyDataGenerator.py` (líneas 33–41) **NO usa la conductividad ni el pH** para determinar la variable `mastitis`. En su lugar, calcula la probabilidad de mastitis así:

```python
mastitis_prob = (
    (df["edad"] > 8).astype(float) * 0.2 +
    (df["antecedentes_de_mastitis"] == 1).astype(float) * 0.3 + 
    (df["volumen_de_leche"] > 25).astype(float) * 0.3 +  # ← INVERTIDO vs realidad
    (df["estado_de_vacunacion"] == 0).astype(float) * 0.1
) + ruido_aleatorio
```

**Problemas fatales de este generador:**

1. **Conductividad y pH son ruido puro:** Se generan con `np.random.uniform()` sin relación alguna con `mastitis`. El modelo busca la regla "conductividad > 6.5 → Mastitis" y la encuentra **violada en el 50% de los casos** porque el dummy data reparte conductividades altas tanto a sanas como a enfermas al azar.

2. **Volumen de leche invertido:** El generador asigna `volumen > 25 → más mastitis` (peso 0.3), pero en la realidad clínica (y en los datos reales), **la mastitis REDUCE la producción** (9.76L vs 12.28L). El modelo aprendió la regla correcta; el dummy data la contradice.

3. **Desbalance artificial:** Con `n_samples=500` y `random_state=123`, el generador produce 381 "Mastitis" vs 119 "Sana" (76%/24%). Los datos reales tienen 111/97 (53%/47%), un balance mucho más equitativo.

### Resultado: El modelo predice correctamente sobre datos incorrectos

| Modelo | Accuracy (Datos Reales) | Accuracy (Dummy Data) | Explicación |
|---|---|---|---|
| Decision Tree | **100%** | **51%** | Busca conductividad > umbral, pero el dummy la genera al azar |
| Random Forest | **97.1%** | **51%** | Mismo problema, ensemble no puede compensar ruido puro |
| Regresión Logística | **98.5%** | **62%** | Captura señal residual de `antecedentes_de_mastitis` |

> **Conclusión:** Un accuracy de 51% sobre dummy data **es exactamente lo esperado**. Es equivalente a lanzar una moneda. Los modelos están buscando patrones biológicos reales (conductividad, pH) que el generador sintético destruye con ruido uniforme. Esto **NO es overfitting** — es un generador de datos que no respeta la distribución real.

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
