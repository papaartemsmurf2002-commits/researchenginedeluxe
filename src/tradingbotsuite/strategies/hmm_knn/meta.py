from __future__ import annotations

import pandas as pd


def compare_knn_and_meta(frame: pd.DataFrame) -> dict[str, int | float]:
    if frame.empty:
        return {"knn_accepted_count": 0, "meta_accepted_count": 0, "meta_retention_rate": 0.0}
    knn = frame["accepted_by_knn"].astype(bool) if "accepted_by_knn" in frame.columns else pd.Series([False] * len(frame))
    meta = frame["accepted_by_meta"].astype(bool) if "accepted_by_meta" in frame.columns else pd.Series([False] * len(frame))
    knn_count = int(knn.sum())
    meta_count = int(meta.sum())
    return {
        "knn_accepted_count": knn_count,
        "meta_accepted_count": meta_count,
        "meta_retention_rate": float(meta_count / max(knn_count, 1)),
    }
