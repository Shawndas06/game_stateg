"""Offline GSHHG high-resolution extraction; no GIS dependency in the game.

Run in a temporary environment with Shapely, passing the basemap-data-hires
2.0.0 wheel from PyPI. Its binary polygons derive from GSHHG 2.3.7 (LGPL).
Coordinates are never adjusted to accommodate settlement markers.
"""
import argparse
import hashlib
import json
import struct
import zipfile
import sys
from pathlib import Path
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from campaign.content import PLACES

def build(wheel):
    bounds=box(-11,22,44.5,50.5)
    detailed=unary_union([box(p[2]-.04,p[3]-.04,p[2]+.04,p[3]+.04) for p in PLACES]+[box(28.7,40.8,29.3,41.3)])
    layers={}
    with zipfile.ZipFile(wheel) as archive:
        for resolution in ['h','f']:
            levels={i:[] for i in range(1,5)};clip=bounds if resolution=='h' else detailed
            raw=archive.read(f'mpl_toolkits/basemap_data/gshhs_{resolution}.dat')
            for line in archive.read(f'mpl_toolkits/basemap_data/gshhsmeta_{resolution}.dat').decode().splitlines():
                level,area,n,south,north,offset,size,*_=line.split();level=int(level)
                if level not in levels or float(south)>50.5 or float(north)<22:continue
                coords=list(struct.iter_unpack('<ff',raw[int(offset):int(offset)+int(size)]))
                if max(p[0] for p in coords)<-11 or min(p[0] for p in coords)>44.5:continue
                p=Polygon(coords)
                if not p.is_valid:p=p.buffer(0)
                p=p.intersection(clip)
                if not p.is_empty:levels[level].append(p)
            islands=unary_union(levels[3]);layers[resolution]={'land':unary_union(levels[1]).union(islands),'lakes':unary_union(levels[2]).difference(islands).union(unary_union(levels[4]))}
        licenses=ROOT/'docs'/'licenses';licenses.mkdir(exist_ok=True)
        for name in ['COPYING','COPYING.LESSER']:
            (licenses/('GSHHG-'+name)).write_bytes(archive.read('basemap_data_hires-2.0.0.dist-info/licenses/'+name))
    def polygons(g):
        if g.geom_type=='Polygon':yield g
        elif hasattr(g,'geoms'):
            for part in g.geoms:yield from polygons(part)
    def encode(g):
        return [[[[round(x,6),round(y,6)] for x,y in ring.coords] for ring in [p.exterior,*p.interiors]] for p in polygons(g.simplify(.00004,preserve_topology=True))]
    result={key:encode(layers['h'][key].difference(detailed).union(layers['f'][key])) for key in ['land','lakes']}
    # Independent surveyed islands/peninsulas, rather than buffers around towns.
    lake_file=ROOT/'web/public/lake-corrections.json'
    if lake_file.exists():
        replacements=[Polygon(p[0],p[1:]) for item in json.loads(lake_file.read_text())['lakes'] for p in item['polygons']]
        regions=unary_union([box(*p.buffer(.02).bounds) for p in replacements])
        old=unary_union([Polygon(p[0],p[1:]) for p in result['lakes']])
        result['lakes']=encode(old.difference(regions).union(unary_union(replacements)))
    protection={'settlements':[list(p[2:4]) for p in PLACES],
                'precision_regions':[[28.7,40.8,29.3,41.3],[26.3,40.1,26.95,40.6]]}
    (ROOT/'web/public/map-sites.json').write_text(json.dumps(protection,separators=(',',':')))
    target=ROOT/'web/public/mediterranean-geography.json';target.write_text(json.dumps(result,separators=(',',':')))
    print('Input SHA256',hashlib.sha256(Path(wheel).read_bytes()).hexdigest(),'output bytes',target.stat().st_size)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('wheel');build(parser.parse_args().wheel)
