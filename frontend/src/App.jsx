import React, { useState, useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Shield, Clock, Map as MapIcon, User, MapPin, Navigation, Info } from 'lucide-react';

const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

export default function App() {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const startMarkerRef = useRef(null);
  const endMarkerRef = useRef(null);

  const [city, setCity] = useState('manhattan');
  const [startPoint, setStartPoint] = useState({ lon: -73.997, lat: 40.725 });
  const [endPoint, setEndPoint] = useState({ lon: -73.990, lat: 40.735 });
  const [routesData, setRoutesData] = useState(null);
  const [anchorsData, setAnchorsData] = useState([]);
  const [loading, setLoading] = useState(false);

  const [time, setTime] = useState('01:00'); 
  const [persona, setPersona] = useState('solo_woman_night');

  useEffect(() => {
    if (map.current) return; // initialize map only once
    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: MAP_STYLE,
      center: [-73.997232, 40.730610],
      zoom: 14,
      pitch: 45,
      bearing: -17.6
    });

    map.current.on('load', () => {
      // Add sources and layers
      ['route2-glow', 'route2-line', 'route3-line', 'route1-line'].forEach(id => {
        if (!map.current.getSource(id)) {
          map.current.addSource(id, { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
        }
      });

      map.current.addLayer({ id: 'route2-glow', type: 'line', source: 'route2-glow', layout: { 'line-join': 'round', 'line-cap': 'round' }, paint: { 'line-color': '#818cf8', 'line-width': 12, 'line-opacity': 0.3, 'line-blur': 4 } });
      map.current.addLayer({ id: 'route2-line', type: 'line', source: 'route2-line', layout: { 'line-join': 'round', 'line-cap': 'round' }, paint: { 'line-color': '#6366f1', 'line-width': 6 } });
      map.current.addLayer({ id: 'route3-line', type: 'line', source: 'route3-line', layout: { 'line-join': 'round', 'line-cap': 'round' }, paint: { 'line-color': '#3b82f6', 'line-width': 5, 'line-opacity': 0.8 } });
      map.current.addLayer({ id: 'route1-line', type: 'line', source: 'route1-line', layout: { 'line-join': 'round', 'line-cap': 'round' }, paint: { 'line-color': '#4b5563', 'line-width': 4, 'line-opacity': 0.6 } });

      // Add draggable markers
      startMarkerRef.current = new maplibregl.Marker({ color: "#10b981", draggable: true })
        .setLngLat([startPoint.lon, startPoint.lat])
        .addTo(map.current);

      endMarkerRef.current = new maplibregl.Marker({ color: "#ef4444", draggable: true })
        .setLngLat([endPoint.lon, endPoint.lat])
        .addTo(map.current);

      startMarkerRef.current.on('dragend', () => {
        const lngLat = startMarkerRef.current.getLngLat();
        setStartPoint({ lon: lngLat.lng, lat: lngLat.lat });
      });

      endMarkerRef.current.on('dragend', () => {
        const lngLat = endMarkerRef.current.getLngLat();
        setEndPoint({ lon: lngLat.lng, lat: lngLat.lat });
      });
    });
  }, []);

  useEffect(() => {
    // When city changes, fly to new location and reset markers
    if (!map.current || !startMarkerRef.current) return;
    
    setRoutesData(null); // clear old routes
    setAnchorsData([]);

    let start, end, center;
    if (city === 'manhattan') {
      center = [-73.997232, 40.730610];
      start = { lon: -73.997, lat: 40.725 };
      end = { lon: -73.990, lat: 40.735 };
    } else if (city === 'detroit') {
      center = [-83.0458, 42.3314];
      start = { lon: -83.05, lat: 42.33 };
      end = { lon: -83.04, lat: 42.34 };
    }

    if (center && start && end) {
      map.current.flyTo({ center, zoom: 13 });
      setStartPoint(start);
      setEndPoint(end);
      startMarkerRef.current.setLngLat([start.lon, start.lat]);
      endMarkerRef.current.setLngLat([end.lon, end.lat]);
    }
  }, [city]);

  useEffect(() => {
    fetchRoutes();
  }, [time, persona]);

  useEffect(() => {
    if (!map.current || !map.current.isStyleLoaded()) return;

    const updateSource = (id, data) => {
      const source = map.current.getSource(id);
      if (source) source.setData(data);
    };

    if (routesData) {
      if (routesData.tier2_safe) {
        const geojson = { type: 'Feature', geometry: { type: 'LineString', coordinates: routesData.tier2_safe.coordinates } };
        updateSource('route2-glow', geojson);
        updateSource('route2-line', geojson);
      } else {
        updateSource('route2-glow', { type: 'FeatureCollection', features: [] });
        updateSource('route2-line', { type: 'FeatureCollection', features: [] });
      }

      if (routesData.tier3_balanced) {
        updateSource('route3-line', { type: 'Feature', geometry: { type: 'LineString', coordinates: routesData.tier3_balanced.coordinates } });
      } else {
        updateSource('route3-line', { type: 'FeatureCollection', features: [] });
      }

      if (routesData.tier1_express) {
        updateSource('route1-line', { type: 'Feature', geometry: { type: 'LineString', coordinates: routesData.tier1_express.coordinates } });
      } else {
        updateSource('route1-line', { type: 'FeatureCollection', features: [] });
      }
    } else {
      ['route2-glow', 'route2-line', 'route3-line', 'route1-line'].forEach(id => {
        updateSource(id, { type: 'FeatureCollection', features: [] });
      });
    }
  }, [routesData]);

  const fetchRoutes = async () => {
    setLoading(true);
    try {
      const d = new Date();
      const [hours, minutes] = time.split(':');
      d.setHours(parseInt(hours), parseInt(minutes));

      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_BASE_URL}/api/route`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_lon: startPoint.lon,
          start_lat: startPoint.lat,
          end_lon: endPoint.lon,
          end_lat: endPoint.lat,
          departure_time: d.toISOString(),
          persona: persona
        })
      });
      const data = await res.json();
      setRoutesData(data);
      setAnchorsData(data.anchors || []);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  return (
    <div className="h-screen w-screen flex flex-col md:flex-row relative overflow-hidden bg-black text-white font-sans">
      
      {/* Sidebar Controls */}
      <div className="w-full md:w-96 flex-shrink-0 z-10 p-6 flex flex-col gap-6 glass-panel md:h-full overflow-y-auto">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-indigo-500/20 rounded-lg border border-indigo-500/30">
            <Shield className="w-6 h-6 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">
              Fear-Free Navigator
            </h1>
            <p className="text-xs text-gray-400 font-medium tracking-wide">PSYCHOLOGICAL SAFETY FIRST</p>
          </div>
        </div>

        {/* City Selector */}
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-300 flex items-center gap-2">
            <MapIcon className="w-4 h-4 text-gray-400" /> Select City
          </label>
          <select 
            value={city} 
            onChange={(e) => setCity(e.target.value)}
            className="w-full bg-black/50 border border-gray-700 rounded-lg p-2.5 text-sm outline-none focus:border-indigo-500 transition-colors"
          >
            <option value="manhattan">New York City (Manhattan)</option>
            <option value="detroit">Detroit, MI</option>
          </select>
        </div>

        {/* Instructions */}
        <div className="bg-indigo-900/30 border border-indigo-500/30 rounded-lg p-3 text-sm text-indigo-200 flex gap-3">
          <MapPin className="w-5 h-5 shrink-0 text-indigo-400" />
          <p>Drag the <strong>Green marker</strong> (Start) and <strong>Red marker</strong> (End) on the map to set your locations anywhere in {city === 'manhattan' ? 'Manhattan' : 'Detroit'}.</p>
        </div>

        {/* Persona & Time Controls */}
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-300 flex items-center gap-2">
              <User className="w-4 h-4 text-gray-400" /> User Persona
            </label>
            <select 
              value={persona} 
              onChange={(e) => setPersona(e.target.value)}
              className="w-full bg-black/50 border border-gray-700 rounded-lg p-2.5 text-sm outline-none focus:border-indigo-500 transition-colors"
            >
              <option value="solo_woman_night">Solo Woman (Safety Priority)</option>
              <option value="elderly">Elderly Traveler (Lighting/Accessibility)</option>
              <option value="general">General Commuter (Balanced)</option>
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-300 flex items-center gap-2">
              <Clock className="w-4 h-4 text-gray-400" /> Departure Time
            </label>
            <input 
              type="time" 
              value={time} 
              onChange={(e) => setTime(e.target.value)}
              className="w-full bg-black/50 border border-gray-700 rounded-lg p-2.5 text-sm outline-none focus:border-indigo-500 transition-colors"
            />
          </div>
          
          <button 
            onClick={fetchRoutes}
            disabled={loading}
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium transition-all shadow-[0_0_15px_rgba(79,70,229,0.3)] hover:shadow-[0_0_25px_rgba(79,70,229,0.5)] disabled:opacity-50 cursor-pointer"
          >
            {loading ? 'Calculating...' : 'Find Safe Routes'}
          </button>
        </div>

        <div className="h-px bg-gradient-to-r from-transparent via-gray-700 to-transparent my-2" />

        {/* Route Explainability Cards */}
        {routesData && (
          <div className="flex-1 overflow-y-auto space-y-4 pr-1">
            <h3 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
              <Navigation className="w-4 h-4 text-indigo-400" /> Route Options
            </h3>
            
            {/* Tier 2: Safe Route */}
            {routesData.tier2_safe && (
              <div className="bg-indigo-900/20 border border-indigo-500/50 rounded-xl p-4 relative overflow-hidden">
                <div className="absolute top-0 right-0 px-2 py-1 bg-indigo-500/20 text-indigo-300 text-xs font-bold rounded-bl-lg border-b border-l border-indigo-500/30">RECOMMENDED</div>
                <h4 className="font-bold text-indigo-300 flex items-center gap-2 mb-2">
                  <Shield className="w-4 h-4" /> Safe Scenic
                </h4>
                <div className="grid grid-cols-2 gap-2 text-sm mb-3">
                  <div className="bg-black/40 rounded p-2 text-center border border-gray-800">
                    <span className="block text-xl font-bold">{routesData.tier2_safe.time_minutes}</span>
                    <span className="text-[10px] text-gray-400 uppercase">Minutes</span>
                  </div>
                  <div className="bg-black/40 rounded p-2 text-center border border-gray-800">
                    <span className="block text-xl font-bold text-green-400">{routesData.tier2_safe.safety_score}%</span>
                    <span className="text-[10px] text-gray-400 uppercase">Safety Score</span>
                  </div>
                </div>
                <div className="bg-black/50 rounded-lg p-3 text-xs text-gray-300 flex gap-3 border border-gray-800">
                  <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                  <p>Prioritizes well-lit primary roads. Passes by {anchorsData.length} active safe zones. {routesData.tier2_safe.mun_count > 0 ? <span className="text-red-400">Crosses {routesData.tier2_safe.mun_count} unsafe segment.</span> : <span className="text-green-400">No critically unsafe segments.</span>}</p>
                </div>
              </div>
            )}

            {/* Tier 1: Express Route */}
            {routesData.tier1_express && (
              <div className="bg-gray-800/30 border border-gray-700 rounded-xl p-4 transition-colors hover:bg-gray-800/50 cursor-pointer">
                <h4 className="font-semibold text-gray-200 mb-2">Fastest Path (Time Optimized)</h4>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-300 font-mono">{routesData.tier1_express.time_minutes} min</span>
                  <span className={`px-2 py-1 rounded text-xs font-bold ${routesData.tier1_express.safety_score < 70 ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'}`}>
                    {routesData.tier1_express.safety_score}% Safe
                  </span>
                </div>
                {routesData.tier1_express.mun_count > 0 && (
                  <p className="text-xs text-red-400 mt-2">Warning: Avoids {routesData.tier1_express.mun_count} critically unsafe areas.</p>
                )}
              </div>
            )}
            
            {/* Tier 3: Balanced Route */}
            {routesData.tier3_balanced && (
              <div className="bg-gray-800/30 border border-gray-700 rounded-xl p-4 transition-colors hover:bg-gray-800/50 cursor-pointer">
                <h4 className="font-semibold text-gray-200 mb-2">Balanced (Time + Safety)</h4>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-gray-300 font-mono">{routesData.tier3_balanced.time_minutes} min</span>
                  <span className="px-2 py-1 rounded text-xs font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30">
                    {routesData.tier3_balanced.safety_score}% Safe
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Map Area */}
      <div className="flex-1 h-full w-full relative" ref={mapContainer} />
      
      {/* Top-right overlay status */}
      <div className="absolute top-6 right-6 glass-panel rounded-full px-4 py-2 flex items-center gap-3 pointer-events-none">
        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
        <span className="text-xs font-semibold tracking-wider text-gray-300">LIVE MONITORING ACTIVE</span>
      </div>
    </div>
  );
}
