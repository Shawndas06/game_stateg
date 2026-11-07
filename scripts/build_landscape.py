"""Offline Natural Earth extraction. Pass a directory containing the two source JSONs.

Inputs: ne_10m_geography_regions_polys.json and ne_50m_rivers_lake_centerlines.json
from nvkelso/natural-earth-vector/geojson (public domain). No GIS at runtime.
"""
import hashlib
import json
import sys
from pathlib import Path


def build(directory):
    layers={}
    def points(coords):
        if not coords:return
        if isinstance(coords[0],(int,float)):yield coords
        else:
            for part in coords:yield from points(part)
    for source,key in [('ne_10m_geography_regions_polys','mountains'),('ne_50m_rivers_lake_centerlines','rivers')]:
        raw=(Path(directory)/(source+'.json')).read_bytes();features=json.loads(raw)['features'];result=[]
        for feature in features:
            props=feature['properties'];g=feature['geometry'];coords=g['coordinates'];ps=list(points(coords))
            if not ps:continue
            if key=='mountains' and props['FEATURECLA']!='Range/mtn':continue
            if key=='rivers' and props['featurecla']!='River':continue
            if max(p[0] for p in ps)<-11 or min(p[0] for p in ps)>44.5 or max(p[1] for p in ps)<22 or min(p[1] for p in ps)>50.5:continue
            result.extend(coords if g['type'].startswith('Multi') else [coords])
        layers[key]=result
        print(source,'SHA256',hashlib.sha256(raw).hexdigest(),'features',len(result))
    # Schematized wooded belts, not a historical vegetation survey.
    layers['woods']=[[29.3,40.05,1.2,.65],[30.15,39.9,1.1,.6],[30.5,40.6,1,.5],[32,41.3,1.4,.45],[35.5,41,1.2,.5],[39,40.7,1.3,.4],[24.3,41.7,1.3,.5],[22,39.5,.55,1],[18,44.3,1,1],[10.5,46.5,2,.45],[6.7,48.2,1.5,.6]]
    # Local relief omitted at Natural Earth's thematic scale: schematic extents.
    layers['hills']=[[29.22,40.07,.45,.15],[30.75,39.98,.8,.16],[29.8,40.6,.9,.1],[29.6,39.9,.35,.15]]
    text=json.dumps(layers,separators=(',',':'),ensure_ascii=False)
    # Millidegree precision is sufficient for thematic landscape, never coast/cities.
    import re
    text=re.sub(r'-?\d+\.\d+',lambda m:str(round(float(m[0]),3)),text)
    target=Path(__file__).resolve().parents[1]/'web/src/map-landscape.json';target.write_text(text);print(target.name,len(text))


if __name__=='__main__':build(sys.argv[1])
