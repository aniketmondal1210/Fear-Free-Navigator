import networkx as nx
import math
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import datetime as dt
from heapq import heappush, heappop

class RoutingEngine:
    def __init__(self, G: nx.MultiDiGraph):
        self.G = G

    def get_time_bucket(self, current_time: datetime) -> str:
        hour = current_time.hour
        if 6 <= hour < 17:
            return 'day'
        elif 17 <= hour < 21:
            return 'evening'
        elif 21 <= hour <= 23 or hour == 0:
            return 'night'
        else:
            return 'late_night'

    def calculate_css(self, edge_data: dict, current_time: datetime, persona_weights: dict) -> float:
        bucket = self.get_time_bucket(current_time)
        scores = edge_data['scores'][bucket]
        
        lighting = scores['lighting']
        crime_risk = scores['crime']
        crowd = scores['crowd']
        perception = scores['perception']
        
        w_l = persona_weights.get('lighting', 0.25)
        w_c = persona_weights.get('crime', 0.25)
        w_cr = persona_weights.get('crowd', 0.25)
        w_p = persona_weights.get('perception', 0.25)
        
        css = (w_l * lighting) + (w_c * (1 - crime_risk)) + (w_cr * crowd) + (w_p * perception)
        return max(0.0, min(1.0, css))

    def modified_astar(self, source, target, departure_time: datetime, persona: str, alpha: float, beta: float):
        def heuristic(u, v):
            if 'x' in self.G.nodes[u] and 'x' in self.G.nodes[v]:
                dx = self.G.nodes[u]['x'] - self.G.nodes[v]['x']
                dy = self.G.nodes[u]['y'] - self.G.nodes[v]['y']
                # Approximate distance in meters
                dist_m = math.sqrt(dx**2 + dy**2) * 111000 
                return (alpha * (dist_m / 1.4))
            return 0
            
        persona_weights = {
            'solo_woman_night': {'lighting': 0.35, 'crime': 0.35, 'crowd': 0.15, 'perception': 0.15},
            'elderly': {'lighting': 0.4, 'crime': 0.4, 'crowd': 0.1, 'perception': 0.1},
            'general': {'lighting': 0.25, 'crime': 0.25, 'crowd': 0.25, 'perception': 0.25}
        }
        weights = persona_weights.get(persona, persona_weights['general'])

        queue = [(heuristic(source, target), 0, source, [source], 0)]
        visited = {}
        
        while queue:
            f, g, u, path, t_offset = heappop(queue)
            
            if u in visited and visited[u] <= g:
                continue
            visited[u] = g
            
            if u == target:
                return path
                
            current_t = departure_time + dt.timedelta(seconds=t_offset)
            
            for v in self.G.neighbors(u):
                # Use minimum travel_time edge if multiple exist
                edge_keys = self.G[u][v].keys()
                best_edge = min(edge_keys, key=lambda k: self.G[u][v][k].get('travel_time', 999))
                edge_data = self.G[u][v][best_edge]
                
                travel_time = edge_data.get('travel_time', 10.0)
                css = self.calculate_css(edge_data, current_t, weights)
                
                # Cost function: combination of time and safety penalty
                cost = alpha * travel_time + beta * 300 * (1 - css)
                
                new_g = g + cost
                new_t_offset = t_offset + travel_time
                new_path = list(path)
                new_path.append(v)
                
                heappush(queue, (new_g + heuristic(v, target), new_g, v, new_path, new_t_offset))
                
        return None

    def get_route_tiers(self, source, target, departure_time: datetime, persona: str):
        path1 = self.modified_astar(source, target, departure_time, persona, alpha=0.9, beta=0.1)
        path2 = self.modified_astar(source, target, departure_time, persona, alpha=0.1, beta=0.9)
        path3 = self.modified_astar(source, target, departure_time, persona, alpha=0.5, beta=0.5)
        
        return {
            "tier1_express": path1,
            "tier2_safe": path2,
            "tier3_balanced": path3
        }

    def enrich_path_data(self, path, departure_time: datetime, persona: str):
        if not path: return None
        
        nodes = []
        total_time = 0
        total_css = 0
        
        persona_weights = {
            'solo_woman_night': {'lighting': 0.35, 'crime': 0.35, 'crowd': 0.15, 'perception': 0.15},
            'elderly': {'lighting': 0.4, 'crime': 0.4, 'crowd': 0.1, 'perception': 0.1},
            'general': {'lighting': 0.25, 'crime': 0.25, 'crowd': 0.25, 'perception': 0.25}
        }
        weights = persona_weights.get(persona, persona_weights['general'])
        
        for i in range(len(path) - 1):
            u = path[i]
            v = path[i+1]
            best_edge = min(self.G[u][v].keys(), key=lambda k: self.G[u][v][k].get('travel_time', 999))
            edge_data = self.G[u][v][best_edge]
            
            node_data = self.G.nodes[u]
            nodes.append([node_data['x'], node_data['y']])
            
            total_time += edge_data.get('travel_time', 10.0)
            css = self.calculate_css(edge_data, departure_time + dt.timedelta(seconds=total_time), weights)
            total_css += css
                
        # Add final node
        nodes.append([self.G.nodes[path[-1]]['x'], self.G.nodes[path[-1]]['y']])
        
        avg_css = total_css / max(1, len(path)-1)
        
        return {
            "coordinates": nodes,
            "time_minutes": round(total_time / 60),
            "safety_score": round(avg_css * 100)
        }
