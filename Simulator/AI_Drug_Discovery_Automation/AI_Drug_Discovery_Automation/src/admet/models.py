"""
ADMET ML Models Module
======================

Machine learning models for ADMET property prediction.
Supports Random Forest, XGBoost, and Neural Network models.
"""

import json
import logging
import pickle
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from abc import ABC, abstractmethod

import numpy as np

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# Abstract Base Model
# ──────────────────────────────────────────────────────────


class BaseADMETModel(ABC):
    """Abstract base class for ADMET prediction models."""

    @abstractmethod
    def train(self, X: np.ndarray, y: np.ndarray) -> Any:
        """Train the model."""
        pass

    @abstractmethod
    def predict(self, features: np.ndarray) -> np.ndarray:
        """Predict ADMET property."""
        pass

    @abstractmethod
    def save(self, path: str) -> None:
        """Save the trained model."""
        pass

    @abstractmethod
    def load(self, path: str) -> None:
        """Load a trained model."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Model name."""
        pass


# ──────────────────────────────────────────────────────────
# Random Forest Model
# ──────────────────────────────────────────────────────────


class RandomForestADMET(BaseADMETModel):
    """
    Random Forest model for ADMET prediction.

    Usage:
        model = RandomForestADMET(n_estimators=100)
        model.train(X_train, y_train)
        preds = model.predict(X_test)
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 10,
        random_state: int = 42,
        n_jobs: int = -1,
    ):
        self.params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "random_state": random_state,
            "n_jobs": n_jobs,
        }
        self.model = None

    def train(self, X: np.ndarray, y: np.ndarray) -> Any:
        from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
        if len(np.unique(y)) < 10:  # Classification
            self.model = RandomForestClassifier(**self.params)
        else:  # Regression
            self.model = RandomForestRegressor(**self.params)
        self.model.fit(X, y)
        logger.info(f"RF model trained: {self.model.__class__.__name__}, features={X.shape[1]}")
        return self.model

    def predict(self, features: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        return self.model.predict(features)

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"model": self.model, "params": self.params}, f)
        logger.info(f"RF model saved to {path}")

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.model = data["model"]
        self.params = data.get("params", self.params)
        logger.info(f"RF model loaded from {path}")

    @property
    def name(self) -> str:
        return "RandomForest"


class XGBoostADMET(BaseADMETModel):
    """
    XGBoost model for ADMET prediction.

    Usage:
        model = XGBoostADMET(n_estimators=100)
        model.train(X_train, y_train)
        preds = model.predict(X_test)
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 6,
        learning_rate: float = 0.1,
        random_state: int = 42,
    ):
        self.params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "random_state": random_state,
        }
        self.model = None

    def train(self, X: np.ndarray, y: np.ndarray) -> Any:
        try:
            import xgboost as xgb
            if len(np.unique(y)) < 10:
                self.model = xgb.XGBClassifier(**self.params)
            else:
                self.model = xgb.XGBRegressor(**self.params, verbosity=0)
            self.model.fit(X, y)
            logger.info(f"XGBoost model trained: features={X.shape[1]}")
            return self.model
        except ImportError:
            logger.warning("XGBoost not available. Install with: pip install xgboost")
            # Fallback to Random Forest
            logger.info("Falling back to Random Forest...")
            rf = RandomForestADMET()
            rf.train(X, y)
            self.model = rf.model
            return self.model

    def predict(self, features: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        return self.model.predict(features)

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"model": self.model, "params": self.params}, f)
        logger.info(f"XGBoost model saved to {path}")

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.model = data["model"]
        self.params = data.get("params", self.params)
        logger.info(f"XGBoost model loaded from {path}")

    @property
    def name(self) -> str:
        return "XGBoost"


class NeuralNetworkADMET(BaseADMETModel):
    """
    PyTorch neural network for ADMET prediction.

    Usage:
        model = NeuralNetworkADMET(input_dim=100, hidden_dim=64)
        model.train(X_train, y_train)
        preds = model.predict(X_test)
    """

    def __init__(
        self,
        input_dim: int = 100,
        hidden_dim: int = 128,
        n_layers: int = 3,
        dropout: float = 0.2,
        learning_rate: float = 1e-3,
        batch_size: int = 32,
        epochs: int = 100,
        device: str = "cpu",
    ):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.n_layers = n_layers
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs
        self.device = device
        self.model = None
        self.is_classifier = False

    def _build_model(self, output_dim: int):
        """Build the neural network architecture."""
        try:
            import torch
            import torch.nn as nn

            layers = []
            in_dim = self.input_dim

            for i in range(self.n_layers):
                out_dim = self.hidden_dim // (2 ** i) if i < self.n_layers - 1 else output_dim
                layers.append(nn.Linear(in_dim, out_dim))
                if i < self.n_layers - 1:
                    layers.append(nn.ReLU())
                    layers.append(nn.Dropout(self.dropout))
                in_dim = out_dim

            self.model = nn.Sequential(*layers)
            self.model.to(self.device)
            logger.info(f"Neural network built: {self.model}")

        except ImportError:
            logger.warning("PyTorch not available. Installing required...")
            raise ImportError("PyTorch is required for NeuralNetworkADMET")

    def train(self, X: np.ndarray, y: np.ndarray) -> Any:
        try:
            import torch
            import torch.nn as nn
            import torch.optim as optim
            from torch.utils.data import DataLoader, TensorDataset

            # Determine output dimension
            self.is_classifier = len(np.unique(y)) < 10
            output_dim = len(np.unique(y)) if self.is_classifier else 1

            self._build_model(output_dim)

            # Convert to tensors
            X_t = torch.FloatTensor(X).to(self.device)
            y_t = torch.FloatTensor(y).to(self.device) if not self.is_classifier else torch.LongTensor(y).to(self.device)

            dataset = TensorDataset(X_t, y_t)
            loader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)

            # Loss and optimizer
            if self.is_classifier:
                criterion = nn.CrossEntropyLoss()
            else:
                criterion = nn.MSELoss()
            optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)

            # Training loop
            for epoch in range(self.epochs):
                epoch_loss = 0.0
                for batch_X, batch_y in loader:
                    optimizer.zero_grad()
                    outputs = self.model(batch_X)
                    if not self.is_classifier:
                        outputs = outputs.squeeze()
                    loss = criterion(outputs, batch_y)
                    loss.backward()
                    optimizer.step()
                    epoch_loss += loss.item()

                if (epoch + 1) % 20 == 0:
                    logger.debug(f"Epoch [{epoch+1}/{self.epochs}] Loss: {epoch_loss/len(loader):.4f}")

            logger.info(f"Neural network trained: {self.epochs} epochs")
            return self.model

        except ImportError:
            raise ImportError("PyTorch is required for NeuralNetworkADMET")

    def predict(self, features: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        try:
            import torch
            self.model.eval()
            with torch.no_grad():
                X_t = torch.FloatTensor(features).to(self.device)
                outputs = self.model(X_t)
                if self.is_classifier:
                    return torch.softmax(outputs, dim=1).numpy()
                return outputs.squeeze().numpy()
        except ImportError:
            raise ImportError("PyTorch is required")

    def save(self, path: str) -> None:
        try:
            import torch
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            torch.save({
                "model_state_dict": self.model.state_dict(),
                "input_dim": self.input_dim,
                "hidden_dim": self.hidden_dim,
                "n_layers": self.n_layers,
                "dropout": self.dropout,
                "is_classifier": self.is_classifier,
            }, path)
            logger.info(f"Neural network saved to {path}")
        except ImportError:
            logger.error("PyTorch is required to save the model")

    def load(self, path: str) -> None:
        try:
            import torch
            checkpoint = torch.load(path, map_location=self.device)
            self.input_dim = checkpoint["input_dim"]
            self.hidden_dim = checkpoint["hidden_dim"]
            self.n_layers = checkpoint["n_layers"]
            self.dropout = checkpoint["dropout"]
            self.is_classifier = checkpoint["is_classifier"]
            output_dim = checkpoint["model_state_dict"][list(checkpoint["model_state_dict"].keys())[-1]].shape[0]
            self._build_model(output_dim)
            self.model.load_state_dict(checkpoint["model_state_dict"])
            logger.info(f"Neural network loaded from {path}")
        except ImportError:
            logger.error("PyTorch is required to load the model")

    @property
    def name(self) -> str:
        return "NeuralNetwork"


# ──────────────────────────────────────────────────────────
# Model Ensemble
# ──────────────────────────────────────────────────────────


class ModelEnsemble(BaseADMETModel):
    """
    Ensemble of multiple ADMET prediction models.

    Combines predictions from multiple models using weighted averaging.

    Usage:
        ensemble = ModelEnsemble()
        ensemble.add_model("rf", rf_model, weight=1.0)
        ensemble.add_model("xgb", xgb_model, weight=1.5)
        preds = ensemble.predict(features)
    """

    def __init__(self, strategy: str = "weighted_average"):
        self.models: Dict[str, Tuple[BaseADMETModel, float]] = {}
        self.strategy = strategy  # 'weighted_average', 'median', 'best'

    def add_model(self, name: str, model: BaseADMETModel, weight: float = 1.0) -> None:
        self.models[name] = (model, weight)
        logger.info(f"Added model '{name}' to ensemble (weight={weight})")

    def remove_model(self, name: str) -> None:
        self.models.pop(name, None)

    def train(self, X: np.ndarray, y: np.ndarray) -> Any:
        results = {}
        for name, (model, _) in self.models.items():
            results[name] = model.train(X, y)
        return results

    def predict(self, features: np.ndarray) -> np.ndarray:
        if not self.models:
            raise ValueError("No models in ensemble.")

        predictions = []
        weights = []

        for name, (model, weight) in self.models.items():
            pred = model.predict(features)
            predictions.append(pred)
            weights.append(weight)

        predictions = np.array(predictions)
        weights = np.array(weights)

        if self.strategy == "weighted_average":
            return np.average(predictions, axis=0, weights=weights)
        elif self.strategy == "median":
            return np.median(predictions, axis=0)
        elif self.strategy == "best":
            # Return prediction from highest-weight model
            best_idx = np.argmax(weights)
            return predictions[best_idx]
        return np.mean(predictions, axis=0)

    def save(self, path: str) -> None:
        data = {
            "strategy": self.strategy,
            "models": list(self.models.keys()),
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(data, f)

        # Save individual models
        model_dir = Path(path).parent / "ensemble_models"
        for name, (model, weight) in self.models.items():
            model.save(str(model_dir / f"{name}.pkl"))

        logger.info(f"Ensemble saved to {path}")

    def load(self, path: str) -> None:
        with open(path, "rb") as f:
            data = pickle.load(f)

        self.strategy = data["strategy"]
        model_dir = Path(path).parent / "ensemble_models"

        for model_name in data["models"]:
            model_path = model_dir / f"{model_name}.pkl"
            if model_path.exists():
                # Determine model type from name
                if "rf" in model_name.lower():
                    model = RandomForestADMET()
                elif "xgb" in model_name.lower() or "xgboost" in model_name.lower():
                    model = XGBoostADMET()
                else:
                    model = RandomForestADMET()
                model.load(str(model_path))
                self.add_model(model_name, model)

        logger.info(f"Ensemble loaded from {path}")

    @property
    def name(self) -> str:
        return f"Ensemble({', '.join(self.models.keys())})"


# ──────────────────────────────────────────────────────────
# Model Manager
# ──────────────────────────────────────────────────────────


class ModelManager:
    """
    Manages ADMET model lifecycle: training, loading, saving, and discovery.

    Usage:
        manager = ModelManager(model_dir="models/admet")
        manager.list_available_models()
        model = manager.get_model("logp", "random_forest")
    """

    def __init__(self, model_dir: str = "models/admet"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def list_available_models(self) -> List[Dict[str, Any]]:
        """List all available pre-trained models."""
        models = []
        for f in self.model_dir.glob("*.pkl"):
            try:
                with open(f, "rb") as fh:
                    data = pickle.load(fh)
                models.append({
                    "name": f.stem,
                    "path": str(f),
                    "size_kb": round(f.stat().st_size / 1024, 1),
                    "type": data.get("params", {}).get("type", "unknown"),
                })
            except Exception:
                models.append({"name": f.stem, "path": str(f), "error": "Corrupted"})
        return models

    def get_model(self, property: str, model_type: str = "random_forest") -> Optional[BaseADMETModel]:
        """
        Get a model for a specific ADMET property.

        Args:
            property: ADMET property name (e.g., 'logp', 'solubility', 'ames').
            model_type: Model type ('random_forest', 'xgboost', 'neural_network').

        Returns:
            Loaded model or None.
        """
        model_path = self.model_dir / f"{property}_{model_type}.pkl"
        if not model_path.exists():
            # Try without model_type
            model_path = self.model_dir / f"{property}.pkl"

        if not model_path.exists():
            logger.warning(f"No model found for {property} ({model_type})")
            return None

        if model_type == "random_forest":
            model = RandomForestADMET()
        elif model_type == "xgboost":
            model = XGBoostADMET()
        elif model_type == "neural_network":
            model = NeuralNetworkADMET()
        else:
            model = RandomForestADMET()

        try:
            model.load(str(model_path))
            return model
        except Exception as e:
            logger.error(f"Failed to load model {model_path}: {e}")
            return None

    def get_model_info(self, name: str) -> Dict[str, Any]:
        """Get detailed information about a model."""
        model_path = self.model_dir / f"{name}.pkl"
        if not model_path.exists():
            return {"error": f"Model '{name}' not found"}
        return {
            "name": name,
            "path": str(model_path),
            "size_bytes": model_path.stat().st_size,
            "modified": model_path.stat().st_mtime,
        }

    def download_pretrained(self, url: str, dest: Optional[str] = None) -> bool:
        """
        Download a pre-trained ADMET model.

        Args:
            url: URL to download from.
            dest: Destination path (auto-generated if None).

        Returns:
            True if download succeeded.
        """
        try:
            import requests
            dest = dest or str(self.model_dir / Path(url).name)
            Path(dest).parent.mkdir(parents=True, exist_ok=True)
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"Downloaded model from {url} to {dest}")
            return True
        except Exception as e:
            logger.error(f"Failed to download model: {e}")
            return False


# ──────────────────────────────────────────────────────────
# Training Utilities
# ──────────────────────────────────────────────────────────


def prepare_features(molecules: List[Any], descriptors: Optional[List[str]] = None) -> np.ndarray:
    """
    Prepare feature matrix from molecules for model training.

    Args:
        molecules: List of RDKit Mol objects or SMILES.
        descriptors: List of descriptor names to use.

    Returns:
        Feature matrix (n_samples × n_features).
    """
    from src.molecular.rdkit_utils import MolFromSMILES, calculate_all_descriptors

    if descriptors is None:
        descriptors = ["MW", "LogP", "HBD", "HBA", "TPSA", "RotB",
                       "RingCount", "HeavyAtomCount", "FractionCSP3",
                       "NumHeteroatoms", "NumAromaticRings"]

    feature_list = []
    for mol_input in molecules:
        if isinstance(mol_input, str):
            mol = MolFromSMILES(mol_input)
        else:
            mol = mol_input

        if mol is None:
            feature_list.append([0.0] * len(descriptors))
            continue

        desc = calculate_all_descriptors(mol)
        row = [desc.get(d, 0.0) for d in descriptors]
        feature_list.append(row)

    return np.array(feature_list, dtype=np.float32)


def prepare_labels(molecules: List[Any], property: str, value_extractor: Optional[callable] = None) -> np.ndarray:
    """
    Prepare label vector from molecules.

    Args:
        molecules: List of molecules.
        property: Property name.
        value_extractor: Custom function to extract property value.

    Returns:
        Label vector.
    """
    if value_extractor:
        return np.array([value_extractor(m) for m in molecules], dtype=np.float32)

    # Default property extraction
    labels = []
    for m in molecules:
        if isinstance(m, dict):
            labels.append(m.get(property, 0.0))
        elif isinstance(m, (list, tuple)):
            labels.append(m[-1] if isinstance(m[-1], (int, float)) else 0.0)
        else:
            labels.append(0.0)

    return np.array(labels, dtype=np.float32)


def train_test_split(X: np.ndarray, y: np.ndarray, test_size: float = 0.2) -> Tuple:
    """Split data into training and test sets."""
    from sklearn.model_selection import train_test_split as sk_split
    return sk_split(X, y, test_size=test_size, random_state=42)


def cross_validate(model: BaseADMETModel, X: np.ndarray, y: np.ndarray, folds: int = 5) -> Dict[str, float]:
    """
    Perform cross-validation.

    Args:
        model: ADMET model instance.
        X: Feature matrix.
        y: Target vector.
        folds: Number of folds.

    Returns:
        Dictionary of metrics (mean, std).
    """
    from sklearn.model_selection import cross_val_score
    from sklearn.ensemble import RandomForestRegressor

    # Use sklearn estimator
    if hasattr(model, 'model') and model.model is not None:
        estimator = model.model
    else:
        estimator = RandomForestRegressor(n_estimators=50)

    scores = cross_val_score(estimator, X, y, cv=folds, scoring='r2')
    return {
        "r2_mean": float(np.mean(scores)),
        "r2_std": float(np.std(scores)),
        "r2_scores": scores.tolist(),
    }


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate regression/classification metrics."""
    from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

    metrics = {
        "r2": float(r2_score(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
    }

    # For classification (if binary)
    if len(np.unique(y_true)) == 2:
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        binary_preds = (y_pred > 0.5).astype(int) if y_pred.dtype == float else y_pred
        metrics["accuracy"] = float(accuracy_score(y_true, binary_preds))
        try:
            metrics["auc_roc"] = float(roc_auc_score(y_true, y_pred))
        except Exception:
            pass

    return metrics
