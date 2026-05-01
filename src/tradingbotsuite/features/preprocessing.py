from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class TrainOnlyFeaturePreprocessor:
    columns: tuple[str, ...]
    median: tuple[float, ...]
    scale: tuple[float, ...]
    fit_row_count: int
    fit_scope: str = "train_only"
    imputation_policy: str = "explicit_missingness_plus_train_only_neutral"

    def transform(self, frame: pd.DataFrame, *, include_missing_indicators: bool = True) -> pd.DataFrame:
        matrix = _numeric_feature_matrix(frame, self.columns)
        missing = ~np.isfinite(matrix)
        median = np.asarray(self.median, dtype=float).reshape(1, -1)
        scale = np.asarray(self.scale, dtype=float).reshape(1, -1)
        transformed = (np.where(missing, median, matrix) - median) / scale
        result = pd.DataFrame(transformed, columns=list(self.columns), index=frame.index)
        if include_missing_indicators:
            for column_index, column in enumerate(self.columns):
                result[f"missing_{column}"] = missing[:, column_index].astype(int)
        return result

    def to_payload(self) -> dict[str, object]:
        return {
            "columns": list(self.columns),
            "median": list(self.median),
            "scale": list(self.scale),
            "fit_row_count": int(self.fit_row_count),
            "fit_scope": self.fit_scope,
            "imputation_policy": self.imputation_policy,
        }


def fit_train_only_preprocessor(
    train_frame: pd.DataFrame,
    feature_columns: Sequence[str],
) -> TrainOnlyFeaturePreprocessor:
    columns = tuple(str(column) for column in feature_columns)
    if not columns:
        raise ValueError("feature_columns must not be empty")
    matrix = _numeric_feature_matrix(train_frame, columns)
    median = _nan_stat_by_column(matrix, "median")
    q75 = _nan_stat_by_column(matrix, "q75")
    q25 = _nan_stat_by_column(matrix, "q25")
    scale = q75 - q25
    scale = np.where(np.isfinite(scale) & (scale > 0), scale, 1.0)
    return TrainOnlyFeaturePreprocessor(
        columns=columns,
        median=tuple(float(value) for value in median),
        scale=tuple(float(value) for value in scale),
        fit_row_count=int(len(train_frame)),
    )


def _numeric_feature_matrix(frame: pd.DataFrame, columns: Sequence[str]) -> np.ndarray:
    matrix_frame = frame.reindex(columns=list(columns)).apply(pd.to_numeric, errors="coerce")
    matrix = matrix_frame.to_numpy(dtype=float, copy=True)
    matrix[~np.isfinite(matrix)] = np.nan
    return matrix


def _nan_stat_by_column(matrix: np.ndarray, statistic: str) -> np.ndarray:
    values: list[float] = []
    for column_index in range(matrix.shape[1]):
        column = matrix[:, column_index]
        column = column[np.isfinite(column)]
        if len(column) == 0:
            values.append(0.0)
        elif statistic == "median":
            values.append(float(np.median(column)))
        elif statistic == "q75":
            values.append(float(np.percentile(column, 75)))
        elif statistic == "q25":
            values.append(float(np.percentile(column, 25)))
        else:  # pragma: no cover - internal guard
            raise ValueError(f"unsupported statistic {statistic}")
    return np.asarray(values, dtype=float)
