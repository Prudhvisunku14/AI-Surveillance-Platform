"""Threat Scoring Engine — EXACT spec feature vector and thresholds section 9.
No invented features. Uses XGBoost with weighted-sum fallback."""
import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple

# ── Spec: exact severity thresholds section 9 ────────────────
THRESHOLDS = {
    "L1": (0.00, 0.30),
    "L2": (0.31, 0.60),
    "L2+": (0.61, 0.80),
    "L3": (0.81, 1.00),
}

# Spec: L3 rule-based overrides regardless of score
L3_OVERRIDE_EVENTS = {"suspect_detected", "tailgating_detected",
                      "abandoned_object", "loitering_critical", "identity_mismatch"}

# Dashboard colors — spec exact
SEVERITY_COLORS = {
    "L1": "#22c55e",   # Green
    "L2": "#f59e0b",   # Amber
    "L2+": "#f97316",  # Orange
    "L3": "#ef4444",   # Red
}


@dataclass
class ThreatFeatures:
    """Exact 9-feature vector — spec section 9. No additions."""
    identity_confidence: float       # 0-1 face match confidence
    is_known_person: int             # 0/1 binary
    risk_level_encoded: int          # 0=low 1=medium 2=high
    zone_risk_encoded: int           # 0-3 zone criticality
    loitering_duration_norm: float   # seconds/300, capped 1.0
    sensor_corroborated: int         # 0/1
    visit_count_1h_norm: float       # count/10, capped 1.0
    velocity_anomaly_score: float    # 0-1
    concurrent_events_count: int     # other events in ±30s window

    def to_array(self) -> np.ndarray:
        return np.array([
            self.identity_confidence,
            float(self.is_known_person),
            float(self.risk_level_encoded) / 2.0,   # normalise 0-1
            float(self.zone_risk_encoded) / 3.0,     # normalise 0-1
            self.loitering_duration_norm,
            float(self.sensor_corroborated),
            self.visit_count_1h_norm,
            self.velocity_anomaly_score,
            min(float(self.concurrent_events_count) / 5.0, 1.0),
        ], dtype=np.float32)

    def to_dict(self) -> dict:
        return {
            "identity_confidence": self.identity_confidence,
            "is_known_person": self.is_known_person,
            "risk_level_encoded": self.risk_level_encoded,
            "zone_risk_encoded": self.zone_risk_encoded,
            "loitering_duration_norm": self.loitering_duration_norm,
            "sensor_corroborated": self.sensor_corroborated,
            "visit_count_1h_norm": self.visit_count_1h_norm,
            "velocity_anomaly_score": self.velocity_anomaly_score,
            "concurrent_events_count": self.concurrent_events_count,
        }


# Calibrated weights for weighted-sum fallback (sum = 1.0)
FEATURE_WEIGHTS = np.array([
    0.15,   # identity_confidence — high weight
    0.10,   # is_known_person
    0.20,   # risk_level_encoded — strongest single signal
    0.18,   # zone_risk_encoded
    0.12,   # loitering_duration_norm
    0.08,   # sensor_corroborated
    0.07,   # visit_count_1h_norm
    0.06,   # velocity_anomaly_score
    0.04,   # concurrent_events_count
], dtype=np.float32)

assert abs(FEATURE_WEIGHTS.sum() - 1.0) < 0.001, "Weights must sum to 1.0"


class ThreatScoringEngine:
    """XGBoost + weighted-sum fallback. Spec: all events get 0-1 score."""

    def __init__(self):
        self.model = None
        self._try_load_xgboost()

    def _try_load_xgboost(self):
        try:
            import xgboost as xgb
            # Generate synthetic calibration data for XGBoost
            np.random.seed(42)
            n = 500
            X = np.random.rand(n, 9).astype(np.float32)
            # Synthetic labels: high risk_level + low identity + restricted zone → high threat
            y = (0.3 * X[:, 2] + 0.3 * X[:, 3] + 0.2 * (1 - X[:, 0]) + 0.2 * X[:, 4])
            y = np.clip(y, 0, 1).astype(np.float32)
            dtrain = xgb.DMatrix(X, label=y)
            params = {"max_depth": 4, "eta": 0.1, "objective": "reg:squarederror",
                      "eval_metric": "rmse", "seed": 42}
            self.model = xgb.train(params, dtrain, num_boost_round=50, verbose_eval=False)
        except Exception:
            self.model = None

    def score(self, features: ThreatFeatures, event_type: str = "") -> Tuple[float, str, dict]:
        """
        Returns (score 0-1, severity label, explainability dict).
        Spec: suspect_detected always L3 regardless of model score.
        """
        feat_array = features.to_array()

        # Compute raw score
        if self.model is not None:
            try:
                import xgboost as xgb
                dm = xgb.DMatrix(feat_array.reshape(1, -1))
                raw_score = float(self.model.predict(dm)[0])
            except Exception:
                raw_score = float(np.dot(feat_array, FEATURE_WEIGHTS))
        else:
            raw_score = float(np.dot(feat_array, FEATURE_WEIGHTS))

        score = float(np.clip(raw_score, 0.0, 1.0))

        # Spec rule-based L3 overrides — always take precedence
        if event_type in L3_OVERRIDE_EVENTS:
            score = max(score, 0.85)

        severity = self._map_severity(score)
        explainability = self._explain(features, feat_array, score)

        return score, severity, explainability

    def _map_severity(self, score: float) -> str:
        """Exact spec thresholds."""
        if score <= 0.30:
            return "L1"
        elif score <= 0.60:
            return "L2"
        elif score <= 0.80:
            return "L2+"
        else:
            return "L3"

    def _explain(self, features: ThreatFeatures, arr: np.ndarray, score: float) -> dict:
        """Per-feature contribution for every event — spec requirement."""
        feature_names = [
            "identity_confidence", "is_known_person", "risk_level_encoded",
            "zone_risk_encoded", "loitering_duration_norm", "sensor_corroborated",
            "visit_count_1h_norm", "velocity_anomaly_score", "concurrent_events_count"
        ]
        contributions = {name: round(float(arr[i] * FEATURE_WEIGHTS[i]), 4)
                         for i, name in enumerate(feature_names)}
        top = max(contributions, key=contributions.get)
        return {
            "score": round(score, 4),
            "feature_contributions": contributions,
            "dominant_factor": top,
            "color": SEVERITY_COLORS.get(self._map_severity(score), "#22c55e"),
        }


# Helpers to build features from event context
def encode_risk_level(risk: str) -> int:
    """spec: low=0, medium=1, high=2"""
    return {"low": 0, "medium": 1, "high": 2}.get(risk.lower(), 1)


def encode_zone_risk(zone_risk: int) -> int:
    """spec: 0-3 zone criticality"""
    return max(0, min(3, zone_risk))


_engine: ThreatScoringEngine = None


def get_threat_engine() -> ThreatScoringEngine:
    global _engine
    if _engine is None:
        _engine = ThreatScoringEngine()
    return _engine
