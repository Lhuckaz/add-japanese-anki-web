import requests
import time
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === CONFIGURATION ===
PORTAINER_URL = os.getenv("PORTAINER_URL", "http://localhost:9000")
USERNAME = os.getenv("PORTAINER_USERNAME")
PASSWORD = os.getenv("PORTAINER_PASSWORD")
ENDPOINT_ID = os.getenv("PORTAINER_ENDPOINT_ID", "1")
CONTAINER_ID = os.getenv("PORTAINER_CONTAINER_ID")

# === AUTHENTICATE AND GET JWT TOKEN ===
def get_jwt_token():
    url = f"{PORTAINER_URL}/api/auth"
    payload = {"Username": USERNAME, "Password": PASSWORD}
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()["jwt"]

# === STOP THE CONTAINER ===
def stop_container(jwt_token):
    url = f"{PORTAINER_URL}/api/endpoints/{ENDPOINT_ID}/docker/containers/{CONTAINER_ID}/stop"
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = requests.post(url, headers=headers)
    
    if response.status_code == 204:
        logger.info(f"Container '{CONTAINER_ID}' stopped successfully.")
    elif response.status_code == 304:
        logger.info(f"Container '{CONTAINER_ID}' is already stopped.")
    else:
        logger.error(f"Failed to stop container: {response.status_code} - {response.text}")
        raise Exception(f"Failed to stop container")
        
# === START CONTAINER ===
def start_container(jwt_token):
    url = f"{PORTAINER_URL}/api/endpoints/{ENDPOINT_ID}/docker/containers/{CONTAINER_ID}/start"
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = requests.post(url, headers=headers)

    if response.status_code == 204:
        logger.info(f"Container '{CONTAINER_ID}' started successfully.")
    elif response.status_code == 304:
        logger.info(f"Container '{CONTAINER_ID}' is already running.")
    else:
        logger.error(f"Failed to start container: {response.status_code} - {response.text}")
        raise Exception(f"Failed to start container")
        
def get_container_status(jwt_token):
    url = f"{PORTAINER_URL}/api/endpoints/{ENDPOINT_ID}/docker/containers/{CONTAINER_ID}/json"
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    return data["State"]["Status"]  # e.g., "running", "exited"

def handle_container():
    try:
        token = get_jwt_token()
        status = get_container_status(token)

        logger.info(f"Current container status: {status}")

        if status == "exited" or status == "created":
            start_container(token)
            logger.info(f"Waiting...")
            time.sleep(10)
        elif status == "running":
            logger.info(f"Container '{CONTAINER_ID}' is already running.")
        else:
            logger.warning(f"Container is in an unexpected state: {status}")
            raise Exception(f"Container is in an unexpected state")
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise e