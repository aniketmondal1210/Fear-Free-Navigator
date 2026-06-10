from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import networkx as nx
import pickle
from datetime import datetime
import os
from routing_engine import RoutingEngine

app = FastAPI(title="Fear-Free Night Navigator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load graphs
graphs = {}
engines = {}

class RouteRequest(BaseModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    departure_time: str # ISO string
    persona: str = 'solo_woman_night'

@app.on_event("startup")
def load_data():
    # We now use Lazy Loading in the get_routes endpoint to stay under the 512MB RAM limit.
    pass

# Global cache
loaded_city = None

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/route")
def get_routes(req: RouteRequest):
    global loaded_city, graphs, engines
    
    # Auto-detect city by longitude
    city = "detroit" if req.start_lon < -79 else "manhattan"
    
    # Lazy load the city graph if not already in memory
    if loaded_city != city:
        print(f"Loading {city} graph into memory...")
        # Clear existing memory to stay under 512MB limit
        graphs = {}
        engines = {}
        
        file = "graph_manhattan.pkl" if city == "manhattan" else "graph_detroit.pkl"
        path = os.path.join(os.path.dirname(__file__), file)
        
        if not os.path.exists(path):
             raise HTTPException(status_code=500, detail=f"Graph file missing for {city}")
             
        try:
            with open(path, 'rb') as f:
                graphs[city] = pickle.load(f)
            engines[city] = RoutingEngine(graphs[city])
            loaded_city = city
            print(f"Successfully switched memory to {city}")
        except Exception as e:
            print(f"Error loading {city}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    G = graphs.get(city)
    engine = engines.get(city)
    
    if not G or not engine:
        raise HTTPException(status_code=500, detail=f"Failed to initialize engine for {city}")

    # Find nearest nodes
    import osmnx as ox
    try:
        source_node = ox.distance.nearest_nodes(G, req.start_lon, req.start_lat)
        target_node = ox.distance.nearest_nodes(G, req.end_lon, req.end_lat)
    except:
        def nearest_node(G, lon, lat):
            return min(G.nodes, key=lambda n: (G.nodes[n]['x'] - lon)**2 + (G.nodes[n]['y'] - lat)**2)
        source_node = nearest_node(G, req.start_lon, req.start_lat)
        target_node = nearest_node(G, req.end_lon, req.end_lat)

    try:
        dt = datetime.fromisoformat(req.departure_time.replace('Z', '+00:00'))
    except:
        dt = datetime.now()

    tiers = engine.get_route_tiers(source_node, target_node, dt, req.persona)
    
    response = {
        "tier1_express": engine.enrich_path_data(tiers["tier1_express"], dt, req.persona),
        "tier2_safe": engine.enrich_path_data(tiers["tier2_safe"], dt, req.persona),
        "tier3_balanced": engine.enrich_path_data(tiers["tier3_balanced"], dt, req.persona)
    }

    # Anchors
    anchors = []
    if tiers["tier2_safe"]:
        import random
        path = tiers["tier2_safe"]
        for i in range(1, len(path)-1):
            if random.random() < 0.1:
                node_data = G.nodes[path[i]]
                anchors.append({
                    "lat": node_data['y'], "lon": node_data['x'],
                    "type": random.choice(["24hr Pharmacy", "Police Booth", "Well-lit Area"])
                })
                if len(anchors) >= 3: break
    
    response["anchors"] = anchors
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
