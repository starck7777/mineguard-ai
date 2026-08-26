export const sensorNodeDimensions={
  units:'mm',
  enclosure:{width:150,height:110,depth:80,wall:3},
  solarPanel:{width:140,height:90,depth:8},
  electronicsTray:{width:125,depth:65,layerSpacing:18},
  batteryCompartment:{width:72,height:24,depth:42},
  cableGland:{diameter:12,length:18},
  groundStake:{length:300,width:18,depth:12},
  sensorPlate:{width:120,depth:65,thickness:5},
  moistureProbe:{length:160,width:22,depth:3,soilDepth:130},
  tofBracket:{height:55,armLength:42},
  antenna:{length:165,diameter:8},
  mountingScrew:{diameter:4,length:16},
  maximumExplodedSpacing:60,
}as const;
export type SensorNodeDimensions=typeof sensorNodeDimensions;
