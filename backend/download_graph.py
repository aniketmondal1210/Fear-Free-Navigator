import osmnx as ox
import networkx as nx
import random
import pickle
import os
import time
import requests
import json
from scipy.spatial import cKDTree
import numpy as np

def fetch_chicago_crime_data(app_token=None):
    print("Fetching live Crime Data for Chicago from SODA API...")
    url = "https://data.cityofchicago.org/resource/ijzp-q8t2.json?$limit=2000&$order=date DESC"
    headers = {}
    if app_token:
        headers['X-App-Token'] = app_token

    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        crime_points = []
        for incident in data:
            if incident.get('latitude') is not None and incident.get('longitude') is not None:
                try:
                    lat = float(incident['latitude'])
                    lon = float(incident['longitude'])
                    crime_points.append((lon, lat))
                except ValueError:
                    continue
        
        print(f"Successfully fetched and mapped {len(crime_points)} recent real crime incidents for Chicago.")
        return crime_points
    except Exception as e:
        print(f"Error fetching Chicago crime data: {e}")
        return []

def fetch_manhattan_crime_data(app_token=None):
    print("Fetching live Crime Data for Manhattan from NYC Open Data SODA API...")
    url = "https://data.cityofnewyork.us/resource/5uac-w243.json?$limit=2000&$order=cmplnt_fr_dt DESC&$where=boro_nm='MANHATTAN'"
    headers = {}
    if app_token:
        headers['X-App-Token'] = app_token

    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        crime_points = []
        for incident in data:
            if incident.get('latitude') is not None and incident.get('longitude') is not None:
                try:
                    lat = float(incident['latitude'])
                    lon = float(incident['longitude'])
                    crime_points.append((lon, lat))
                except ValueError:
                    continue
        
        print(f"Successfully fetched and mapped {len(crime_points)} recent real crime incidents for Manhattan.")
        return crime_points
    except Exception as e:
        print(f"Error fetching Manhattan crime data: {e}")
        return []

def fetch_detroit_crime_data(app_token=None):
    print("Fetching live Crime Data for Detroit from Detroit Open Data Portal...")
    # Detroit Crime Data (RMS) - Last 30 days
    url = "https://data.detroitmi.gov/resource/89tr-v7gh.json?$limit=2000&$order=incident_timestamp DESC"
    headers = {}
    if app_token:
        headers['X-App-Token'] = app_token

    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        crime_points = []
        for incident in data:
            if incident.get('latitude') is not None and incident.get('longitude') is not None:
                try:
                    lat = float(incident['latitude'])
                    lon = float(incident['longitude'])
                    crime_points.append((lon, lat))
                except ValueError:
                    continue
        
        print(f"Successfully fetched and mapped {len(crime_points)} recent real crime incidents for Detroit.")
        return crime_points
    except Exception as e:
        print(f"Error fetching Detroit crime data: {e}")
        return []

def map_crimes_to_nodes(G, crime_points):
    if not crime_points:
        return {}
    
    print("Mapping crimes to street nodes via KDTree...")
    # Extract node coordinates
    nodes = list(G.nodes(data=True))
    node_ids = [n[0] for n in nodes]
    node_coords = np.array([[n[1]['x'], n[1]['y']] for n in nodes])
    
    # Build KDTree
    tree = cKDTree(node_coords)
    
    # Query nearest node for each crime
    crime_coords = np.array(crime_points)
    distances, indices = tree.query(crime_coords)
    
    # Count crimes per node
    crime_counts = {nid: 0 for nid in node_ids}
    for idx in indices:
        nearest_node = node_ids[idx]
        crime_counts[nearest_node] += 1
        
    return crime_counts

def calculate_bucketed_scores(u, v, data, city, crime_counts):
    highway = data.get('highway', '')
    if isinstance(highway, list):
        highway = highway[0]

    is_main_road = highway in ['primary', 'secondary', 'tertiary']
    
    # Real data logic:
    # If the edge is connected to nodes with high crime counts, crime risk goes up.
    # We take the max crime count of the two connecting nodes
    local_crimes = 0
    if crime_counts:
        local_crimes = max(crime_counts.get(u, 0), crime_counts.get(v, 0))
    
    # Each recent crime mapped to the intersection adds 15% risk penalty to the baseline
    real_crime_penalty = min(0.9, local_crimes * 0.15) 
        
    # 1. Day
    day_lighting = 1.0
    day_crime_risk = min(1.0, real_crime_penalty + random.uniform(0.0, 0.05))
    day_crowd = random.uniform(0.6, 1.0) if is_main_road else random.uniform(0.3, 0.7)
    day_perception = random.uniform(0.7, 1.0)
    
    # 2. Evening
    eve_lighting = random.uniform(0.7, 1.0) if is_main_road else random.uniform(0.4, 0.8)
    eve_crime_risk = min(1.0, day_crime_risk * 1.2)
    eve_crowd = random.uniform(0.5, 0.9) if is_main_road else random.uniform(0.2, 0.6)
    eve_perception = random.uniform(0.6, 0.9)

    # 3. Night
    night_lighting = eve_lighting
    night_crime_risk = min(1.0, day_crime_risk * 1.5)
    night_crowd = random.uniform(0.2, 0.5) if is_main_road else random.uniform(0.0, 0.3)
    night_perception = random.uniform(0.4, 0.7)

    # 4. Late Night
    late_lighting = night_lighting
    late_crime_risk = min(1.0, day_crime_risk * 2.0)
    late_crowd = random.uniform(0.0, 0.2)
    late_perception = random.uniform(0.2, 0.5)

    data['scores'] = {
        'day': {
            'lighting': day_lighting, 'crime': day_crime_risk, 
            'crowd': day_crowd, 'perception': day_perception
        },
        'evening': {
            'lighting': eve_lighting, 'crime': eve_crime_risk, 
            'crowd': eve_crowd, 'perception': eve_perception
        },
        'night': {
            'lighting': night_lighting, 'crime': night_crime_risk, 
            'crowd': night_crowd, 'perception': night_perception
        },
        'late_night': {
            'lighting': late_lighting, 'crime': late_crime_risk, 
            'crowd': late_crowd, 'perception': late_perception
        }
    }
    
    length = data.get('length', 10.0)
    data['travel_time'] = length / 1.4

def main():
    print("Starting Weekly ETL Pipeline for Multiple Cities...")
    
    app_token = os.environ.get("SODA_APP_TOKEN")
    
    cities = [
        {"name": "Manhattan, New York City, New York, USA", "file": "graph_manhattan.pkl", "fetcher": fetch_manhattan_crime_data},
        {"name": "Detroit, Michigan, USA", "file": "graph_detroit.pkl", "fetcher": fetch_detroit_crime_data}
    ]

    for city in cities:
        output_file = os.path.join(os.path.dirname(__file__), city["file"])
        
        print(f"Downloading full graph for {city['name']}...")
        try:
            G = ox.graph_from_place(city['name'], network_type='walk')
        except Exception as e:
            print(f"Failed to fetch network graph for {city['name']}: {e}")
            continue
        
        crime_points = city["fetcher"](app_token)
        crime_counts = map_crimes_to_nodes(G, crime_points)
        
        print("Enriching graph edges with time-bucketed safety scores based on live data...")
        for u, v, k, data in G.edges(keys=True, data=True):
            calculate_bucketed_scores(u, v, data, city['name'], crime_counts)
            
        print(f"Graph processed: {len(G.nodes)} nodes, {len(G.edges)} edges.")
        
        with open(output_file, 'wb') as f:
            pickle.dump(G, f)
            
        print(f"Production Graph saved to {output_file}")

if __name__ == "__main__":
    main()
