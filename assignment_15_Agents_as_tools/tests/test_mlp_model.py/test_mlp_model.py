import numpy as np

import pytest
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

from mlp_classifier import MLPClassifierWrapper


def test_fit_predict_shapes():
    X, y = make_classification(n_samples=200, n_features=20, n_informative=15, n_classes=2, random_state=0)
    model = MLPClassifierWrapper(hidden_layer_sizes=(10,), max_iter=200, random_state=0)
    model.fit(X, y)
    preds = model.predict(X[:5])
    assert preds.shape == (5,)


def test_score_requires_good_accuracy_on_split():
    X, y = make_classification(n_samples=400, n_features=20, n_informative=15, n_classes=2, random_state=42, n_redundant=0)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.5, random_state=42)
    model = MLPClassifierWrapper(hidden_layer_sizes=(20,), max_iter=200, random_state=42)
    model.fit(X_train, y_train)
    acc = model.score(X_test, y_test)
    assert acc > 0.7


def test_save_and_load_consistency(tmp_path):
    X, y = make_classification(n_samples=150, n_features=20, n_informative=15, n_classes=2, random_state=0)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
    model = MLPClassifierWrapper(hidden_layer_sizes=(20,), max_iter=200, random_state=0)
    model.fit(X_train, y_train)
    preds_before = model.predict(X_test)
    save_path = tmp_path / "mlp_model.joblib"
    model.save_model(str(save_path))

    loaded = MLPClassifierWrapper.load_model(str(save_path))
    preds_after = loaded.predict(X_test)

    assert preds_before.shape == preds_after.shape
    assert (preds_before == preds_after).all()
