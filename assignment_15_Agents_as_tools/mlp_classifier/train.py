"""train.py - simple CLI to train the wrapped MLP on synthetic data."""

from __future__ import annotations

from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split

from mlp_classifier import MLPClassifierWrapper


def main() -> None:
    # Generate a compact synthetic dataset
    X, y = make_classification(
        n_samples=300,
        n_features=20,
        n_informative=15,
        n_classes=2,
        random_state=42,
    )
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = MLPClassifierWrapper(hidden_layer_sizes=(20,), max_iter=300, random_state=42)
    model.fit(X_train, y_train)
    acc = model.score(X_test, y_test)
    print(f"Training complete. Test accuracy: {acc:.4f}")


if __name__ == "__main__":
    main()
