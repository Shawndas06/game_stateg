import type {Catalog} from './types';

export type Point = [number, number];
export type Polygon = Point[][];
export type Geography = {land: Polygon[]; lakes: Polygon[]};
export type Viewport = {x: number; y: number; width: number; height: number};

export const project = (lon: number, lat: number): Point => [(lon + 10) * 20, (50 - lat) * 23];

export function screenPoint(point: Point, view: Viewport, width: number, height: number): Point {
  return [(point[0] - view.x) / view.width * width, (point[1] - view.y) / view.height * height];
}

export function polygonPath(polygon: Polygon, view: Viewport, width: number, height: number): string {
  return polygon.map(ring => ring.map(([lon, lat], i) => {
    const [x, y] = screenPoint(project(lon, lat), view, width, height);
    return `${i ? 'L' : 'M'}${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(' ') + 'Z').join(' ');
}

function inRing(lon: number, lat: number, ring: Point[]): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [x, y] = ring[i], [px, py] = ring[j];
    if ((y > lat) !== (py > lat) && lon < (px - x) * (lat - y) / (py - y) + x) inside = !inside;
  }
  return inside;
}

export function onLand(lon: number, lat: number, geography: Geography): boolean {
  const contains = (polygons: Polygon[]) => polygons.some(p => inRing(lon, lat, p[0]) && !p.slice(1).some(r => inRing(lon, lat, r)));
  return contains(geography.land) && !contains(geography.lakes);
}

export type MapPlace = Catalog['places'][number] & {anchor: Point; position: Point};

/** Keep touch targets and labels separate; leader lines preserve geographic truth. */
export function layoutPlaces(places: Catalog['places'], view: Viewport, width: number, height: number): MapPlace[] {
  const visible = places.map(p => {
    const anchor = screenPoint(project(p.lon, p.lat), view, width, height);
    return {...p, anchor, position: [...anchor] as Point};
  }).filter(p => p.anchor[0] > 15 && p.anchor[0] < width - 15 && p.anchor[1] > 30 && p.anchor[1] < height - 30);
  for (let iteration = 0; iteration < 120; iteration++) {
    for (let i = 0; i < visible.length; i++) {
      const p = visible[i];
      p.position[0] += (p.anchor[0] - p.position[0]) * .008;
      p.position[1] += (p.anchor[1] - p.position[1]) * .008;
      for (let j = i + 1; j < visible.length; j++) {
        const q = visible[j];
        const dx = q.position[0] - p.position[0], dy = q.position[1] - p.position[1];
        const ox = 98 - Math.abs(dx), oy = 72 - Math.abs(dy);
        if (ox <= 0 || oy <= 0) continue;
        if (ox < oy) {
          const shift = (ox + .5) * .51 * (dx >= 0 ? 1 : -1);
          p.position[0] -= shift; q.position[0] += shift;
        } else {
          const shift = (oy + .5) * .51 * (dy >= 0 ? 1 : -1);
          p.position[1] -= shift; q.position[1] += shift;
        }
      }
      p.position[0] = Math.max(53, Math.min(width - 53, p.position[0]));
      p.position[1] = Math.max(63, Math.min(height - 105, p.position[1]));
    }
  }
  return visible;
}
