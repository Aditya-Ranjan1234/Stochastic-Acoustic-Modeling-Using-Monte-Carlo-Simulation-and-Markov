import urllib.request
import urllib.parse
import json
import math

# Overpass API endpoint
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def fetch_city_grid(bbox, name, default_h=5):
    # bbox: (south, west, north, east)
    s, w, n, e = bbox
    
    query = f"""
    [out:json];
    (
      way["building"]({s},{w},{n},{e});
      relation["building"]({s},{w},{n},{e});
      node["amenity"="hospital"]({s},{w},{n},{e});
      way["amenity"="hospital"]({s},{w},{n},{e});
    );
    out center;
    """
    
    try:
        data_encoded = urllib.parse.urlencode({'data': query}).encode('utf-8')
        req = urllib.request.Request(OVERPASS_URL, data=data_encoded)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
    except Exception as ex:
        print(f"Error fetching {name}: {ex}")
        return []

    # Map real coords to 0-9 (10x10 grid)
    lat_span = n - s
    lon_span = e - w
    
    buildings_dict = {} # (x,y) -> building info
    
    for element in data.get('elements', []):
        if 'center' in element:
            lat = element['center']['lat']
            lon = element['center']['lon']
        elif 'lat' in element and 'lon' in element:
            lat = element['lat']
            lon = element['lon']
        else:
            continue
            
        tags = element.get('tags', {})
        
        # Calculate grid x, y (0 to 9)
        # Note: lon maps to x, lat maps to y
        # We want y=0 to be top, so n - lat
        x = int(((lon - w) / lon_span) * 10)
        y = int(((n - lat) / lat_span) * 10)
        
        if 0 <= x < 10 and 0 <= y < 10:
            levels = tags.get('building:levels', None)
            is_hospital = tags.get('amenity') == 'hospital'
            
            h = default_h
            if levels:
                try:
                    h = int(float(levels.split(',')[0])) * 3 # roughly 3m per level
                except:
                    pass
            h = min(max(h, 2), 15) # cap height
            
            material = 'hospital' if is_hospital else 'concrete'
            
            # Keep the tallest/most important building in that cell
            if (x, y) not in buildings_dict:
                buildings_dict[(x, y)] = {'x': x, 'y': y, 'h': h, 'material': material}
            else:
                curr = buildings_dict[(x, y)]
                if material == 'hospital':
                    curr['material'] = 'hospital' # prioritize hospital
                curr['h'] = max(curr['h'], h)
                buildings_dict[(x, y)] = curr
                
    result = list(buildings_dict.values())
    return result

with open("osm_data_out.json", "w", encoding='utf-8') as f:
    out = {}
    out["kolkata"] = fetch_city_grid((22.5371, 88.3403, 22.5419, 88.3467), "Kolkata (SSKM)")
    out["barcelona"] = fetch_city_grid((41.3863, 2.1603, 41.3911, 2.1667), "Barcelona (Eixample)")
    json.dump(out, f, indent=2)

