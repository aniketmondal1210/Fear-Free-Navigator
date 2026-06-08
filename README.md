# Fear-Free Night Navigator

A safety-conscious urban routing system that calculates optimal paths based on a dynamic **Composite Safety Score (CSS)**, integrating real-time municipal crime data with environmental factors.

## Features
- **Safety-First Routing**: Uses a modified A* algorithm to balance travel time with psychological safety.
- **Dynamic Scoring**: Safety scores update based on time of day (Day, Evening, Night, Late Night).
- **Multi-City Support**: Currently supports Manhattan, NYC and Chicago, IL.
- **Persona-Based Navigation**: Custom weights for Solo Women, Elderly, and General Commuters.
- **Interactive UI**: Map-based interface with glowing safe routes and draggable markers.

## Tech Stack
- **Backend**: FastAPI, NetworkX, OSMnx, Scipy
- **Frontend**: React (Vite), MapLibre GL, Tailwind CSS
- **Data**: NYC Open Data, Chicago Data Portal (via SODA API)

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+

### Installation & Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fear-free-navigator
   ```

2. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   pip install fastapi uvicorn networkx osmnx scipy pydantic requests
   ```
   *Note: You may need to run `python download_graph.py` to generate the initial graph data.*

3. **Frontend Setup**
   ```bash
   cd ../frontend
   npm install
   npm run dev
   ```

4. **Run the Application**
   - Start the backend: `python main.py` in the backend folder.
   - Access the frontend at the URL provided by Vite (usually `http://localhost:5173`).

## Project Report
For a detailed technical breakdown, methodology, and mathematical proofs, refer to the [Project Report](university_project_report.md) (if included in repo).

## License
MIT
