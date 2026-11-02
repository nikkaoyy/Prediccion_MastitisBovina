# Tabla de transparencia de métricas

Generado por `python -m src.models.compare_variants`. No editar a mano.

**Datos:** reales, `datos_entrenamiento_mastitis-v3.csv`, 209 filas, 6 fincas (SHA-256 `a9b38d30ef23`). Ninguna cifra sale de datos sintéticos.

**Validación:** GroupKFold(5) por finca, búsqueda anidada optimizando F1. El preprocesamiento se ajusta dentro de cada pliegue de entrenamiento. Umbral de clasificación 0,5. El promedio y la desviación estándar (DE, muestral, n = 5) son entre pliegues.

**Variables.** Completo (12): las 12 predictoras del conjunto A, con pH y conductividad. Campo (8): `edad`, `raza`, `numero_de_partos`, `volumen_de_leche`, `etapa_de_lactancia`, `frecuencia_de_ordeno`, `estado_de_vacunacion` y `antecedentes_de_mastitis`.

## Modelo completo frente a modelo de campo

| Modelo | Variables | F1 | Precision | Recall | PR-AUC |
|---|---|---|---|---|---|
| Árbol de decisión | Completo (12) | 1,000 ± 0,000 | 1,000 ± 0,000 | 1,000 ± 0,000 | 1,000 ± 0,000 |
| Árbol de decisión | Campo (8) | 0,753 ± 0,076 | 0,762 ± 0,154 | 0,766 ± 0,089 | 0,803 ± 0,115 |
| Random Forest | Completo (12) | 0,981 ± 0,043 | 0,965 ± 0,078 | 1,000 ± 0,000 | 1,000 ± 0,000 |
| Random Forest | Campo (8) | 0,738 ± 0,092 | 0,766 ± 0,114 | 0,736 ± 0,158 | 0,874 ± 0,058 |
| Regresión logística | Completo (12) | 0,982 ± 0,029 | 0,990 ± 0,022 | 0,975 ± 0,056 | 0,997 ± 0,007 |
| Regresión logística | Campo (8) | 0,716 ± 0,121 | 0,737 ± 0,152 | 0,722 ± 0,173 | 0,815 ± 0,100 |

Referencia para PR-AUC: un clasificador sin información obtiene aproximadamente la prevalencia, 0,538 en promedio entre pliegues.

## Resultados por pliegue

- **P1:** Finca_4 (n = 41, prevalencia 46,3 %)
- **P2:** Finca_3 (n = 41, prevalencia 61,0 %)
- **P3:** Finca_2 (n = 41, prevalencia 61,0 %)
- **P4:** Finca_1 (n = 41, prevalencia 58,5 %)
- **P5:** Finca_5 + Finca_6 (n = 45, prevalencia 42,2 %)

| Modelo | Variables | Métrica | P1 | P2 | P3 | P4 | P5 | Promedio | DE |
|---|---|---|---|---|---|---|---|---|---|
| Árbol de decisión | Completo | F1 | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 0,000 |
| Árbol de decisión | Completo | Precision | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 0,000 |
| Árbol de decisión | Completo | Recall | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 0,000 |
| Árbol de decisión | Completo | PR-AUC | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 0,000 |
| Árbol de decisión | Campo | F1 | 0,780 | 0,760 | 0,864 | 0,682 | 0,681 | 0,753 | 0,076 |
| Árbol de decisión | Campo | Precision | 0,727 | 0,760 | 1,000 | 0,750 | 0,571 | 0,762 | 0,154 |
| Árbol de decisión | Campo | Recall | 0,842 | 0,760 | 0,760 | 0,625 | 0,842 | 0,766 | 0,089 |
| Árbol de decisión | Campo | PR-AUC | 0,783 | 0,857 | 0,973 | 0,697 | 0,706 | 0,803 | 0,115 |
| Random Forest | Completo | F1 | 1,000 | 1,000 | 1,000 | 1,000 | 0,905 | 0,981 | 0,043 |
| Random Forest | Completo | Precision | 1,000 | 1,000 | 1,000 | 1,000 | 0,826 | 0,965 | 0,078 |
| Random Forest | Completo | Recall | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 0,000 |
| Random Forest | Completo | PR-AUC | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 0,000 |
| Random Forest | Campo | F1 | 0,762 | 0,650 | 0,851 | 0,638 | 0,791 | 0,738 | 0,092 |
| Random Forest | Campo | Precision | 0,696 | 0,867 | 0,909 | 0,652 | 0,708 | 0,766 | 0,114 |
| Random Forest | Campo | Recall | 0,842 | 0,520 | 0,800 | 0,625 | 0,895 | 0,736 | 0,158 |
| Random Forest | Campo | PR-AUC | 0,853 | 0,897 | 0,963 | 0,822 | 0,833 | 0,874 | 0,058 |
| Regresión logística | Completo | F1 | 1,000 | 1,000 | 1,000 | 0,933 | 0,974 | 0,982 | 0,029 |
| Regresión logística | Completo | Precision | 1,000 | 1,000 | 1,000 | 1,000 | 0,950 | 0,990 | 0,022 |
| Regresión logística | Completo | Recall | 1,000 | 1,000 | 1,000 | 0,875 | 1,000 | 0,975 | 0,056 |
| Regresión logística | Completo | PR-AUC | 1,000 | 1,000 | 1,000 | 0,984 | 1,000 | 0,997 | 0,007 |
| Regresión logística | Campo | F1 | 0,700 | 0,714 | 0,898 | 0,558 | 0,708 | 0,716 | 0,121 |
| Regresión logística | Campo | Precision | 0,667 | 0,882 | 0,917 | 0,632 | 0,586 | 0,737 | 0,152 |
| Regresión logística | Campo | Recall | 0,737 | 0,600 | 0,880 | 0,500 | 0,895 | 0,722 | 0,173 |
| Regresión logística | Campo | PR-AUC | 0,799 | 0,846 | 0,969 | 0,749 | 0,711 | 0,815 | 0,100 |

## Importancia de variables

Permutación sobre la finca de prueba, ΔPR-AUC, 20 repeticiones, promediada entre pliegues y por variable original (`raza` se permuta completa). "Ganó" o "Perdió" compara campo con completo; una diferencia menor que 0,005 se lee como "Sin cambio". Con variables correlacionadas, como pH y conductividad o edad y partos, la permutación reparte la importancia entre ellas y puede subestimar cada una.

### Árbol de decisión

| Variable | Completo | Campo | Lectura |
|---|---|---|---|
| `volumen_de_leche` | 0,000 | 0,180 | Ganó |
| `antecedentes_de_mastitis` | 0,000 | 0,064 | Ganó |
| `numero_de_partos` | 0,000 | 0,045 | Ganó |
| `raza` | 0,000 | 0,023 | Ganó |
| `etapa_de_lactancia` | 0,000 | 0,006 | Ganó |
| `edad` | 0,000 | 0,003 | Sin cambio |
| `estado_de_vacunacion` | 0,000 | 0,000 | Sin cambio |
| `frecuencia_de_ordeno` | 0,000 | 0,000 | Sin cambio |
| `ph_leche` | 0,466 | — | Perdió (excluida) |
| `conductividad_leche_ms_cm` | 0,000 | — | Perdió (excluida) |
| `humedad` | 0,000 | — | Perdió (excluida) |
| `temperatura` | 0,000 | — | Perdió (excluida) |

### Random Forest

| Variable | Completo | Campo | Lectura |
|---|---|---|---|
| `volumen_de_leche` | 0,000 | 0,160 | Ganó |
| `antecedentes_de_mastitis` | 0,000 | 0,048 | Ganó |
| `etapa_de_lactancia` | 0,000 | 0,018 | Ganó |
| `numero_de_partos` | 0,000 | 0,014 | Ganó |
| `raza` | 0,000 | 0,007 | Ganó |
| `edad` | 0,000 | 0,003 | Sin cambio |
| `estado_de_vacunacion` | 0,000 | 0,000 | Sin cambio |
| `frecuencia_de_ordeno` | 0,000 | 0,000 | Sin cambio |
| `ph_leche` | 0,160 | — | Perdió (excluida) |
| `conductividad_leche_ms_cm` | 0,020 | — | Perdió (excluida) |
| `temperatura` | 0,000 | — | Perdió (excluida) |
| `humedad` | 0,000 | — | Perdió (excluida) |

### Regresión logística

| Variable | Completo | Campo | Lectura |
|---|---|---|---|
| `volumen_de_leche` | -0,001 | 0,091 | Ganó |
| `antecedentes_de_mastitis` | 0,001 | 0,062 | Ganó |
| `numero_de_partos` | 0,001 | 0,032 | Ganó |
| `etapa_de_lactancia` | 0,000 | 0,007 | Ganó |
| `raza` | 0,000 | 0,001 | Sin cambio |
| `estado_de_vacunacion` | 0,000 | 0,000 | Sin cambio |
| `frecuencia_de_ordeno` | 0,000 | 0,000 | Sin cambio |
| `edad` | 0,001 | -0,009 | Perdió |
| `conductividad_leche_ms_cm` | 0,097 | — | Perdió (excluida) |
| `ph_leche` | 0,069 | — | Perdió (excluida) |
| `humedad` | 0,001 | — | Perdió (excluida) |
| `temperatura` | 0,000 | — | Perdió (excluida) |

## Filas de Finca 6 (n = 8, 1 positiva)

Predicciones fuera de pliegue. Su conductividad se imputa con la mediana de entrenamiento, que cae en el rango de mastitis (`docs/CURACION_DATOS.md`).

| Modelo | Variables | VP | FP | VN | FN |
|---|---|---|---|---|---|
| Árbol de decisión | Completo | 1 | 0 | 7 | 0 |
| Árbol de decisión | Campo | 1 | 4 | 3 | 0 |
| Random Forest | Completo | 1 | 4 | 3 | 0 |
| Random Forest | Campo | 0 | 5 | 2 | 1 |
| Regresión logística | Completo | 1 | 1 | 6 | 0 |
| Regresión logística | Campo | 1 | 4 | 3 | 0 |

## Cómo leer esta tabla

- **Separación total por pH en esta muestra.** Máximo en sanas 6,72, mínimo con mastitis 6,75. Con conductividad: 5,25 y 5,45. Las métricas del modelo completo reflejan esa separación y no demuestran generalización: puede ser un efecto biológico o una circularidad con la verdad de referencia.
- **Dos variables de campo no aportan.** `frecuencia_de_ordeno` es constante y `estado_de_vacunacion` vale 1 en una sola fila de 209. Se entrenó con las ocho; retirarlas es decisión de los autores.
- **`signos sanitarios`.** No existe esa columna. Se tomó `antecedentes_de_mastitis`, la única predictora restante del animal que no requiere instrumento. Debe confirmarse.
- **Solo 6 fincas.** P5 agrupa dos fincas y la DE se calcula sobre 5 pliegues. No hay validación externa.
