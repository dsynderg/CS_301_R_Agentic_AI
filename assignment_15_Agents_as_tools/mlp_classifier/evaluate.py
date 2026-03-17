"""evaluate.py - evaluate a saved model on generated data or provided dataset."""

from __future__ import annotations

import argparse
from typing import Tuple
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, accuracy_score

from mlp_classifier import MLPClassifierWrapper


def _generate_dataset(n_samples: int, n_features: int, random_state: int = 0) -> Tuple[object, object]:
    X, y = make_classification(
        n_samples=n_samples,
        n_features=n_features,
        n_informative=max(2, int(n_features * 0.6)),
        n_classes=2,
        random_state=random_state,
    )
    return X, y


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a saved model.")
    parser.add_argument("--model-path", required=True, help="Path to the saved model (joblib)")
    parser.add_argument("--n-samples", type=int, default=200, help="Number of samples for synthetic evaluation data")
    parser.add_argument("--n-features", type=int, default=20, help="Number of features for synthetic evaluation data")
    parser.add_argument("--random-state", type=int, default=0, help="Random state for data generation")
    args = parser.parse_args()

    wrapper = MLPClassifierWrapper.load_model(args.model_path)

    X, y = _generate_dataset(args.n_samples, args.n_features, random_state=args.random_state)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.5, random_state=args.random_state)

    preds = wrapper.predict(X_test)
    acc = accuracy_score(y_test, preds)
    cm = confusion_matrix(y_test, preds)

    print(f"Evaluation results for model at: {args.model_path}")
    print(f"Accuracy: {acc:.4f}")
    print("Confusion matrix:")
    print(cm)


if __name__ == "__main__":
    main()
