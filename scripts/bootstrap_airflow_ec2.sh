#!/usr/bin/env bash
set -euo pipefail

# Reference bootstrap script for EC2 LocalExecutor.
# Review before running on a real server.

sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip build-essential libpq-dev
python3.11 -m venv ~/airflow-venv
source ~/airflow-venv/bin/activate
pip install --upgrade pip
pip install -r requirements-airflow.txt
export AIRFLOW_HOME=~/airflow
airflow db migrate
airflow users create --username admin --firstname admin --lastname admin --role Admin --email admin@example.com --password admin
