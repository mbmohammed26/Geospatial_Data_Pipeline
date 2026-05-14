#!/bin/bash

# Exit on error
set -e

NAMESPACE="geodata"

echo "Creating namespace: $NAMESPACE"
kubectl create namespace $NAMESPACE || echo "Namespace already exists"

echo "Adding Helm repositories"
helm repo add apache-airflow https://airflow.apache.org
helm repo add superset https://apache.github.io/superset
helm repo update

echo "Deploying PostGIS"
kubectl apply -f k8s/postgis-deployment.yaml

echo "Installing Apache Airflow with KubernetesExecutor"
helm upgrade --install airflow apache-airflow/airflow \
  --namespace $NAMESPACE \
  --set executor=KubernetesExecutor \
  --set labels.project=flood-risk \
  --wait --timeout 10m0s

echo "Installing Apache Superset"
helm upgrade --install superset superset/superset \
  --namespace $NAMESPACE \
  --set labels.project=flood-risk \
  --wait --timeout 10m0s

echo "Infrastructure scaffolding complete!"
