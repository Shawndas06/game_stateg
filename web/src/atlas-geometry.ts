import type {Catalog} from './types';

export type Point = [number, number];
export type Polygon = Point[][];
export type Geography = {land: Polygon[]; lakes: Polygon[]; settlements?:Point[];precision_regions?:[number,number,number,number][];geometry_fingerprint?:string;coast_cache?:{geometry:string;values:number[]}};
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

/** Geographic anchors are immutable: label collisions must not move a city. */
export function layoutPlaces(places: Catalog['places'], view: Viewport, width: number, height: number): MapPlace[] {
  const visible = places.map(p => {
    const anchor = screenPoint(project(p.lon, p.lat), view, width, height);
    return {...p, anchor, position: [...anchor] as Point};
  }).filter(p => p.anchor[0] > 15 && p.anchor[0] < width - 15 && p.anchor[1] > 30 && p.anchor[1] < height - 30);
  return visible;
}

/** Reuse scanline intersections across terrain cells; polygon holes and lakes
 * retain the same even/odd containment rule as onLand. */
export function landSampler(geography: Geography): (lon:number,lat:number)=>boolean {
  const prepare=(polygons:Polygon[])=>polygons.map(rings=>({rings,south:Math.min(...rings[0].map(p=>p[1])),north:Math.max(...rings[0].map(p=>p[1]))}));
  const land=prepare(geography.land),lakes=prepare(geography.lakes);
  const rows=new Map<number,{land:number[][][];lakes:number[][][]}>();
  const cut=(polygons:ReturnType<typeof prepare>,lat:number)=>polygons.filter(p=>lat>=p.south&&lat<p.north).map(p=>p.rings.map(ring=>{
    const crossings:number[]=[];
    for(let i=0,j=ring.length-1;i<ring.length;j=i++){
      const [x,y]=ring[i],[px,py]=ring[j];
      if((y>lat)!==(py>lat))crossings.push((px-x)*(lat-y)/(py-y)+x);
    }
    return crossings.sort((a,b)=>a-b);
  }));
  const inside=(lon:number,edges:number[])=>{let i=0;while(i<edges.length&&edges[i]<=lon)i++;return i%2===1};
  const contains=(lon:number,polygons:number[][][])=>polygons.some(r=>inside(lon,r[0])&&!r.slice(1).some(h=>inside(lon,h)));
  return (lon,lat)=>{
    let row=rows.get(lat);
    if(!row){row={land:cut(land,lat),lakes:cut(lakes,lat)};if(rows.size>=512)rows.delete(rows.keys().next().value!);rows.set(lat,row)}
    return contains(lon,row.land)&&!contains(lon,row.lakes);
  };
}
