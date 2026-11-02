# Curación del dataset v3

Archivo: `data/raw/datos_entrenamiento_mastitis-v3.csv`. Código: `src/data/curation.py`. Candados: `tests/test_curacion.py`.

## Estado resultante

- **209 filas × 14 columnas, 6 fincas** (`Finca_1` a `Finca_6`), 112 positivos y 97 negativos (prevalencia 53,6 %).
- Finca 6: 8 filas, 1 positiva (12,5 %).
- Único faltante: `conductividad_leche_ms_cm` en las 8 filas de Finca 6.

## Las 208 filas de la documentación antigua

Varias notas y la versión anterior de esta tarea hablan de 208 filas, 7 en Finca 6, prevalencia 53,4 %, Finca 6 con 0 % y `estado_de_vacunacion` constante. Todas esas cifras corresponden al CSV **sin su última fila**, que no termina en salto de línea, lo que la hace fácil de perder al contar líneas. Esa fila existe desde el commit `a6a4f5b` (2026-09-20) y se conserva:

```
Finca_6,8,Holstein,5,15.5,1,2,1,1,46,20,6.92,,1
```

| Cifra | Con 208 filas | Con 209 filas (real) |
|---|---|---|
| Prevalencia global | 53,4 % | 53,6 % |
| Prevalencia Finca 6 | 0 % | 12,5 % |
| Filas sin conductividad | 7 | 8 |
| `estado_de_vacunacion` | constante en 0 | 208 en 0, 1 en 1 |
| Volumen con mastitis | 9,76 L/día | 9,81 L/día |

## Cambios de etiquetas

La unificación ya estaba hecha en el CSV desde el commit `b53b961` (2026-09-19). Las cifras salen de comparar `4a7765d`, última versión sin curar, con el CSV actual. Aplicar `curate()` a `4a7765d` reproduce exactamente las columnas `finca` y `raza` actuales.

| Cambio | Filas | Motivo |
|---|---:|---|
| `finca_6` → `Finca_6` | 6 | `GroupKFold` contaba 7 fincas en vez de 6 |
| `Hounstein` → `Holstein` | 4 | Error ortográfico |
| `Normanda` → `Normando` | 3 | Variante de la misma raza |

Sobre el CSV actual, `curate()` cambia **0 filas**: queda como candado para lotes nuevos.

| Raza | Antes (`4a7765d`, 208 filas) | Después (actual, 209 filas) |
|---|---:|---:|
| Holstein | 123 | 128 |
| Normando | 55 | 58 |
| Jersey | 13 | 13 |
| Pardo_Suizo | 6 | 6 |
| Cruzado | 4 | 4 |
| Hounstein | 4 | 0 |
| Normanda | 3 | 0 |

Holstein pasa de 123 a 128 por las 4 filas corregidas más la fila 209.

## Decisiones

### Se conservan cinco razas, no dos

Jersey (13), Pardo_Suizo (6) y Cruzado (4) son razas registradas, no variantes de escritura. Recodificar esas 23 filas como Holstein o Normando cambiaría el dato de origen, y el artículo y `docs/esquema_datos.md` reconocen esas razas. `curate()` solo une escrituras de una misma raza y rechaza una etiqueta desconocida en lugar de reasignarla.

Si los autores prefieren agrupar, la opción defendible es una categoría `Otra` declarada en el texto, no absorberlas en las dos mayoritarias.

### La conductividad de Finca 6 se imputa con la mediana del pliegue de entrenamiento

El CSV no se rellena: los 8 vacíos siguen vacíos, porque esa medición no se hizo. El `SimpleImputer(strategy="median")` del Pipeline se ajusta solo con el pliegue de entrenamiento, así que al modelo llegan cero nulos y Finca 6 nunca aporta información a su propio valor imputado.

Alternativas descartadas:

- **Media o mediana global:** filtran información entre fincas.
- **Indicador de dato faltante:** como solo falta en Finca 6, sería una variable que identifica la finca.
- **`NaN` nativo del árbol:** Random Forest y regresión logística tampoco lo compartirían, y `model.json` tendría una regla distinta por modelo.

**Limitación medida.** Las medianas de entrenamiento por pliegue van de 5,605 a 5,775 mS/cm. El máximo en vacas sanas es 5,25 y el mínimo con mastitis es 5,45, así que el valor imputado cae dentro del rango de mastitis: las 8 filas de Finca 6, 7 de ellas sanas, entran al modelo con conductividad de vaca enferma. Finca 6 no aporta evidencia sobre la conductividad.

## Hallazgos del historial que no se revirtieron

Son decisiones del autor y quedan señaladas para que las confirme contra la libreta de campo:

1. **`ph_leche` editado a mano:** el commit `2989fcd` cambió una fila de Finca 6 de pH 6,1 a 6,7 (vaca sana) sin motivo registrado. El pH es de los predictores más fuertes.
2. **Fila 209:** es el único positivo de Finca 6 y el único registro con `estado_de_vacunacion = 1`. Se agregó un día después del resto del lote y con humedad y temperatura distintas (46 % y 20 °C frente a 45 % y 16–17 °C).
3. **Humedad de Finca 6:** 45–46 % frente a unos 73 % en las demás fincas. Sigue sin explicarse si es un microclima real o un valor anotado por lote.
4. **`frecuencia_de_ordeno`:** constante en 2, no aporta información.

## Reproducir

```bash
.venv/bin/python -m pytest -q tests/test_curacion.py
git show 4a7765d:data/raw/datos_entrenamiento_mastitis-v3.csv   # versión sin curar
```
