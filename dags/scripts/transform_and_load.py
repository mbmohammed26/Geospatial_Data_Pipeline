import os
import glob
import json
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine, text
from geoalchemy2 import Geometry, WKTElement

# Configuration
RAW_DATA_PATH = '/opt/airflow/data/raw/'
DB_URL = "postgresql://geo_admin:geo_password@postgis:5432/geodata"
TARGET_CRS = "EPSG:4326"

def get_engine():
    return create_engine(DB_URL)

def transform_and_load_spatial():
    engine = get_engine()
    
    # Drop existing tables to avoid duplicate rows and ensure consistent schemas
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS buildings;"))
        conn.execute(text("DROP TABLE IF EXISTS roads;"))
        conn.commit()
    
    # Process Buildings
    building_files = glob.glob(os.path.join(RAW_DATA_PATH, "*_buildings.geojson"))
    for file in building_files:
        state = os.path.basename(file).split('_buildings')[0]
        print(f"Processing buildings for {state}...")
        
        gdf = gpd.read_file(file)
        
        # CRS Check and Reprojection
        if gdf.crs is None:
            print(f"Warning: {file} has no CRS. Assuming EPSG:4326")
            gdf.set_crs(TARGET_CRS, allow_override=True, inplace=True)
        elif gdf.crs != TARGET_CRS:
            print(f"Reprojecting {state} buildings from {gdf.crs} to {TARGET_CRS}")
            gdf = gdf.to_crs(TARGET_CRS)
            
        # Cleaning: Drop null geometries
        initial_count = len(gdf)
        gdf = gdf[gdf.geometry.notnull()]
        gdf = gdf[~gdf.geometry.is_empty]
        print(f"Cleaned {initial_count - len(gdf)} empty/null geometries.")
        
        # Load to PostGIS
        # Keep consistent columns to prevent database schema mismatch errors on append
        gdf['state'] = state
        cols_to_keep = ['name', 'building', 'amenity', 'geometry', 'state']
        gdf_subset = gdf[[c for c in cols_to_keep if c in gdf.columns]].copy()
        
        gdf_subset.to_postgis("buildings", engine, if_exists="append", index=False, 
                              dtype={'geometry': Geometry('GEOMETRY', srid=4326)})
        print(f"Loaded buildings for {state} to PostGIS.")

    # Process Roads
    road_files = glob.glob(os.path.join(RAW_DATA_PATH, "*_roads.graphml"))
    # Note: osmnx graphml can be read into GeoPandas nodes and edges
    import osmnx as ox
    for file in road_files:
        state = os.path.basename(file).split('_roads')[0]
        print(f"Processing roads for {state}...")
        
        G = ox.load_graphml(file)
        nodes, edges = ox.graph_to_gdfs(G)
        
        # Reproject Edges
        if edges.crs != TARGET_CRS:
            edges = edges.to_crs(TARGET_CRS)
        
        # Clean Edges
        edges = edges[edges.geometry.notnull()]
        edges['state'] = state
        
        # Load to PostGIS
        # Simplifying edges for database storage (OSMNX edges have complex structure)
        # We'll just take the basic columns
        cols_to_keep = ['osmid', 'name', 'highway', 'oneway', 'length', 'geometry', 'state']
        edges_subset = edges[[c for c in cols_to_keep if c in edges.columns]]
        
        edges_subset.to_postgis("roads", engine, if_exists="append", index=False,
                                dtype={'geometry': Geometry('GEOMETRY', srid=4326)})
        print(f"Loaded roads for {state} to PostGIS.")

def transform_and_load_rainfall():
    engine = get_engine()
    weather_files = glob.glob(os.path.join(RAW_DATA_PATH, "*_weather.json"))
    
    for file in weather_files:
        state = os.path.basename(file).split('_weather')[0]
        print(f"Processing weather data for {state}...")
        
        with open(file, 'r') as f:
            data = json.load(f)
            
        # Extract daily data
        daily = data.get('daily', {})
        if not daily:
            continue
            
        df = pd.DataFrame(daily)
        df['state'] = state
        df['latitude'] = data.get('latitude')
        df['longitude'] = data.get('longitude')
        
        # Load to PostGIS
        df.to_sql("rainfall", engine, if_exists="append", index=False)
        print(f"Loaded rainfall for {state} to PostGIS.")

def create_spatial_indexes():
    engine = get_engine()
    with engine.connect() as conn:
        print("Creating spatial indexes...")
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_buildings_geom ON buildings USING GIST (geometry);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_roads_geom ON roads USING GIST (geometry);"))
            conn.commit()
        except Exception as e:
            print(f"Error creating indexes (tables might not exist yet): {e}")
        print("Spatial index creation attempt completed.")

if __name__ == "__main__":
    # Ensure tables exist with spatial columns if needed
    # (to_postgis handles this, but indexes are separate)
    transform_and_load_spatial()
    transform_and_load_rainfall()
    create_spatial_indexes()
