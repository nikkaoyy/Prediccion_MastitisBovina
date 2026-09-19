# Análisis Profundo del Dataset y Nuevos Datos

> **Archivo Fuente:** `data/raw/datos_entrenamiento_mastitis-v3.csv`  
> **Dimensiones:** 208 observaciones × 14 variables  
> **Objetivo Clínico:** Detección de mastitis subclínica (positividad en reactivo CMT)  
> **Estado de Calidad:** Requiere normalización léxica y manejo de nulos en lote Finca 6.

---

## 1. Auditoría del Lote Recién Agregado (Finca 6)

En la última actualización del archivo CSV (commit `4a7765d`), se incorporaron **7 nuevas observaciones** correspondientes a una sexta unidad productiva (Finca 6). La inspección profunda revela hallazgos críticos de calidad de datos que impactan directamente el preprocesamiento y la validación cruzada:

```csv
Finca_6,5,Normanda,3,18,1,2,0,0,45,17,6.71,,0
finca_6,4,Hounstein,2,10,0,2,0,0,45,17,6.52,,0
finca_6,12,Normanda,7,20,0,2,0,1,45,17,6.68,,0
finca_6,7,Normanda,3,12,0,2,0,1,45,16,6.54,,0
finca_6,6,Hounstein,3,8,0,2,0,0,45,16,6.1,,0
finca_6,7,Hounstein,3,10.5,0,2,0,0,45,16,6.28,,0
finca_6,4,Hounstein,1,12,0,2,0,0,45,16,6.41,,0
```

### Hallazgos Críticos en los Nuevos Datos:
1. **Inconsistencia de Mayúsculas/Minúsculas en Identificador de Finca:**
   - Se observa 1 registro rotulado como `Finca_6` y 6 registros como `finca_6`.
   - **Impacto:** `DataValidator` y `GroupKFold` detectan **7 fincas únicas** en lugar de 6. Al tratar a `Finca_6` como un grupo independiente de 1 sola vaca, los algoritmos de partición por grupos fallan o generan pliegues degenerados.
   - **Acción Requerida:** Homogeneizar con `.str.capitalize()` o asignación directa a `Finca_6`.

2. **Corrupción Ortotipográfica en Razas:**
   - `Hounstein` (4 casos): Error ortográfico por `Holstein`.
   - `Normanda` (3 casos): Variante dialectal por `Normando`.
   - **Impacto:** Si no se corrigen, el `OneHotEncoder` creará dos columnas sintéticas adicionales (`raza_Hounstein`, `raza_Normanda`), fragmentando la varianza y provocando columnas espurias durante la inferencia en producción.

3. **Ausencia Sistemática de Conductividad Eléctrica:**
   - En las 7 filas, la columna `conductividad_leche_ms_cm` está vacía (`6.71,,0`).
   - El dataset total tiene exactamente **7 valores nulos**, todos concentrados en este nuevo lote.
   - **Impacto:** Dado que la conductividad es el biomarcador predictivo más potente ($r = 0.917$), una imputación simple (como mediana de todo el dataset) podría subestimar o alterar la distribución de esta finca. Sin embargo, el `FeaturePipelineBuilder` actual usa `SimpleImputer(strategy="median")`, lo que permite procesarlas sin error sintáctico pero exige cautela analítica.

4. **Homogeneidad Total de Clase (100% Sanas):**
   - Las 7 observaciones tienen `mastitis = 0`.
   - **Impacto Matemático en GroupKFold:** Cuando el fold de prueba toma a la Finca 6 aislada, $y_{true} = [0, 0, 0, 0, 0, 0, 0]$. Al no existir ningún caso positivo ($1$), la métrica $F_1$ no puede calcularse (división por cero), arrojando:
     `UndefinedMetricWarning: F-score is ill-defined and being set to 0.0 due to no true nor predicted samples`.
   - Además, durante el tuning interno de `GridSearchCV`, esto castiga artificialmente los hiperparámetros.

5. **Disparidad Micro-Climática Marcada:**
   - Humedad: $45.0\%$ en todas las filas de Finca 6, en contraste con el promedio de las Fincas 1 a 5 ($73.4\%$, rango $65\% - 91.8\%$).
   - Temperatura: $16 - 17^\circ\text{C}$ (más cálido y seco que los hatos de páramo).

---

## 2. Métricas Estadísticas Globales del Dataset

Tras la unión de los lotes, la distribución poblacional queda de la siguiente manera:

| Variable | Tipo | Conteo | Media / Moda | Desv. Est. | Mín | Mediana | Máx |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **finca** | Categórica (Grupo) | 208 | Finca_1 a 4 (41 c/u) | — | — | — | 7 grupos actuales |
| **edad** | Numérica (Años) | 208 | 5.49 años | 1.64 | 3.0 | 5.0 | 12.0 |
| **raza** | Categórica | 208 | Holstein (127 corregido) | — | — | — | 5 razas reales |
| **numero_de_partos** | Discreta | 208 | 2.84 partos | 1.56 | 1.0 | 3.0 | 10.0 |
| **volumen_de_leche** | Continua (L/día) | 208 | 10.94 L | 3.27 | 3.77 | 10.98 | 23.40 |
| **etapa_de_lactancia**| Binaria (0: Temprana, 1: Tardía) | 208 | 0.50 (50.5% en 1) | 0.50 | 0.0 | 1.0 | 1.0 |
| **frecuencia_de_ordeno**| Discreta | 208 | **2.00 (Varianza Cero)** | 0.00 | 2.0 | 2.0 | 2.0 |
| **estado_de_vacunacion**| Binaria | 208 | **0.00 (Varianza Cero)** | 0.00 | 0.0 | 0.0 | 0.0 |
| **antecedentes_de_mastitis**| Binaria | 208 | 0.45 (44.7% positivos) | 0.50 | 0.0 | 0.0 | 1.0 |
| **humedad** | Continua (% HR) | 208 | 72.50% | 8.09 | 45.0 | 72.8 | 91.8 |
| **temperatura** | Continua (°C) | 208 | 12.77 °C | 4.17 | -2.90 | 13.9 | 17.0 |
| **ph_leche** | Continua | 208 | 6.77 | 0.19 | 6.10 | 6.75 | 7.18 |
| **conductividad_leche_ms_cm**| Continua (mS/cm) | 201 | 5.55 mS/cm | 0.88 | 4.15 | 5.70 | 7.60 |
| **mastitis (Target)**| Binaria (0 / 1) | 208 | 0.534 (53.4% Mastitis) | 0.50 | 0.0 | 1.0 | 1.0 |

---

## 3. Jerarquía de Correlación y Justificación Fisiopatológica

El análisis de correlación de Pearson con respecto a la variable objetivo `mastitis` revela la jerarquía de predicción:

```
1. conductividad_leche_ms_cm   +0.9171  (Asociación Crítica Primaria)
2. ph_leche                    +0.8509  (Asociación Crítica Secundaria)
3. antecedentes_de_mastitis    +0.4336  (Factor de Riesgo Crónico)
4. volumen_de_leche            -0.3851  (Pérdida de Rendimiento Productivo)
5. numero_de_partos            +0.3140  (Factor de Desgaste Anatomofisiológico)
6. edad                        +0.3066  (Senescencia e Inmunocompetencia)
7. humedad                     +0.1746  (Presión Ambiental de Patógenos)
8. etapa_de_lactancia          +0.1536  (Fase Fisiológica)
9. temperatura                 -0.0726  (Baja correlación lineal directa)
10. frecuencia_de_ordeno        NaN     (Constante = 2, sin aporte predictivo)
11. estado_de_vacunacion        NaN     (Constante = 0, sin aporte predictivo)
```

### Desglose Fisiológico:
1. **Conductividad Eléctrica ($r = +0.917$):**
   - En una ubre sana, las uniones estrechas (*tight junctions*) entre las células epiteliales glandulares impiden el paso libre de iones desde la sangre.
   - Cuando colonizan bacterias mastitogénicas (*S. aureus*, *E. coli*, *S. agalactiae*), la respuesta inflamatoria destruye la integridad del epitelio mamario.
   - Hay una trasudación masiva de iones sodio ($Na^+$) y cloro ($Cl^-$) desde el líquido extracelular y capilar hacia la leche alveolar, mientras el potasio ($K^+$) disminuye.
   - Este incremento en electrolitos libres dispara la conductividad eléctrica de $\sim 4.5\text{ mS/cm}$ a más de $6.0 - 7.5\text{ mS/cm}$.
2. **pH de la Leche ($r = +0.851$):**
   - La leche normal es ligeramente ácida a neutra ($6.5 - 6.7$).
   - Con la inflamación e infiltración de bicarbonato y plasma sanguíneo (pH $\approx 7.4$), el pH de la leche se alcaliniza ($> 6.8$ hasta $7.2$).
3. **El Hallazgo del Volumen de Leche: Desmitificando Supuestos Previos ($r = -0.385$):**
   - En prototipos anteriores y en el notebook con *dummy data*, se asumía erróneamente que las vacas con mastitis tenían más volumen.
   - **Los datos reales demuestran lo contrario:**
     - Vacas sanas: **$12.28\text{ L/día}$** (rango $6.20 - 20.00\text{ L}$).
     - Vacas con mastitis: **$9.76\text{ L/día}$** (rango $3.77 - 23.40\text{ L}$).
   - Hay una caída neta de producción de **$2.52\text{ L/vaca/día}$** ($-20.5\%$ de pérdida de leche), lo que coincide exactamente con el impacto zootécnico reportado en la literatura internacional.
4. **Variables Huérfanas de Varianza:**
   - `frecuencia_de_ordeno` (todas en 2 ordeños diarios) y `estado_de_vacunacion` (todas en 0, no vacunadas) no aportan información para distinguir sanas de enfermas. Se recomienda conservarlas únicamente si se planea alimentar el sistema con hatos de 3 ordeños o que apliquen biológicos preventivos en el futuro.
5. **Temperatura Extrema ($-2.9^\circ\text{C}$):**
   - Registrada en Finca 5. Corresponde a heladas nocturnas frecuentes en la Sabana de Bogotá y el Altiplano Cundiboyacense durante temporadas secas. El frío extremo estresa los esfínteres del pezón (*ductus papillaris*), aumentando la susceptibilidad a infecciones ambientales.

---

## 4. Distribución por Hatos Lecheros (Fincas)

| Finca | N° Vacas | Vacas Sanas (0) | Con Mastitis (1) | Prevalencia (%) | Observaciones |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Finca_1** | 41 | 17 | 24 | 58.5% | Alta prevalencia, raza Normando preponderante |
| **Finca_2** | 41 | 16 | 25 | 61.0% | Mayor prevalencia del estudio |
| **Finca_3** | 41 | 16 | 25 | 61.0% | Mayor prevalencia del estudio |
| **Finca_4** | 41 | 22 | 19 | 46.3% | Hato con mejor control higiénico |
| **Finca_5** | 37 | 19 | 18 | 48.6% | Registra temperaturas mínimas (-2.9 °C) |
| **Finca_6** | 7 | 7 | 0 | 0.0% | Lote nuevo. Cero positivos. Nulos en conductividad |

---

## 🔗 Enlaces Relacionados
- [[CORE DEL PROYECTO]]
- [[Diagnóstico de Rutas y Fallos en Modelos]]
- [[Arquitectura CRISP-ML(Q) y Pipelines]]
- [[Hoja de Ruta y Próximos Pasos]]