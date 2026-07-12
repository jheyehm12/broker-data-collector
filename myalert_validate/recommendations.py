"""ML training recommendations derived from validation."""

from __future__ import annotations

from myalert_validate.schema import (
    EXCLUDE_FROM_TRAINING,
    RECOMMENDED_FEATURE_COLUMNS,
    SUGGESTED_TARGETS,
)


def build_recommendations() -> dict:
    return {
        "recommended_features": RECOMMENDED_FEATURE_COLUMNS,
        "exclude_from_training": EXCLUDE_FROM_TRAINING,
        "suggested_targets": {
            "classification": {
                "primary": "Outcome",
                "binary": ["TP Hit", "SL Hit", "First Reaction"],
                "notes": "For binary WIN vs LOSS, filter Outcome to WIN/LOSS only; exclude BOTH/NONE",
            },
            "regression": {
                "primary": "Final Forward Return",
                "secondary": ["MFE", "MAE"],
            },
        },
        "chronological_split": {
            "method": "per_symbol_timeframe_time_order",
            "train_fraction": 0.70,
            "validation_fraction": 0.15,
            "test_fraction": 0.15,
            "shuffle": False,
            "purge_rules": [
                "Exclude rows with Eligible For Training = 0",
                "Exclude INSUFFICIENT_FORWARD tail rows",
                "Never use outcome columns as features",
            ],
        },
        "baseline_models": [
            {
                "task": "Outcome WIN vs LOSS (binary)",
                "models": ["LogisticRegression", "RandomForestClassifier"],
                "notes": "Use class_weight balanced; metrics: precision/recall/F1",
            },
            {
                "task": "Outcome multiclass (WIN/LOSS/BOTH/NONE)",
                "models": ["RandomForestClassifier", "HistGradientBoostingClassifier"],
            },
            {
                "task": "Final Forward Return (regression)",
                "models": ["Ridge", "RandomForestRegressor"],
                "metrics": ["MAE", "RMSE", "R2"],
            },
        ],
        "feature_engineering_notes": [
            "Encode Asset Class, Session, Day of Week as categorical",
            "Prefer derived structure/relative features over raw OHLC",
            "Join outcomes only at train/label time via Symbol+Timeframe+Timestamp",
        ],
    }
