"""Tests for Event Detection Engine — all 15 event types."""
import pytest
from app.services.event_engine import EventDetectionEngine, EVENT_CATALOG


def test_all_15_event_types_in_catalog():
    """Spec section 8: exact 15 event types."""
    expected = {
        "person_detected", "person_exited", "identity_verified", "identity_unknown",
        "loitering_warning", "loitering_critical", "zone_violation", "tailgating_detected",
        "sensor_mismatch", "identity_mismatch", "crowd_alert", "sudden_movement",
        "suspect_detected", "abandoned_object", "repeated_reappearance",
    }
    assert set(EVENT_CATALOG.keys()) == expected


def test_loitering_warning_trigger():
    """Spec: >120s → loitering_warning."""
    engine = EventDetectionEngine("TEST")
    ev = engine.check_loitering(1, "P003", "Carol Zhang", 0.88, "Z02", 150, 2, "Medium")
    assert ev is not None
    assert ev["event_type"] == "loitering_warning"
    assert ev["severity"] in ("L2", "L2+", "L3")


def test_loitering_critical_trigger():
    """Spec: >300s → loitering_critical."""
    engine = EventDetectionEngine("TEST")
    ev = engine.check_loitering(1, "P003", "Carol Zhang", 0.88, "Z02", 350, 3, "Medium")
    assert ev is not None
    assert ev["event_type"] == "loitering_critical"
    assert ev["severity"] == "L3"


def test_no_loitering_under_threshold():
    """No event below 120s."""
    engine = EventDetectionEngine("TEST")
    ev = engine.check_loitering(1, "P001", "Alice", 0.9, "Z01", 90, 1, "Low")
    assert ev is None


def test_suspect_detected_always_l3():
    """Spec: suspect_detected always L3."""
    engine = EventDetectionEngine("TEST")
    ev = engine.check_suspect_detected(4, "P004", "Dave Rostov", 0.91, "Z02")
    assert ev["event_type"] == "suspect_detected"
    assert ev["severity"] == "L3"
    assert ev["threat_score"] >= 0.81


def test_canonical_event_schema():
    """Spec section 8: canonical schema fields."""
    engine = EventDetectionEngine("V001")
    ev = engine.check_suspect_detected(4, "P004", "Dave Rostov", 0.91, "Z02")
    required_fields = ["event_id", "video_id", "event_type", "severity", "timestamp",
                        "persons_involved", "threat_score", "acknowledged"]
    for f in required_fields:
        assert f in ev, f"Missing field: {f}"


def test_event_id_format():
    """Spec: EVT_XXXX_NNNN format."""
    engine = EventDetectionEngine("V001")
    ev = engine.check_crowd_alert("Z03", 15, 10, 2)
    assert ev["event_id"].startswith("EVT_")


def test_tailgating_l3():
    engine = EventDetectionEngine("TEST")
    ev = engine.check_tailgating("Z02", [1, 2], 1)
    assert ev is not None
    assert ev["event_type"] == "tailgating_detected"
    assert ev["severity"] == "L3"


def test_abandoned_object_threshold():
    """Spec: >60s → abandoned_object."""
    engine = EventDetectionEngine("TEST")
    ev = engine.check_abandoned_object(10, "Z01", 70)
    assert ev is not None
    assert ev["event_type"] == "abandoned_object"

    no_ev = engine.check_abandoned_object(11, "Z01", 30)
    assert no_ev is None
