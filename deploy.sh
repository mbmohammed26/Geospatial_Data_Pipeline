#!/bin/bash

# Exit on error
set -e

NAMESPACE="geodata"
SECRET_KEY="geodata_secret_key_$(openssl rand -hex 16)"

echo "Creating namespace: $NAMESPACE"
kubectl create namespace $NAMESPACE || echo "Namespace already exists"

echo "Adding Helm repositories"
helm repo add apache-airflow https://airflow.apache.org
helm repo add superset https://apache.github.io/superset
helm repo update

echo "Deploying Infrastructure Manifests"
kubectl apply -f k8s/postgis-deployment.yaml
kubectl apply -f k8s/data-pvc.yaml

echo "Waiting for PostGIS to be ready..."
kubectl rollout status statefulset/postgis -n $NAMESPACE --timeout=5m

echo "Installing Apache Airflow with KubernetesExecutor"
# We enable dags.persistence to ensure DAGs are available to worker pods
# We mount data-pvc to /opt/airflow/data/raw
helm upgrade --install airflow apache-airflow/airflow \
  --namespace $NAMESPACE \
  --set executor=KubernetesExecutor \
  --set labels.project=flood-risk \
  --set postgresql.enabled=true \
  --set migrateDatabaseJob.enabled=true \
  --set migrateDatabaseJob.useHelmHooks=false \
  --set createUserJob.enabled=true \
  --set createUserJob.useHelmHooks=false \
  --set dags.persistence.enabled=true \
  --set dags.persistence.size=1Gi \
  --set "extraPipPackages={geopandas,shapely,sqlalchemy,geoalchemy2,osmnx,requests}" \
  --set "workers.extraVolumes[0].name=data-volume" \
  --set "workers.extraVolumes[0].persistentVolumeClaim.claimName=data-pvc" \
  --set "workers.extraVolumeMounts[0].name=data-volume" \
  --set "workers.extraVolumeMounts[0].mountPath=/opt/airflow/data/raw" \
  --wait --timeout 20m0s

echo "Installing Apache Superset"
helm upgrade --install superset superset/superset \
  --namespace $NAMESPACE \
  --set labels.project=flood-risk \
  --set image.repository=apache/superset \
  --set image.tag=5.0.0-dev \
  --set "configOverrides.secret=SECRET_KEY = '$SECRET_KEY'" \
  --set postgresql.enabled=true \
  --wait --timeout 20m0s

echo "Infrastructure scaffolding complete!"
