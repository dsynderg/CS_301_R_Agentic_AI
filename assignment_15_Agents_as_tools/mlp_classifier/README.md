# MLPClassifierWrapper
A minimal, reusable Python wrapper around scikit-learn's MLPClassifier.

## Features
- Lightweight API: fit, predict, predict_proba, score
- Save and load model for end-to-end persistence
- Deterministic defaults for reproducible results
- Small, synthetic-data oriented training and evaluation utilities

## Installation
- Python 3.11+
- Requirements (dependencies are lightweight):
  - numpy
  - scikit-learn

Install dependencies:

pip install -r requirements.txt

## Quickstart

```python
from mlp_classifier import MLPClassifierWrapper
import numpy as np
from sklearn.datasets import make_classification

# Create a small synthetic dataset
X, y = make_classification(n_samples=200, n_features=20, n_informative=15, n_classes=2, random_state=0)
X_train, X_test, y_train, y_test = __import__('sklearn').model_selection.train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Initialize and train the wrapper
model = MLPClassifierWrapper(hidden_layer_sizes=(20,), max_iter=300, random_state=42)
model.fit(X_train, y_train)

# Predict on new data
preds = model.predict(X_test)
print("Predictions shape:", preds.shape)
print("Accuracy:", model.score(X_test, y_test))

# Persist and reload
model.save_model("mlp_model.joblib")
loaded = MLPClassifierWrapper.load_model("mlp_model.joblib")
print("Loaded model predictions equal: ", (loaded.predict(X_test) == preds).all())
```

## CLI utilities
- Train: python -m mlp_classifier.train
- Evaluate: python -m mlp_classifier.evaluate --model-path mlp_model.joblib

## Tests
A small pytest suite is included at tests/test_mlp_model.py to validate core functionality.
