# Wiring and telemetry

Prototype only. Never power a NEMA17 from an ESP32. Use a separate fused 12 V motor supply and join logic grounds at one controlled common-ground point.

| Device | ESP32 pins / address |
|---|---|
| VL53L1X + MPU6050 | SDA 21, SCL 22; 0x29 and 0x68 |
| ADXL345 | shared I²C; 0x53 |
| SX1276/78 | SCK 18, MISO 19, MOSI 23, CS 5, RESET 14, DIO0 26 |
| Moisture | ADC 34 through 3.3 V-safe conditioning |
| Battery divider | ADC 35; calibrated divider, never exceed 3.3 V |
| Buzzer / LED | GPIO 27 / 25 through suitable driver/resistor |
| A4988 | STEP 16, DIR 17, ENABLE 4; separate motor controller firmware |
| Safety inputs | E-stop 32, upper limit 33, lower limit 13; normally closed preferred |

Calibrate the VL53L1X zero against the stationary platform, record moisture dry/wet references, verify the voltage-divider ratio with a multimeter, and test limit/E-stop inputs before coupling the motor. Firmware configuration is centralized in `firmware/common/config.h`.

Hardware posts the documented JSON payload to `/api/telemetry`; genuine packets must use `source_type: "real"`. Sequence IDs must persist across ordinary reconnects.

## Physical routing

Route the solar lead through the upper gland to the charge controller, then through reverse-polarity protection to the BMS. Restrain the protected 18650 cells in their holder; connect the regulator output to the ESP32 power input. Keep the SPI harness between ESP32 and SX1276/78 short and route the antenna coax directly to the external connector.

Route I²C to the fixed VL53L1X bracket, ground-coupled MPU6050/ADXL345 plate and ventilated SHT31 cap. Route moisture and battery-divider signals to their ADC inputs. The optional load cell sits beneath the demonstration pressure plate and connects through HX711. No harness should cross a solid wall: all external cables pass through the labelled glands.

RSSI and SNR are derived by the LoRa radio and must not be represented as separate physical sensors.
