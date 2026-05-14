import os
import time
import json
import requests
import osmnx as ox
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# Configuration
STATES = ['Lagos, Nigeria', 'Kogi, Nigeria', 'Bayelsa, Nigeria']
RAW_DATA_PATH = '/opt/airflow/data/raw/'

# Coordinates for Open-Meteo (Approximate centers)
STATE_COORDINATES = {
    'Lagos, Nigeria': {'lat': 6.5244, 'lon': 3.3792},
    'Kogi, Nigeria': {'lat': 7.7985, 'lon': 6.7327},
    'Bayelsa, Nigeria': {'lat': 4.9330, 'lon': 6.2676}
}

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def extract_osm_data(**kwargs):
    ensure_dir(RAW_DATA_PATH)
    
    for state in STATES:
        print(f"Extracting OSM data for {state}...")
        
        # Road Network
        print(f"Fetching road network for {state}...")
        G = ox.graph_from_place(state, network_type='drive')
        ox.save_graphml(G, filepath=os.path.join(RAW_DATA_PATH, f"{state.replace(', ', '_')}_roads.graphml"))
        
        time.sleep(5) # Internal sleep between road and building requests
        
        # Building Footprints
        print(f"Fetching building footprints for {state}...")
        try:
            buildings = ox.features_from_place(state, tags={"building": True})
            buildings.to_file(os.path.join(RAW_DATA_PATH, f"{state.replace(', ', '_')}_buildings.geojson"), driver='GeoJSON')
        except Exception as e:
            print(f"No buildings found or error for {state}: {e}")
            
        print(f"Completed OSM extraction for {state}. Sleeping for 10s to avoid API rate limits.")
        time.sleep(10)

def extract_weather_data(**kwargs):
    ensure_dir(RAW_DATA_PATH)
    
    # Yesterday's date for historical data
    target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    for state in STATES:
        coords = STATE_COORDINATES.get(state)
        print(f"Fetching weather data for {state} ({coords['lat']}, {coords['lon']})...")
        
        # Open-Meteo Archive API
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": coords['lat'],
            "longitude": coords['lon'],
            "start_date": target_date,
            "end_date": target_date,
            "daily": "rain_sum,precipitation_sum,showers_sum",
            "timezone": "Africa/Lagos"
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            with open(os.path.join(RAW_DATA_PATH, f"{state.replace(', ', '_')}_weather.json"), 'w') as f:
                json.dump(data, f)
            print(f"Saved weather data for {state}")
        else:
            print(f"Failed to fetch weather data for {state}: {response.status_code}")
            
        time.sleep(2) # Small delay for rate limits

with DAG(
    'extract_spatial_data',
    default_args=default_args,
    description='Extract OSM and Weather data for Nigeria Flood Risk Assessment',
    schedule=timedelta(days=1),
    catchup=False,
    tags=['geospatial', 'nigeria', 'flood-risk'],
) as dag:

    osm_task = PythonOperator(
        task_id='extract_osm_infrastructure',
        python_callable=extract_osm_data,
    )

    weather_task = PythonOperator(
        task_id='extract_weather_data',
        python_callable=extract_weather_data,
    )

    # Note: In a production environment, we'd use a dedicated container or 
    # ensure the script is in the PYTHONPATH. For this scaffold, we'll run it as a task.
    def run_transform_and_load():
        # Using import instead of subprocess for better integration if in the same volume
        import sys
        sys.path.append('/opt/airflow/dags/repo/scripts') # Assuming git-sync or similar
        sys.path.append('/opt/airflow/dags/scripts')
        from transform_and_load import transform_and_load_spatial, transform_and_load_rainfall, create_spatial_indexes
        transform_and_load_spatial()
        transform_and_load_rainfall()
        create_spatial_indexes()

    transform_task = PythonOperator(
        task_id='transform_and_load_to_postgis',
        python_callable=run_transform_and_load,
    )

    osm_task >> weather_task >> transform_task
