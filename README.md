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

## How to Deploy
Run the following command in the project root:
```bash
./deploy.sh
```