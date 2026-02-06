from __future__ import annotations
from pathlib import Path
from typing import Any
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

try:
    import mlflow
    from mlflow.sklearn import log_model
except ImportError:
    mlflow = None
    log_model = None

def train_model() -> LogisticRegression:
    """Обучает простую модель на синтетических данных."""
    np.random.seed(42)
    # Признаки: [is_verified_seller, images_qty, description_length, category]
    X = np.random.rand(1000, 4)
    # Целевая переменная: 1 = нарушение, 0 = нет нарушения
    y = (X[:, 0] < 0.3) & (X[:, 1] < 0.2)
    y = y.astype(int)
    
    model = LogisticRegression(random_state=42, max_iter=200)
    model.fit(X, y)
    return model

def save_model(model: LogisticRegression, path: Path | str = "model.pkl") -> None:
    path = Path(path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)

def train_and_save_model(
    path: Path | str = "model.pkl",
    use_mlflow: bool = False,
    mlflow_tracking_uri: str = "sqlite:///mlflow.db",
    mlflow_experiment: str = "moderation-model",
    mlflow_model_name: str = "moderation-model",
) -> LogisticRegression:
    model = train_model()
    save_model(model, path)
    if use_mlflow:
        register_model_in_mlflow(
            model,
            tracking_uri=mlflow_tracking_uri,
            experiment=mlflow_experiment,
            registered_model_name=mlflow_model_name,
        )
    return model

def load_model(path: Path | str = "model.pkl") -> LogisticRegression:
    path = Path(path)
    return joblib.load(path)


def load_model_from_mlflow(model_name: str, stage: str = "Production") -> Any:
    if mlflow is None:
        raise RuntimeError("MLflow is not available")
    model_uri = f"models:/{model_name}/{stage}"
    return mlflow.sklearn.load_model(model_uri)


def register_model_in_mlflow(
    model: LogisticRegression,
    tracking_uri: str,
    experiment: str,
    registered_model_name: str,
) -> None:
    if mlflow is None or log_model is None:
        raise RuntimeError("MLflow is not available")

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment)
    with mlflow.start_run():
        log_model(
            model,
            name="model",
            registered_model_name=registered_model_name,
        )

