# Geospatial Data Pipeline for Urban Flood Risk Assessment

This project implements an enterprise-grade Geospatial Data Pipeline for urban flood risk assessment in Nigeria, leveraging a containerized architecture powered by Docker Compose.

---

## 1. Prerequisites
- **Docker Desktop** installed and running.
- **Hardware Resources**: Allocate at least **8GB RAM** and **4 CPUs** to Docker (Settings > Resources) to handle the resource-intensive spatial processing.

---

## 2. Infrastructure Setup (Docker Compose)

The pipeline uses a consolidated database backend (a single PostgreSQL + PostGIS instance containing separate databases for `airflow`, `superset`, and `geodata`) to optimize resource usage.

### Quick Start
To spin up all services:
```bash
# Start all containers in detached mode
docker compose up -d
```

### Deployed Services
1. **PostgreSQL + PostGIS** (`localhost:5432`): Stores spatial footprints, roads, and rainfall statistics.
2. **PgAdmin 4** (`http://localhost:5050`): Web-based database management UI (Credentials: `admin@admin.com` / `admin`).
3. **Apache Airflow** (`http://localhost:8080`): DAG runner and orchestration scheduler (Credentials: `admin` / `admin`).
4. **Apache Superset** (`http://localhost:8088`): Visualization layer (Credentials: `admin` / `admin`).

---

## 3. Data Ingestion & Transformation Pipeline

### Step 3.1: Trigger Ingestion (Airflow)
1. Navigate to the Airflow UI at `http://localhost:8080` (credentials: `admin` / `admin`).
2. Turn the `extract_spatial_data` DAG **On** and trigger it.
3. The DAG performs two extraction phases:
   - **OSM Infrastructure**: Queries building footprints and road networks for Ikeja (Lagos), Kogi, and Bayelsa using the `osmnx` library.
   - **Weather Extraction**: Queries Open-Meteo historical archive API for precipitation totals.
4. Once extraction finishes, it executes `transform_and_load.py` which cleans the spatial records, reprojects them to `EPSG:4326`, loads them into PostGIS, and applies GIST spatial indexing.

### Step 3.2: Verify Data Ingestion (PgAdmin)
1. Open PgAdmin at `http://localhost:5050` (credentials: `admin@admin.com` / `admin`).
2. Add a new server connection:
   - **Host**: `postgis` (or `localhost` if connecting from host machine)
   - **Username**: `geo_admin`
   - **Password**: `geo_password`
   - **Database**: `geodata`
3. Run the following queries to verify datasets:
   ```sql
   SELECT * FROM buildings LIMIT 10;
   SELECT * FROM roads LIMIT 10;
   SELECT * FROM rainfall LIMIT 10;
   ```

---

## 4. Superset Configuration & Visualization

### Step 4.1: Automate Database and Dataset Registration
Once the pipeline has completed running and data is successfully loaded into PostGIS, run the following automated script to connect Superset to the database and register the datasets:
```bash
./init_superset.sh
```

### Step 4.2: Assembling the Dashboard in Superset
1. Open `http://localhost:8088` (credentials: `admin` / `admin`).
2. Go to **Data > Datasets** to verify the datasets `buildings`, `roads`, and `rainfall` are present.

#### Create the Building Footprints Map:
1. Click **+ Chart** in the top right.
2. Select `buildings` as your dataset and **deck.gl Polygon** as the visualization type.
3. Under the query panel:
   - Set **Polygon Column** to `geometry`.
   - Set Stroke and Fill Colors as desired.
   - Click **Save** and name it `Ikeja Building Footprints`.

#### Create the Rainfall Scatterplot:
1. Click **+ Chart** in the top right.
2. Select `rainfall` as your dataset and **deck.gl Scatterplot** as the visualization type.
3. Under the query panel:
   - Set Longitude/Latitude fields.
   - Set Point Radius based on the `precipitation_sum` column to highlight heavy rainfall centers.
   - Click **Save** and name it `Rainfall Spotlights`.

#### Assemble the Dashboard:
Create a new dashboard named **Urban Flood Risk Dashboard** and drop both charts side by side to identify structure locations under high precipitation risks.