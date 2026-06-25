import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock the paho-mqtt module before importing drone_publisher
sys.modules['paho'] = MagicMock()
sys.modules['paho.mqtt'] = MagicMock()
sys.modules['paho.mqtt.client'] = MagicMock()

# Add device-simulator directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../device-simulator')))

import drone_publisher

@patch('builtins.print')
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

if __name__ == '__main__':
    unittest.main()
