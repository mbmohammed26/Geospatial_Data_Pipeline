-- Initialize databases for the services
CREATE DATABASE airflow;
CREATE DATABASE superset;

-- Grant privileges (optional but good practice for local admin)
GRANT ALL PRIVILEGES ON DATABASE airflow TO geo_admin;
GRANT ALL PRIVILEGES ON DATABASE superset TO geo_admin;

-- Connect to geodata database and enable PostGIS extension
\c geodata
CREATE EXTENSION IF NOT EXISTS postgis;
