import os
import time
import json
import requests
import osmnx as ox
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

# Configuration
STATES = ['Ikeja, Lagos, Nigeria', 'Kogi, Nigeria', 'Bayelsa, Nigeria']
RAW_DATA_PATH = '/opt/airflow/data/raw/'

# Configure OSMnx to use alternative Overpass API endpoint to bypass rate limits
ox.settings.overpass_url = "https://overpass.kumi.systems/api/interpreter"

# Coordinates for Open-Meteo
STATE_COORDINATES = {
    'Ikeja, Lagos, Nigeria': {'lat': 6.5965, 'lon': 3.3366},
    'Kogi, Nigeria': {'lat': 7.7985, 'lon': 6.7327},
    'Bayelsa, Nigeria': {'lat': 4.9330, 'lon': 6.2676}
}

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=1),
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
        try:
            G = ox.graph_from_place(state, network_type='drive')
            ox.save_graphml(G, filepath=os.path.join(RAW_DATA_PATH, f"{state.replace(', ', '_')}_roads.graphml"))
        except Exception as e:
            print(f"Error fetching road network for {state}: {e}")
        
        time.sleep(10) # API delay to avoid timeouts
        
        # Building Footprints
        print(f"Fetching building footprints for {state}...")
        try:
            # Using tags to limit query scope to buildings
            buildings = ox.features_from_place(state, tags={"building": True})
            buildings.to_file(os.path.join(RAW_DATA_PATH, f"{state.replace(', ', '_')}_buildings.geojson"), driver='GeoJSON')
        except Exception as e:
            print(f"No buildings found or error for {state}: {e}")
            
        print(f"Completed OSM extraction for {state}. Sleeping to avoid API rate limits.")
        time.sleep(10)

def extract_weather_data(**kwargs):
    ensure_dir(RAW_DATA_PATH)
    
    # Fetch data for yesterday
    target_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    
    for state in STATES:
        coords = STATE_COORDINATES.get(state)
        print(f"Fetching weather data for {state} ({coords['lat']}, {coords['lon']})...")
        
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": coords['lat'],
            "longitude": coords['lon'],
            "start_date": target_date,
            "end_date": target_date,
            "daily": "rain_sum,precipitation_sum,showers_sum",
            "timezone": "Africa/Lagos"
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                filename = f"{state.replace(', ', '_')}_weather.json"
                with open(os.path.join(RAW_DATA_PATH, filename), 'w') as f:
                    json.dump(data, f)
                print(f"Saved weather data for {state}")
            else:
                print(f"Failed to fetch weather data for {state}: {response.status_code}")
        except Exception as e:
            print(f"Error calling Open-Meteo API for {state}: {e}")
            
        time.sleep(5) # Delay for API limits

def run_transform_and_load(**kwargs):
    import sys
    sys.path.append('/opt/airflow/dags')
    from scripts.transform_and_load import transform_and_load_spatial, transform_and_load_rainfall, create_spatial_indexes
    transform_and_load_spatial()
    transform_and_load_rainfall()
    create_spatial_indexes()

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

    transform_task = PythonOperator(
        task_id='transform_and_load_to_postgis',
        python_callable=run_transform_and_load,
    )

    # Define execution order
    osm_task >> weather_task >> transform_task
