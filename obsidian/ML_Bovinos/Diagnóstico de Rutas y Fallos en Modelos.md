# Diagnóstico de Rutas y Fallos en Modelos

> **Alcance:** Auditoría técnica de fallos de ejecución, dependencias y rutas en `src/models/`, `main.py` y `notebooks/`.  
> **Objetivo:** Dejar constancia y testimonio explícito de por qué los archivos en la carpeta `models` fallan al intentar entrenar de forma aislada, y establecer la guía de resolución para futuras IAs y desarrolladores.

---

## 🚨 Testigo Técnico: Síntomas y Causas Raíz

Al intentar ejecutar los entrenamientos de modelos directamente desde la carpeta `src/models/` o a través de ciertos entornos de ejecución, el proceso falla o se bloquea. A continuación se detallan las **5 causas raíz identificadas**:

### 1. Error Crítico de Importación: `ModuleNotFoundError: No module named 'src'`
* **Síntoma:** Al pararse en la carpeta `src/models/` o ejecutar:
  ```powershell
  python src/models/DecisionTreeTraining.py
  # O:
  cd src/models
  python RandomForest.py
  ```
  Se desencadena inmediatamente:
  ```python
  Traceback (most recent call last):
    File "src/models/DecisionTreeTraining.py", line 28, in <module>
      from src.data.featureEngineer import FeaturePipelineBuilder
  ModuleNotFoundError: No module named 'src'
  ```
* **Causa Raíz:** Python agrega automáticamente al inicio de `sys.path` el directorio donde reside el script ejecutado (`src/models/`). Desde esa ubicación, el paquete de nivel superior `src` no existe en el árbol visible, rompiendo cualquier importación absoluta que comience por `from src...`.
* **Solución Estándar:** 
  1. Ejecutar siempre desde la raíz del proyecto usando el modo módulo:
     ```powershell
     python -m src.models.DecisionTreeTraining
     ```
  2. O agregar una resolución dinámica de la raíz del proyecto al inicio de cada script en `models/`:
     ```python
     import sys
     from pathlib import Path
     sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
     ```

---

### 2. Ambigüedad de Rutas Relativas al Persistir Artefactos y Reportes
* **Síntoma:** En `main.py` y `generateDecisionTree.py`, los argumentos de ruta para artefactos y reportes se definen como cadenas o rutas relativas:
  ```python
  def run(
      data_path: str | Path,
      artifacts_dir: str | Path = "src/data/artifacts",
      reports_dir: str | Path = "demo_reports",
      use_dummy: bool = False,
  ) -> dict[str, Any]:
  ```
* **Causa Raíz:** Si el comando se invoca desde una carpeta distinta a la raíz (por ejemplo, desde `notebooks/`, `src/`, o mediante una extensión de IDE), `Path("src/data/artifacts")` se resuelve relativo al *Current Working Directory* ($CWD$) actual del proceso, creando carpetas espurias anidadas (`notebooks/src/data/artifacts`) o provocando `FileNotFoundError`.
* **Solución Estándar:** Anclar todas las rutas predeterminadas a la constante absoluta `PROJECT_ROOT`:
  ```python
  PROJECT_ROOT = Path(__file__).resolve().parent
  DEFAULT_ARTIFACTS_DIR = PROJECT_ROOT / "src" / "data" / "artifacts"
  DEFAULT_REPORTS_DIR = PROJECT_ROOT / "demo_reports"
  ```

---

### 3. Divergencia en el Kernel del Jupyter Notebook (`Model_Analysis_and_Testing.ipynb`)
* **Síntoma:** El notebook contiene la siguiente celda de inicialización:
  ```python
  import sys
  sys.path.append('../') # Para importar desde src
  from pathlib import Path
  artifacts_dir = Path("../src/data/artifacts")
  ```
* **Causa Raíz:** Si el usuario o VS Code inicia el kernel de Jupyter teniendo como directorio de trabajo la raíz del proyecto (`ML_BOVINOS`), `../src/data/artifacts` apuntará a `c:/Users/nikka/OneDrive/Documentos/src/data/artifacts` (fuera del repositorio), fallando al cargar los modelos `.pkl`.
* **Solución Estándar:** Usar detección agnóstica de la raíz en el notebook:
  ```python
  from pathlib import Path
  import sys
  PROJECT_ROOT = Path.cwd() if (Path.cwd() / "src").exists() else Path.cwd().parent
  if str(PROJECT_ROOT) not in sys.path:
      sys.path.insert(0, str(PROJECT_ROOT))
  artifacts_dir = PROJECT_ROOT / "src" / "data" / "artifacts"
  ```

---

### 4. Ausencia de Bloque Ejecutable (`__main__`) en los Scripts de Modelos
* **Síntoma:** Aunque se solucione la importación ejecutando `python -m src.models.DecisionTreeTraining` o `python -m src.models.RandomForest`, el script termina inmediatamente sin hacer nada y sin entrenar ningún modelo.
* **Causa Raíz:** `DecisionTreeTraining.py`, `LogisticalRegresion.py` y `RandomForest.py` son únicamente definiciones de clases (`Trainer`). No poseen bloque `if __name__ == '__main__':` ni argumentos de línea de comandos para cargar el dataset y entrenar. Toda la orquestación depende de `main.py`.

---

### 5. Cuello de Botella Computacional y Bloqueo en `GridSearchCV` Anidado
* **Síntoma:** Al lanzar el entrenamiento completo vía `python main.py`, el proceso parece quedarse colgado indefinidamente.
* **Causa Raíz:**
  1. **Explosión Combinatoria:** `DecisionTreeModelTrainer` ejecuta un `GridSearchCV` externo con 144 combinaciones sobre 5 pliegues de `GroupKFold` ($720$ ajustes). Pero dentro de cada uno de los 5 pliegues de evaluación OOF (`evaluate_grouped_cv`), se ejecuta *otro* `GridSearchCV` anidado con 144 combinaciones sobre 5 pliegues internos ($5 	imes 720 = 3600$ ajustes). En total, son **más de 4,320 ajustes de árboles** para un solo modelo, ejecutados en un solo hilo (`n_jobs=1`).
  2. **Colapso de Métrica F1 por Finca 6:** Como la Finca 6 tiene 0 casos positivos, cuando queda como fold de prueba, `f1_score` lanza masivamente:
     `UndefinedMetricWarning: F-score is ill-defined and being set to 0.0 due to no true nor predicted samples`.
  3. **Riesgo en Windows con `n_jobs=-1`:** En `RandomForest.py` y `LogisticalRegresion.py` se especificó `n_jobs=-1`. En Windows, si el multiprocessing de `joblib` no está estrictamente blindado bajo `if __name__ == '__main__':`, puede provocar bucles de spawneo recursivo de procesos.

---

## 🛠️ Plan de Refactorización y Reparación

Para habilitar el entrenamiento fluido con el dataset real en la siguiente fase:

1. **Blindaje de Paths en Modelos:**  
   Agregar al inicio de cada archivo en `src/models/` la inyección de `PROJECT_ROOT` en `sys.path`.
2. **Normalización en `main.py`:**  
   Convertir todos los paths relativos (`artifacts_dir`, `reports_dir`) a rutas absolutas ancladas a `PROJECT_ROOT`.
3. **Poda del Espacio de Búsqueda (`param_grid`):**  
   Optimizar los diccionarios de hiperparámetros para que la búsqueda anidada tarde menos de 10 segundos en lugar de varios minutos.
4. **Control de División por Cero en Métricas:**  
   Asegurar `zero_division=0` en todas las llamadas a `f1_score`, `precision_score` y en el scoring de `GridSearchCV`.

---

## 🔗 Enlaces Relacionados
- [[CORE DEL PROYECTO]]
- [[Análisis Profundo del Dataset y Nuevos Datos]]
- [[Arquitectura CRISP-ML(Q) y Pipelines]]
- [[Hoja de Ruta y Próximos Pasos]]