import math
from typing import Tuple

def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    R = 6371.0
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat/2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * 
         math.sin(delta_lon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def manhattan_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
   
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    lat_diff = abs(lat2 - lat1) * 111.0  
    lon_diff = abs(lon2 - lon1) * 111.0 * math.cos(math.radians(lat1))
    
    return lat_diff + lon_diff