"""Zone intelligence — polygon zones, occupancy, risk levels.
Reuses zone logic from repo detectors/zone_intrusion.py, extended per spec."""
import json
import os
import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Zone:
    id: str
    name: str
    points: List[List[int]]
    zone_type: str              # restricted / monitored / open
    risk_level: int             # 0-3 (zone_risk_encoded spec feature)
    max_occupancy: int
    allowed_categories: List[str]
    current_count: int = 0


# Default zones matching spec personas (P001-P005 access zones)
DEFAULT_ZONES = [
    Zone("Z01", "Lobby", [[50, 400], [750, 400], [750, 580], [50, 580]],
         "monitored", 1, 20, ["Employee", "Visitor", "Unknown"]),
    Zone("Z02", "Server Room / Lab A", [[0, 0], [400, 0], [400, 300], [0, 300]],
         "restricted", 3, 5, ["Employee"]),
    Zone("Z03", "Corridor", [[0, 0], [800, 0], [800, 600], [0, 600]],
         "monitored", 2, 10, ["Employee", "Visitor"]),
    Zone("Z04", "Exit", [[600, 400], [800, 400], [800, 600], [600, 600]],
         "monitored", 1, 5, ["Employee", "Visitor", "Unknown"]),
]


class ZoneManager:
    def __init__(self, zone_config_path: Optional[str] = None):
        if zone_config_path and os.path.exists(zone_config_path):
            self.zones = self._load_from_file(zone_config_path)
        else:
            self.zones = {z.id: z for z in DEFAULT_ZONES}

    def _load_from_file(self, path: str) -> dict:
        with open(path) as f:
            data = json.load(f)
        zones = {}
        for zd in data.get("zones", []):
            z = Zone(**zd)
            zones[z.id] = z
        return zones

    def point_in_zone(self, point: tuple, zone: Zone) -> bool:
        """Ray-casting polygon test — from existing repo zone_intrusion.py."""
        pts = np.array(zone.points, dtype=np.int32)
        return cv2.pointPolygonTest(pts, point, False) >= 0

    def get_zones_for_point(self, cx: int, cy: int) -> List[Zone]:
        return [z for z in self.zones.values() if self.point_in_zone((cx, cy), z)]

    def check_violation(self, cx: int, cy: int, person_category: str) -> List[dict]:
        violations = []
        for zone in self.zones.values():
            if self.point_in_zone((cx, cy), zone):
                if zone.zone_type == "restricted" and person_category not in zone.allowed_categories:
                    violations.append({"zone_id": zone.id, "zone_name": zone.name,
                                        "risk_level": zone.risk_level})
        return violations

    def update_occupancy(self, track_positions: List[tuple]) -> dict:
        for zone in self.zones.values():
            zone.current_count = 0
        for cx, cy in track_positions:
            for zone in self.zones.values():
                if self.point_in_zone((cx, cy), zone):
                    zone.current_count += 1
        return {zid: z.current_count for zid, z in self.zones.items()}

    def get_crowd_alerts(self) -> List[dict]:
        alerts = []
        for zone in self.zones.values():
            if zone.current_count > zone.max_occupancy:
                alerts.append({"zone_id": zone.id, "count": zone.current_count,
                                "max": zone.max_occupancy})
        return alerts

    def draw_zones(self, frame: np.ndarray) -> np.ndarray:
        """Draw zone overlays — from existing repo draw_zones, extended."""
        color_map = {"restricted": (0, 0, 255), "monitored": (255, 200, 0), "open": (0, 255, 0)}
        for zone in self.zones.values():
            color = color_map.get(zone.zone_type, (255, 255, 255))
            pts = np.array(zone.points, dtype=np.int32)
            overlay = frame.copy()
            cv2.fillPoly(overlay, [pts], (*color[::-1], 40))
            frame = cv2.addWeighted(overlay, 0.2, frame, 0.8, 0)
            cv2.polylines(frame, [pts], True, color, 2)
            cx_label = sum(p[0] for p in zone.points) // len(zone.points)
            cy_label = sum(p[1] for p in zone.points) // len(zone.points)
            label = f"{zone.id} ({zone.current_count}/{zone.max_occupancy})"
            cv2.putText(frame, label, (cx_label - 40, cy_label),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        return frame
