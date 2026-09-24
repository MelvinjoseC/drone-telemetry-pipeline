import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock the paho-mqtt module before importing drone_publisher
sys.modules["paho"] = MagicMock()
sys.modules["paho.mqtt"] = MagicMock()
sys.modules["paho.mqtt.client"] = MagicMock()

# Add device-simulator directory to path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../device-simulator"))
)

import drone_publisher  # noqa: E402


@patch("builtins.print")
class TestDroneSimulator(unittest.TestCase):
    def test_simulator_init(self, mock_print):
        simulator = drone_publisher.DroneSimulator()
        self.assertEqual(simulator.altitude, 0.0)
        self.assertEqual(simulator.speed, 0.0)
        self.assertEqual(simulator.battery, 100)
        self.assertEqual(simulator.flight_mode, "TAKEOFF")
        self.assertEqual(simulator.tick, 0)

    def test_takeoff_phase(self, mock_print):
        simulator = drone_publisher.DroneSimulator()

        # Tick 1: Takeoff
        telemetry = simulator.update()
        self.assertEqual(telemetry["flight_mode"], "TAKEOFF")
        self.assertGreater(telemetry["altitude_m"], 0.0)
        self.assertGreater(telemetry["speed_kmh"], 0.0)
        self.assertEqual(telemetry["status"], "flying")

    def test_cruise_phase(self, mock_print):
        simulator = drone_publisher.DroneSimulator()
        # Advance simulator past takeoff (ticks 1-5)
        for _ in range(6):
            telemetry = simulator.update()

        self.assertEqual(telemetry["flight_mode"], "AUTO")
        self.assertEqual(telemetry["status"], "flying")
        self.assertGreater(telemetry["battery_pct"], 0.0)
        self.assertLess(telemetry["battery_pct"], 100.0)

    def test_landing_phase(self, mock_print):
        simulator = drone_publisher.DroneSimulator()
        # Advance simulator past cruise (ticks 1-50) into landing (ticks 51-60)
        for _ in range(52):
            telemetry = simulator.update()

        self.assertEqual(telemetry["flight_mode"], "LANDING")

    def test_reset_phase(self, mock_print):
        simulator = drone_publisher.DroneSimulator()
        # Advance simulator to reset point (exactly 61 updates)
        for _ in range(61):
            telemetry = simulator.update()

        # Should reset back to TAKEOFF with tick = 0
        self.assertEqual(telemetry["flight_mode"], "TAKEOFF")
        self.assertEqual(simulator.tick, 0)
        self.assertEqual(telemetry["battery_pct"], 100.0)

    def test_fleet_simulator(self, mock_print):
        fleet = drone_publisher.FleetSimulator(
            drone_ids=["DRONE-ALPHA", "DRONE-BRAVO"], fleet_size=2
        )
        self.assertEqual(len(fleet.drones), 2)
        self.assertEqual(fleet.drones[0].drone_id, "DRONE-ALPHA")
        self.assertEqual(fleet.drones[1].drone_id, "DRONE-BRAVO")

        records = fleet.update_all()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["drone_id"], "DRONE-ALPHA")
        self.assertEqual(records[1]["drone_id"], "DRONE-BRAVO")

    def test_waypoint_navigation_and_distance(self, mock_print):
        from scenarios import (
            Waypoint,
            WaypointNavigator,
            build_perimeter_patrol,
            calculate_bearing,
            haversine_distance,
        )

        dist = haversine_distance(10.8505, 76.2711, 10.8515, 76.2711)
        self.assertGreater(dist, 100.0)
        self.assertLess(dist, 120.0)

        bearing = calculate_bearing(10.8505, 76.2711, 10.8550, 76.2711)
        self.assertAlmostEqual(bearing, 0.0, delta=1.0)

        waypoints = [
            Waypoint(10.8505, 76.2711, altitude_m=30.0, speed_kmh=20.0),
            Waypoint(10.8510, 76.2711, altitude_m=50.0, speed_kmh=30.0),
        ]
        navigator = WaypointNavigator(waypoints)
        new_lat, new_lon, new_alt, speed, hdg, finished = navigator.step(
            10.8505, 76.2711, 0.0, interval_seconds=1.0
        )
        self.assertFalse(finished)
        self.assertGreater(new_alt, 0.0)

        patrol_wps = build_perimeter_patrol(10.8505, 76.2711)
        self.assertEqual(len(patrol_wps), 6)


if __name__ == "__main__":
    unittest.main()
