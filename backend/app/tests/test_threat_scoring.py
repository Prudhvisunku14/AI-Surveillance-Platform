"""Tests for threat scoring engine — spec feature vector verification."""
import pytest
import numpy as np
from app.services.threat_scoring import ThreatFeatures, ThreatScoringEngine, THRESHOLDS


def make_features(**kwargs):
    defaults = dict(
        identity_confidence=0.5, is_known_person=0, risk_level_encoded=1,
        zone_risk_encoded=2, loitering_duration_norm=0.0, sensor_corroborated=0,
        visit_count_1h_norm=0.0, velocity_anomaly_score=0.0, concurrent_events_count=0,
    )
    defaults.update(kwargs)
    return ThreatFeatures(**defaults)


def test_feature_vector_length():
    tf = make_features()
    assert len(tf.to_array()) == 9, "Spec requires exactly 9 features"


def test_l1_range():
    engine = ThreatScoringEngine()
    tf = make_features(risk_level_encoded=0, zone_risk_encoded=0, identity_confidence=0.9,
                        is_known_person=1)
    score, severity, _ = engine.score(tf)
    assert 0.0 <= score <= 1.0


def test_l3_override_suspect():
    """Spec: suspect_detected always L3 regardless of model score."""
    engine = ThreatScoringEngine()
    tf = make_features(risk_level_encoded=0, zone_risk_encoded=0)
    score, severity, _ = engine.score(tf, event_type="suspect_detected")
    assert severity == "L3", f"suspect_detected must be L3, got {severity}"
    assert score >= 0.81


def test_l3_override_tailgating():
    """Spec: tailgating_detected always L3."""
    engine = ThreatScoringEngine()
    tf = make_features(risk_level_encoded=0, zone_risk_encoded=0)
    score, severity, _ = engine.score(tf, event_type="tailgating_detected")
    assert severity == "L3"


def test_severity_thresholds():
    """Spec exact thresholds: 0-0.30=L1, 0.31-0.60=L2, 0.61-0.80=L2+, 0.81-1.0=L3."""
    engine = ThreatScoringEngine()
    assert engine._map_severity(0.15) == "L1"
    assert engine._map_severity(0.30) == "L1"
    assert engine._map_severity(0.45) == "L2"
    assert engine._map_severity(0.60) == "L2"
    assert engine._map_severity(0.70) == "L2+"
    assert engine._map_severity(0.80) == "L2+"
    assert engine._map_severity(0.85) == "L3"
    assert engine._map_severity(1.00) == "L3"


def test_loitering_norm_formula():
    """Spec: loitering_duration_norm = seconds / 300, capped at 1.0."""
    tf = make_features(loitering_duration_norm=min(450 / 300, 1.0))
    assert tf.loitering_duration_norm == 1.0

    tf2 = make_features(loitering_duration_norm=120 / 300)
    assert abs(tf2.loitering_duration_norm - 0.4) < 0.001


def test_visit_count_norm_formula():
    """Spec: visit_count_1h_norm = count / 10, capped at 1.0."""
    tf = make_features(visit_count_1h_norm=min(5 / 10, 1.0))
    assert tf.visit_count_1h_norm == 0.5


def test_explainability_present():
    """Every threat score must include explainability per spec."""
    engine = ThreatScoringEngine()
    tf = make_features(risk_level_encoded=2, zone_risk_encoded=3)
    score, severity, explain = engine.score(tf)
    assert "feature_contributions" in explain
    assert "dominant_factor" in explain
    assert len(explain["feature_contributions"]) == 9
