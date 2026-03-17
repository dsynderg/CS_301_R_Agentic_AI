from __future__ import annotations

"""MLPClassifierWrapper
A minimal, reusable wrapper around sklearn.neural_network.MLPClassifier.

Features:
- fit(X, y)
- predict(X)
- predict_proba(X)
- score(X, y)
- save_model(path) / @staticmethod load_model(path)
- minimal input validation via to_numpy_arrays helper
- deterministic by default (random_state set)
"""

from typing import Any

import numpy as np
from sklearn.neural_network import MLPClassifier
from joblib import dump, load


class MLPClassifierWrapper:
    """A small, dependency-light wrapper around scikit-learn's MLPClassifier.

    Parameters
    - hidden_layer_sizes: tuple, e.g., (50, 25)
    - max_iter: int, training iterations
    - random_state: int for reproducibility
    - kwargs: additional keyword arguments passed to MLPClassifier
    """

    def __init__(self, hidden_layer_sizes: tuple = (50,), max_iter: int = 200, random_state: int = 42, **kwargs: Any) -> None:
        self.hidden_layer_sizes = hidden_layer_sizes
        self.max_iter = max_iter
        self.random_state = random_state
        self.kwargs = kwargs
        self.model = MLPClassifier(
            hidden_layer_sizes=hidden_layer_sizes,
            max_iter=max_iter,
            random_state=random_state,
            **kwargs,
        )

    def to_numpy_arrays(self, X: Any) -> np.ndarray:
        """Coerce input to a 2D numpy array of shape (n_samples, n_features)."""
        X_arr = np.asarray(X)
        if X_arr.ndim != 2:
            raise ValueError("X must be a 2D array of shape (n_samples, n_features)")
        return X_arr

    def fit(self, X: Any, y: Any) -> "MLPClassifierWrapper":
        X_arr = self.to_numpy_arrays(X)
        y_arr = np.asarray(y).ravel()
        self.model.fit(X_arr, y_arr)
        return self

    def predict(self, X: Any) -> np.ndarray:
        X_arr = self.to_numpy_arrays(X)
        return self.model.predict(X_arr)

    def predict_proba(self, X: Any) -> np.ndarray:
        X_arr = self.to_numpy_arrays(X)
        return self.model.predict_proba(X_arr)

    def score(self, X: Any, y: Any) -> float:
        X_arr = self.to_numpy_arrays(X)
        y_arr = np.asarray(y).ravel()
        return self.model.score(X_arr, y_arr)

    def save_model(self, path: str) -> None:
        """Persist the underlying scikit-learn model to disk."""
        dump(self.model, path)

    @staticmethod
    def load_model(path: str) -> "MLPClassifierWrapper":
        """Load a saved scikit-learn MLPClassifier and return a wrapper around it."""
        model = load(path)
        wrapper = MLPClassifierWrapper()
        wrapper.model = model
        # Attempt to restore meta attributes if available
        wrapper.hidden_layer_sizes = getattr(model, "hidden_layer_sizes", wrapper.hidden_layer_sizes)
        wrapper.max_iter = getattr(model, "max_iter", wrapper.max_iter)
        wrapper.random_state = getattr(model, "random_state", wrapper.random_state)
        return wrapper

    def __repr__(self) -> str:
        return (
            f"MLPClassifierWrapper(hidden_layer_sizes={self.hidden_layer_sizes}, "
            f"max_iter={self.max_iter}, random_state={self.random_state})"
        )
