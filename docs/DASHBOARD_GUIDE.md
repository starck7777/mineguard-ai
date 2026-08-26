# MineGuard dashboard and hardware model

Open `/module-analytics` for module and sensor analytics. Selecting a sensor tile opens `/hardware-model-3d`, selects the same module and highlights the corresponding physical sensor. The shared WebSocket continues updating the selected node without a page refresh.

The hardware view offers the **Complete Mine Prototype** and **Sensor Node Exploded View** tabs. Controls cover assembled/exploded spacing, X-ray, cutaway, installation, camera presets, labels, wiring, dimensions, live values, risk overlays, quality, fullscreen and screenshot export.

Sensor halos represent individual backend-calculated sensor risk. Ground risk, hardware health, communication status and data quality remain separate. RSSI and SNR appear on the LoRa transceiver because they are radio measurements, not physical sensors.

The printable drawing is [sensor-node-exploded.svg](../hardware/sensor-node-exploded.svg). If WebGL is unavailable, the application presents a selectable 2D exploded view with live values.

> Prototype thresholds and hardware are for demonstration only and are not certified operational mine-safety equipment.
