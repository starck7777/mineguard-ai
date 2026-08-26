# Tabletop prototype build

Build a 600 × 400 × 350 mm acrylic/plywood enclosure around a removable 500 × 300 mm soil tray. Below the tray, mount a 120 mm cavity and a guided platform on two linear rails. Couple an 8 mm lead screw to a NEMA17 through a flexible coupler. Fit normally-closed upper/lower limits and a latching emergency stop. Mount the direct ToF displacement sensor to a rigid reference frame, not the moving soil.

Use a fused, current-limited 12 V motor supply separate from the ESP32 supply. The A4988 current limit must be set before attaching the motor. Start with the mechanism uncoupled, verify direction and both limits, then enforce the 20 mm software travel limit. The controller is disabled after every boot and requires deliberate arming.

The four displayed nodes include one intended physical node and three virtual nodes. Until genuine telemetry arrives, all are explicitly labelled SIMULATED.

## Sensor-node assembly order

1. Drive the pointed stake to the chosen marked depth and lock the adjustable enclosure bracket.
2. Bolt the ground-coupled plate rigidly to the stake/platform. Fasten the MPU6050 and ADXL345 to this plate.
3. Install the optional load cell beneath the movable demonstration pressure plate and attach its HX711 interface.
4. Insert the capacitive probe below ground through protected cable routing. Treat its output as a calibrated relative soil-moisture trend.
5. Mount the VL53L1X to the fixed reference bracket with an unobstructed sightline to the moving reference plate. Displacement comes from this changing distance, not MPU6050 acceleration integration.
6. Fit the enclosure mounting tray, sensor-interface board, LoRa board, ESP32, protected battery holder, BMS/regulator and solar charge controller from bottom to top.
7. Route cables through glands, attach the external antenna, ventilated SHT31 cap, protected buzzer outlet and warning beacon.
8. Seat the lid gasket, install four lid screws, attach the adjustable solar bracket and connect the panel last.

The interactive and printable exploded views use `sensor_node_dimensions.json` and `sensor-node-exploded.svg` as documentation references.
