import{describe,expect,it}from'vitest';
import{sensorNodeDimensions as d}from'./sensorNodeDimensions';
describe('sensor node model dimensions',()=>{it('keeps safe editable prototype defaults',()=>{expect(d.enclosure).toMatchObject({width:150,height:110,depth:80});expect(d.solarPanel.width).toBe(140);expect(d.groundStake.length).toBe(300);expect(d.maximumExplodedSpacing).toBe(60);expect(d.moistureProbe.soilDepth).toBeLessThanOrEqual(d.moistureProbe.length)})});
