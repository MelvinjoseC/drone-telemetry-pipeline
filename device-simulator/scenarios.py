"""
scenarios.py
────────────────────────────────────────────────────────
Flight scenarios and waypoint navigation engine for drone
telemetry simulation.

Provides realistic flight profiles:
- Perimeter Patrol (surveillance / boundary inspection)
- Point-to-point Delivery (transit, cargo drop, RTL)
- Emergency Return-to-Launch (failsafe response)

Author: Melvin Chacko Jose
────────────────────────────────────────────────────────
"""

import math
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Waypoint:
    lat: float
    lon: float
    altitude_m: float
    speed_kmh: float
    hover_seconds: float = 0.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth in meters.
    """
    earth_radius_m = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return earth_radius_m * c


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate initial compass bearing from start to destination in degrees (0 - 360).
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    x = math.sin(delta_lambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - (
        math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    )
    initial_bearing = math.atan2(x, y)
    bearing_deg = (math.degrees(initial_bearing) + 360.0) % 360.0
    return round(bearing_deg, 1)


class WaypointNavigator:
    """
    Sequences a drone through an ordered list of waypoints.
    Updates GPS coordinates, altitude, heading, and speed on each step.
    """

    def __init__(self, waypoints: List[Waypoint]):
        if not waypoints:
            raise ValueError("Waypoints list cannot be empty.")
        self.waypoints = waypoints
        self.current_idx = 0
        self.is_completed = False

    def step(
        self,
        current_lat: float,
        current_lon: float,
        current_alt: float,
        interval_seconds: float,
    ) -> Tuple[float, float, float, float, float, bool]:
        """
        Advance position towards current target waypoint.

        Returns (new_lat, new_lon, new_alt, new_speed, new_heading, reached_destination).
        """
        if self.is_completed:
            target = self.waypoints[-1]
            return (
                target.lat,
                target.lon,
                target.altitude_m,
                0.0,
                0.0,
                True,
            )

        target = self.waypoints[self.current_idx]
        dist_to_target = haversine_distance(
            current_lat, current_lon, target.lat, target.lon
        )
        bearing = calculate_bearing(current_lat, current_lon, target.lat, target.lon)

        speed_ms = (target.speed_kmh * 1000.0) / 3600.0
        step_dist = speed_ms * interval_seconds

        # Check if waypoint reached
        if dist_to_target <= step_dist or dist_to_target < 2.0:
            new_lat = target.lat
            new_lon = target.lon
            new_alt = target.altitude_m
            self.current_idx += 1
            if self.current_idx >= len(self.waypoints):
                self.is_completed = True
            return (
                new_lat,
                new_lon,
                new_alt,
                target.speed_kmh,
                bearing,
                self.is_completed,
            )

        # Move intermediate distance along bearing
        rad_bearing = math.radians(bearing)
        delta_lat = (step_dist * math.cos(rad_bearing)) / 111320.0
        delta_lon = (step_dist * math.sin(rad_bearing)) / (
            111320.0 * math.cos(math.radians(current_lat))
        )

        new_lat = current_lat + delta_lat
        new_lon = current_lon + delta_lon

        # Climb / descend towards target altitude
        alt_diff = target.altitude_m - current_alt
        alt_step = min(abs(alt_diff), 3.0 * interval_seconds) * (
            1 if alt_diff >= 0 else -1
        )
        new_alt = max(0.0, current_alt + alt_step)

        return (
            new_lat,
            new_lon,
            new_alt,
            target.speed_kmh,
            bearing,
            False,
        )


def build_perimeter_patrol(start_lat: float, start_lon: float) -> List[Waypoint]:
    """Build a rectangular perimeter inspection path."""
    return [
        Waypoint(start_lat, start_lon, altitude_m=30.0, speed_kmh=15.0),
        Waypoint(start_lat + 0.003, start_lon, altitude_m=60.0, speed_kmh=35.0),
        Waypoint(
            start_lat + 0.003,
            start_lon + 0.004,
            altitude_m=60.0,
            speed_kmh=40.0,
        ),
        Waypoint(start_lat, start_lon + 0.004, altitude_m=50.0, speed_kmh=35.0),
        Waypoint(start_lat, start_lon, altitude_m=10.0, speed_kmh=15.0),
        Waypoint(start_lat, start_lon, altitude_m=0.0, speed_kmh=0.0),
    ]


def build_delivery_mission(start_lat: float, start_lon: float) -> List[Waypoint]:
    """Build a point-to-point delivery and return mission."""
    dest_lat = start_lat + 0.008
    dest_lon = start_lon + 0.006
    return [
        Waypoint(start_lat, start_lon, altitude_m=20.0, speed_kmh=10.0),
        Waypoint(
            start_lat + 0.002,
            start_lon + 0.001,
            altitude_m=80.0,
            speed_kmh=50.0,
        ),
        Waypoint(dest_lat, dest_lon, altitude_m=80.0, speed_kmh=55.0),
        Waypoint(dest_lat, dest_lon, altitude_m=2.0, speed_kmh=5.0),  # Dropoff
        Waypoint(dest_lat, dest_lon, altitude_m=80.0, speed_kmh=40.0),  # Ascend
        Waypoint(start_lat, start_lon, altitude_m=60.0, speed_kmh=50.0),  # RTL
        Waypoint(start_lat, start_lon, altitude_m=0.0, speed_kmh=0.0),  # Touchdown
    ]
