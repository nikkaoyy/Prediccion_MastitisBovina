# Protocolo de verdad de referencia (CMT) y recolección de datos nuevos

Objetivo: obtener datos que permitan **validar externamente** el Modelo B y medir el Recall real de la app sin circularidad entre la etiqueta y el pH.

> Este protocolo es una propuesta técnica. Debe ser revisado por el director y por un médico veterinario antes de usarse; los campos `[COMPLETAR]` los define el equipo.

## 1. Definición de la etiqueta

- **Verdad de referencia:** prueba CMT (California Mastitis Test) por cuarto o a nivel de vaca [COMPLETAR].
- **Escala y regla:** N (negativo), T (trazas), 1, 2, 3. **Positivo = grado 1, 2 o 3**; N y T son negativos. (Es la regla que aplican la app y el servidor: un grado incoherente con `resultado_positivo` se rechaza.)
- **Confirmación opcional:** conteo de células somáticas o cultivo bacteriológico en una submuestra [COMPLETAR].

## 2. Ciego (evita circularidad)

1. La persona que lee el CMT **no debe conocer** el pH ni la estimación de la app al momento de leer.
2. La app guarda `ciego_al_ph` (casilla en la pantalla CMT). Solo los registros con `ciego_al_ph = true` se usan para validar.
3. **Limitación actual de la app:** muestra el riesgo apenas se calcula (no hay modo ciego todavía), por lo que durante la validación el pH debe ingresarlo una persona y el CMT leerlo otra que no vea la pantalla; la casilla `ciego_al_ph` es declarativa.
4. Para evitar sesgo de verificación, aplicar CMT a **todas** las vacas del estudio, no solo a las de riesgo medio/alto.
5. El orden recomendado en el ordeño: (a) tomar la muestra, (b) otra persona mide el pH y lo ingresa en la app **sin mostrarlo**, (c) el evaluador lee el CMT y registra el resultado, (d) recién entonces se muestra el riesgo.

## 3. Momento de las mediciones

- pH y CMT de la **misma muestra y en el mismo ordeño**; registrar fecha y hora (la app las guarda con zona horaria).
- Registrar el instrumento de pH y la calibración del día (tampones 4,01 / 7,00 / 10,01) [COMPLETAR: bitácora].

## 4. Tamaño y diseño mínimos

- Fincas **nuevas** (no usadas en el entrenamiento), idealmente en otra temporada.
- Mínimo orientativo: 5 fincas y 20 vacas con CMT positivo para estimar el Recall con un IC aceptable (el servidor solo informa Recall observado con ≥ 20 positivos confirmados).
- Una medición por vaca por visita; `vaca_id` único y estable entre visitas (la app lo genera) para poder estudiar series por animal.

## 5. Plantilla de recolección

`data/templates/plantilla_recoleccion.csv` (si se recolecta en papel antes de usar la app). Columnas: finca, vaca_id, arete, fecha, hora, edad, raza, partos, volumen, etapa de lactancia, antecedentes, humedad, temperatura ambiental, pH, instrumento_ph, cmt_grado, cmt_evaluador, cmt_ciego_al_ph, observaciones.

## 6. Análisis previsto

1. Congelar el modelo (`models/model_lite.json`, versión registrada) **antes** de ver los datos nuevos.
2. Calcular Recall, precisión y AUC con IC bootstrap por finca solo sobre registros ciegos.
3. Reportar los positivos clasificados como riesgo “bajo” y revisarlos con el veterinario.
4. Si el desempeño cae de forma importante respecto a la validación interna, documentarlo y no desplegar sin recalibrar.
