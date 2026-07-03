import { describe, expect, it } from 'vitest';
import { filterGraphSearchResults } from './graphFilterUtils.js';

describe('graphFilterUtils', () => {
  it('filters by query', () => {
    const items = [{ title: 'Nickel plant', material: 'Ni', process: 'leach', geo: 'RU', geoKey: 'domestic' }];
    const result = filterGraphSearchResults(items, {
      query: 'nickel',
      material: 'all',
      process: 'all',
      geo: 'all',
    });
    expect(result).toHaveLength(1);
  });
});
