-- Initialize databases for the services
CREATE DATABASE airflow;
CREATE DATABASE superset;
CREATE DATABASE geodata;

-- Grant privileges (optional but good practice for local admin)
GRANT ALL PRIVILEGES ON DATABASE airflow TO geo_admin;
GRANT ALL PRIVILEGES ON DATABASE superset TO geo_admin;
GRANT ALL PRIVILEGES ON DATABASE geodata TO geo_admin;
