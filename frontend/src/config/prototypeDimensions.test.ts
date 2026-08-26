import {describe,expect,it} from 'vitest';
import {prototypeDimensions} from './prototypeDimensions';

describe('prototype safety dimensions',()=>{
  it('keeps visual settlement within the documented demonstration limit',()=>{
    expect(prototypeDimensions.maxSettlement).toBe(20);
    expect(prototypeDimensions.surfaceTray.width).toBeLessThan(prototypeDimensions.enclosure.width);
  });
});
