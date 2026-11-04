"""Extract only public lake geometry from complete OSM relation XML files.

Usage: Python with Shapely; downloaded /api/0.6/relation/{id}/full files as args.
No contributor names, user IDs or unrelated map objects are retained.
"""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from shapely.geometry import LineString
from shapely.ops import polygonize, unary_union

def extract(path):
    root=ET.parse(path).getroot()
    nodes={n.attrib['id']:(float(n.attrib['lon']),float(n.attrib['lat'])) for n in root.findall('node')}
    ways={w.attrib['id']:[nodes[n.attrib['ref']] for n in w.findall('nd')] for w in root.findall('way')}
    result=[]
    for relation in root.findall('relation'):
        tags={t.attrib['k']:t.attrib['v'] for t in relation.findall('tag')}
        if tags.get('natural')!='water' or tags.get('water')!='lake':continue
        def rings(role):
            lines=[LineString(ways[m.attrib['ref']]) for m in relation.findall('member') if m.attrib['type']=='way' and m.attrib['role']==role]
            return unary_union(list(polygonize(unary_union(lines))))
        geom=rings('outer').difference(rings('inner'));assert geom.is_valid and not geom.is_empty
        polys=[geom] if geom.geom_type=='Polygon' else list(geom.geoms)
        result.append({'relation':relation.attrib['id'],'name':tags['name'],'version':relation.attrib['version'],
                       'polygons':[[[[round(x,6),round(y,6)] for x,y in r.coords] for r in [p.exterior,*p.interiors]] for p in polys]})
    return result

if __name__=='__main__':
    result={'source':'© OpenStreetMap contributors','license':'https://opendatacommons.org/licenses/odbl/1-0/',
            'retrieved':'2026-11-04','lakes':[item for path in sys.argv[1:] for item in extract(path)]}
    assert {x['relation'] for x in result['lakes']}=={'1273044','1410914'}
    (Path(__file__).resolve().parents[1]/'web/public/lake-corrections.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')))
