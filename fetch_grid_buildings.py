import math, json, urllib.request, urllib.parse

def fetch_buildings_for_grid(clat, clon, city_name, zoom=17):
    """Fetch OSM buildings and map them to a 10x10 grid."""
    mpp = 156543.03 * math.cos(math.radians(clat)) / (2**zoom)
    cell_m = mpp * 60
    half_extent = 300 * mpp
    
    print(f"\n=== {city_name} ===")
    print(f"Zoom: {zoom}, m/px: {mpp:.4f}, cell: {cell_m:.1f}m, total: {cell_m*10:.0f}m")
    
    dlat = half_extent / 111320
    dlon = half_extent / (111320 * math.cos(math.radians(clat)))
    bbox = f"{clat - dlat},{clon - dlon},{clat + dlat},{clon + dlon}"
    
    query = (
        '[out:json][timeout:25];'
        f'(way["building"]({bbox});way["amenity"="hospital"]({bbox}););'
        'out center;'
    )
    
    url = 'https://overpass-api.de/api/interpreter?data=' + urllib.parse.quote(query)
    print(f"Fetching from Overpass API...")
    
    req = urllib.request.Request(url, headers={"User-Agent": "AcousticSim/1.0"})
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read())
    elements = data.get('elements', [])
    print(f"Got {len(elements)} building ways")
    
    occupied = {}
    hospitals = set()
    
    for el in elements:
        if 'center' not in el:
            continue
        blat = el['center']['lat']
        blon = el['center']['lon']
        
        dx_m = (blon - clon) * 111320 * math.cos(math.radians(clat))
        dy_m = -(blat - clat) * 111320
        
        px = 300 + dx_m / mpp
        py = 300 + dy_m / mpp
        
        col = int(px / 60)
        row = int(py / 60)
        
        if 0 <= col < 10 and 0 <= row < 10:
            key = (col, row)
            tags = el.get('tags', {})
            is_hosp = tags.get('amenity') == 'hospital' or tags.get('building') == 'hospital'
            if is_hosp:
                hospitals.add(key)
            occupied[key] = occupied.get(key, 0) + 1
    
    print(f"\nOccupied cells: {len(occupied)}/100")
    print(f"Hospital cells: {hospitals}")
    
    print("\nGrid visualization (count of buildings per cell):")
    for row in range(10):
        line = ''
        for col in range(10):
            if (col, row) in hospitals:
                line += '  H'
            elif (col, row) in occupied:
                count = occupied[(col, row)]
                line += f'{count:3d}'
            else:
                line += '  .'
        print(f"  row {row}: {line}")
    
    buildings = []
    for (col, row), count in sorted(occupied.items()):
        mat = 'hospital' if (col, row) in hospitals else 'concrete'
        h = 20 if mat == 'hospital' else (15 if count > 3 else 10 if count > 1 else 5)
        buildings.append({"x": col, "y": row, "h": h, "material": mat})
    
    print(f"\nJS array ({len(buildings)} entries):")
    print(json.dumps(buildings))
    return buildings

# Barcelona - Eixample / Hospital Clinic area
b_buildings = fetch_buildings_for_grid(41.3887, 2.1635, "Barcelona")

# Kolkata - SSKM Hospital / Maidan area
k_buildings = fetch_buildings_for_grid(22.5395, 88.3435, "Kolkata")
