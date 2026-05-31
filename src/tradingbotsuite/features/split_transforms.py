from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pandas as pd

from tradingbotsuite.backtesting.splits import (
    WalkForwardSplit,
    training_positions_for_split,
    validation_positions_for_split,
)
from tradingbotsuite.features.preprocessing import TrainOnlyFeaturePreprocessor, fit_train_only_preprocessor


@dataclass(frozen=True, slots=True)
class SplitTransformResult:
    split_id: str
    preprocessor: TrainOnlyFeaturePreprocessor
    train_matrix: pd.DataFrame
    validation_matrix: pd.DataFrame

    def to_payload(self) -> dict[str, object]:
        return {
            "split_id": self.split_id,
            "fit_scope": "train_only",
            "train_row_count": len(self.train_matrix),
            "validation_row_count": len(self.validation_matrix),
            "preprocessor": self.preprocessor.to_payload(),
            "research_only": True,
            "observe_only": True,
            "promotion_ready": False,
        }


def fit_transform_split_train_only(
    feature_frame: pd.DataFrame,
    split: WalkForwardSplit,
    *,
    feature_columns: Sequence[str],
) -> SplitTransformResult:
    ordered = feature_frame.reset_index(drop=True)
    train_positions = training_positions_for_split(split, row_count=len(ordered))
    validation_positions = validation_positions_for_split(split, row_count=len(ordered))
    if not train_positions:
        train = ordered.iloc[0:0].copy()
    else:
        train = ordered.iloc[train_positions].copy()
    validation = ordered.iloc[validation_positions].copy()
    preprocessor = fit_train_only_preprocessor(train, feature_columns)
    return SplitTransformResult(
        split_id=split.split_id,
        preprocessor=preprocessor,
        train_matrix=preprocessor.transform(train),
        validation_matrix=preprocessor.transform(validation),
    )
