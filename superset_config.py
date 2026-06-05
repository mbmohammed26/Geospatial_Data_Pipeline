# superset_config.py
import os

SQLALCHEMY_DATABASE_URI = 'postgresql://geo_admin:geo_password@postgis:5432/superset'
SECRET_KEY = 'geodata_secret_key_12345'

# Prevent telemetry / notifications warnings in logs if needed
# (Optional) Allow embedding or specific feature flags
FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": True
}
