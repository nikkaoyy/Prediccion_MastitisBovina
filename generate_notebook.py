import json
import os

notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Análisis y Testeo de Modelos de Mastitis Bovina\n",
                "\n",
                "Este notebook documenta el análisis de los datos sintéticos (dummy data) generados basándose en las propiedades de la Finca.\n",
                "\n",
                "## Anomalía en el Dataset: Relación Volumen de Leche vs Mastitis\n",
                "> **Hallazgo Importante:** En los datos sin procesar originales, se observa que algunas vacas con mastitis tienden a tener un volumen de leche mayor. Clínicamente, la mastitis causa inflamación y daño en el tejido mamario, lo que debería reducir la producción de leche. Este patrón puede ser un artefacto del proceso de recolección de datos, un error humano en el registro, o estar condicionado por otras variables (por ejemplo, vacas de alta producción siendo más susceptibles y monitoreadas más de cerca).\n",
                "\n",
                "Se recomienda documentar y vigilar esta variable cuando se expanda el modelo con datos en tiempo real mediante CRISP-ML(Q).\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import pandas as pd\n",
                "import numpy as np\n",
                "import matplotlib.pyplot as plt\n",
                "import seaborn as sns\n",
                "import joblib\n",
                "import warnings\n",
                "warnings.filterwarnings('ignore')\n",
                "\n",
                "import sys\n",
                "sys.path.append('../') # Para importar desde src\n",
                "from src.data.dummyDataGenerator import generate_dummy_data\n",
                "\n",
                "# Generar datos sintéticos\n",
                "df = generate_dummy_data(n_samples=500, random_state=123)\n",
                "df.head()"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Análisis Exploratorio de Variables\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "fig, axes = plt.subplots(1, 3, figsize=(18, 5))\n",
                "\n",
                "# Edad vs Mastitis\n",
                "sns.boxplot(x='mastitis', y='edad', data=df, ax=axes[0])\n",
                "axes[0].set_title('Edad vs Mastitis')\n",
                "\n",
                "# Número de partos vs Mastitis\n",
                "sns.boxplot(x='mastitis', y='numero_de_partos', data=df, ax=axes[1])\n",
                "axes[1].set_title('Número de Partos vs Mastitis')\n",
                "\n",
                "# Volumen vs Mastitis\n",
                "sns.boxplot(x='mastitis', y='volumen_de_leche', data=df, ax=axes[2])\n",
                "axes[2].set_title('Volumen de Leche vs Mastitis')\n",
                "\n",
                "plt.tight_layout()\n",
                "plt.show()"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Evaluación de Modelos (Dummy Data)\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from pathlib import Path\n",
                "from sklearn.metrics import classification_report\n",
                "\n",
                "artifacts_dir = Path(\"../src/data/artifacts\")\n",
                "models = [\"decision_tree\", \"random_forest\", \"logistic_regression\"]\n",
                "\n",
                "X_test = df.drop(columns=[\"finca\", \"mastitis\"])\n",
                "y_test = df[\"mastitis\"]\n",
                "\n",
                "for model_name in models:\n",
                "    model_path = artifacts_dir / f\"mastitis_{model_name}_pipeline.pkl\"\n",
                "    if model_path.exists():\n",
                "        model = joblib.load(model_path)\n",
                "        predictions = model.predict(X_test)\n",
                "        print(f\"--- Evaluación: {model_name.upper()} ---\")\n",
                "        print(classification_report(y_test, predictions, target_names=[\"Sana\", \"Mastitis\"]))\n",
                "    else:\n",
                "        print(f\"Modelo no encontrado: {model_path}\")"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {
                "name": "ipython",
                "version": 3
            },
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.8.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

os.makedirs('notebooks', exist_ok=True)
with open('notebooks/Model_Analysis_and_Testing.ipynb', 'w', encoding='utf-8') as f:
    json.dump(notebook, f, ensure_ascii=False, indent=2)

print("Notebook generado exitosamente")
