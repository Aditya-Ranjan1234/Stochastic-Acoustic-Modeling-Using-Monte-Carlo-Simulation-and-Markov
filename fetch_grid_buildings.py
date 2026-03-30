import math, json, urllib.request, urllib.parse

def fetch_buildings_for_grid(clat, clon, city_name, zoom=17, angle_deg=0):
    """Fetch OSM buildings and map them to a 10x10 grid."""
    mpp = 156543.03 * math.cos(math.radians(clat)) / (2**zoom)
    cell_m = mpp * 60
    # Increase the query extent due to rotation potentially pulling in distant corners
    query_extent = 320 * mpp # Search wider area to cover corners safely
    
    print(f"\n=== {city_name} ===")
    print(f"Zoom: {zoom}, angle: {angle_deg}°, m/px: {mpp:.4f}, cell: {cell_m:.1f}m, total bounding: {cell_m*10:.0f}m")
    
    dlat = query_extent / 111320
    dlon = query_extent / (111320 * math.cos(math.radians(clat)))
    bbox = f"{clat - dlat},{clon - dlon},{clat + dlat},{clon + dlon}"
    
    query = (
        '[out:json][timeout:25];'
        f'(way["building"]({bbox});way["amenity"="hospital"]({bbox}););'
        'out center;'
    )
    
    # Use fallback overpass server
    url = 'https://overpass.kumi.systems/api/interpreter?data=' + urllib.parse.quote(query)
    print(f"Fetching from Overpass API (kumi.systems)...")
    
    req = urllib.request.Request(url, headers={"User-Agent": "AcousticSim/1.0"})
    resp = urllib.request.urlopen(req, timeout=120)
    data = json.loads(resp.read())
    elements = data.get('elements', [])
    print(f"Got {len(elements)} building ways")
    
    occupied = {}
    hospitals = set()
    rad = math.radians(angle_deg)
    
    for el in elements:
        if 'center' not in el:
            continue
        blat = el['center']['lat']
        blon = el['center']['lon']
        
        dx_m = (blon - clon) * 111320 * math.cos(math.radians(clat))
        dy_m = -(blat - clat) * 111320
        
        # Apply rotation around center
        nx = dx_m * math.cos(rad) - dy_m * math.sin(rad)
        ny = dx_m * math.sin(rad) + dy_m * math.cos(rad)
        
        px = 300 + nx / mpp
        py = 300 + ny / mpp
        
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
        # Simplify geometry to massive unitary blocks for cleaner acoustic rendering
        h = 20 if mat == 'hospital' else (15 if count > 2 else 10)
        buildings.append({"x": col, "y": row, "h": h, "material": mat})
    
    print(f"\nJS array ({len(buildings)} entries):")
    print(json.dumps(buildings))
    return buildings

# Barcelona - Eixample / Hospital Clinic area (rotated ~45 degrees to align diagonal blocks cleanly to grid)
b_buildings = fetch_buildings_for_grid(41.3887, 2.1635, "Barcelona", zoom=17, angle_deg=-45)

# Kolkata - SSKM Hospital / Maidan area
k_buildings = fetch_buildings_for_grid(22.5395, 88.3435, "Kolkata", zoom=17, angle_deg=0)
