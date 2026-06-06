# superset_config.py
import os

SQLALCHEMY_DATABASE_URI = 'postgresql://geo_admin:geo_password@postgis:5432/superset'
SECRET_KEY = 'geodata_secret_key_12345'

# Prevent telemetry / notifications warnings in logs if needed
# (Optional) Allow embedding or specific feature flags
FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": True
}

# Add your free Mapbox API token here (starts with 'pk.') to enable deck.gl maps
# MAPBOX_API_KEY = 'pk.YOUR_MAPBOX_TOKEN_HERE'
