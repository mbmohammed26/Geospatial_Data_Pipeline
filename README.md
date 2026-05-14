# Geospatial Data Pipeline for Urban Flood Risk Assessment

This project implements an enterprise-grade Geospatial Data Pipeline for urban flood risk assessment in Nigeria, leveraging a cloud-native architecture.

## Prerequisites
- **kubectl** (v1.36.1+): Installed locally in `~/.local/bin`.
- **Helm** (v3.15.2+): Installed locally in `~/.local/bin`.
- **Kubernetes Cluster**: Local cluster (e.g., Docker Desktop, Minikube, or Kind).

## Infrastructure Scaffolding

The core infrastructure is deployed in the `geodata` namespace using `deploy.sh`.

### Components
- **PostGIS**: A spatial database for storing geospatial vectors and rasters.
  - Deployed as a `StatefulSet` with a 10GB `PersistentVolumeClaim`.
- **Apache Airflow**: Orchestration engine configured with `KubernetesExecutor` for scalable task isolation.
- **Apache Superset**: Visualization platform for exploring geospatial insights.

### Deployment Script
The `deploy.sh` script automates:
1. Namespace creation.
2. Helm repository management.
3. PostGIS manifest application.
4. Airflow and Superset installation/upgrades.

## Challenges & Solutions

### 1. Airflow Migration Deadlocks
**Problem**: Airflow components were stuck waiting for database migrations that wouldn't trigger automatically in the local environment.
**Solution**: Explicitly enabled `migrateDatabaseJob` and `createUserJob` while disabling `useHelmHooks` to ensure jobs run reliably during the installation phase.

### 2. Superset Security Requirements
**Problem**: Newer Superset versions refuse to start if an insecure or default `SECRET_KEY` is detected.
**Solution**: Injected a unique `SECRET_KEY` via `configOverrides` in the Helm chart.

### 3. Missing Database Drivers in Superset
**Problem**: The official lean Superset images do not include the `psycopg2` driver required for PostgreSQL connectivity.
**Solution**: Switched to the `apache/superset:5.0.0-dev` image tag which includes common database drivers by default.

### 4. Registry Connectivity Issues
**Problem**: Unreliable connection to the `scarf.sh` registry caused `ImagePullBackOff` errors.
**Solution**: Re-routed image pulls directly to the official `apache/superset` repository on Docker Hub.

### 5. Shared Volume Access Modes
**Problem**: `ReadWriteMany` (RWX) is not supported by default local storage classes, causing `data-pvc` to remain in `Pending` state.
**Solution**: Switched to `ReadWriteOnce` (RWO). In a single-node local cluster, this still allows multiple pods (scheduler and workers) to mount the same volume simultaneously.

### 6. Airflow 3.0 Compatibility
**Problem**: The DAG failed to parse with a `TypeError` because `schedule_interval` is deprecated and removed in Airflow 3.0+.
**Solution**: Updated the DAG definition to use the new `schedule` parameter.

## Data Pipeline

### Airflow DAGs
- **`extract_spatial_data`**: 
  - **Purpose**: Extracts road networks and building footprints from OpenStreetMap (OSM) and historical weather data from Open-Meteo.
  - **Targets**: Lagos, Kogi, and Bayelsa states in Nigeria.
  - **Logic**: Each task runs in an isolated pod (KubernetesExecutor). Uses `osmnx` for spatial data and `requests` for weather APIs.
  - **Output**: Raw data is stored in `/opt/airflow/data/raw/` on the shared `data-pvc`.

- **`transform_and_load`**:
  - **Purpose**: Cleans raw data, reprojects to `EPSG:4326`, and loads it into PostGIS.
  - **Tables**: `buildings`, `roads`, `rainfall`.
  - **Logic**: Uses `GeoPandas` for spatial transformations and `GeoAlchemy2` for PostGIS loading. Adds spatial GIST indexes to geometry columns.

## Superset Configuration & Visualization

### 1. Automating Connection
Run the following commands to connect Superset to PostGIS and create datasets:
```bash
# Upload the init script to the Superset pod
export SUPERSET_POD=$(kubectl get pods -n geodata -l app=superset -o jsonpath='{.items[0].metadata.name}')
kubectl cp scripts/superset_init_geodata.py geodata/$SUPERSET_POD:/tmp/superset_init_geodata.py

# Execute the script via Superset shell
kubectl exec -it $SUPERSET_POD -n geodata -- superset shell < scripts/superset_init_geodata.py
```

### 2. Accessing the UI
1. **Port-Forward**:
   ```bash
   kubectl port-forward service/superset 8088:8088 -n geodata
   ```
2. **Login**:
   - URL: `http://localhost:8088`
   - Default Username: `admin`
   - Default Password: `admin` (Wait for `superset-init` job to complete)

### 3. Creating the Dashboard
To assemble the **Urban Flood Risk Dashboard**:

#### Building Footprints (Deck.gl Polygon)
- **Dataset**: `buildings`
- **Visualization Type**: `deck.gl Polygon`
- **Geometry Column**: `geometry`
- **Styling**: Set opacity to 0.6 and choose a color gradient based on building attributes (if available).

#### Rainfall Data (Deck.gl Scatterplot)
- **Dataset**: `rainfall`
- **Visualization Type**: `deck.gl Scatterplot`
- **Longitude/Latitude**: Use the corresponding columns.
- **Point Radius**: Map to `precipitation_sum` to visualize rainfall intensity.

## How to Deploy
Run the following command in the project root:
```bash
./deploy.sh
```