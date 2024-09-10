from typing import Dict
from functools import wraps
import json
import os
from enum import Enum
import requests


class FinicEnvironment(str, Enum):
    LOCAL = "local"
    DEV = "dev"
    PROD = "prod"


class Finic:
    def __init__(
        self,
        api_key: str,
        environment: FinicEnvironment = FinicEnvironment.LOCAL,
        url: str = "https://finic-521298051240.us-central1.run.app",
    ):
        finic_env = os.environ.get("FINIC_ENV")
        self.environment = FinicEnvironment(finic_env) if finic_env else environment
        self.api_key = api_key
        self.secrets_manager = FinicSecretsManager(api_key, environment=environment)
        self.url = url

    def deploy_job(self, job_id: str, job_name: str, project_zipfile: str):
        with open(project_zipfile, "rb") as f:
            upload_file = f.read()

        response = requests.post(
            f"{self.url}/get-job-upload-link",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "job_id": job_id,
                "job_name": job_name,
            },
        )

        response_json = response.json()

        upload_link = response_json["upload_link"]

        # Upload the project zip file to the upload link
        requests.put(upload_link, data=upload_file)

        print("Project files uploaded for build. Deploying job...")

        response = requests.post(
            f"{self.url}/deploy-job",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "job_id": job_id,
                "job_name": job_name,
            },
        )

        response_json = response.json()

        if "id" in response_json:
            return "Job deployed successfully"
        else:
            return "Error in deploying job"

    def start_run(self, job_id: str, input_data: Dict):
        # TODO
        pass

    def get_runs(self, job_id: str):
        # TODO
        pass

    def get_run_status(self, job_id: str, run_id: str):
        # TODO
        pass

    def log_run_status(self, job_id: str, status: str, message: str):
        # TODO
        print(f"Logging status: {status} - {message}")

    def workflow_entrypoint(self, func):

        if self.environment == FinicEnvironment.LOCAL:
            # Check if input.json file is present
            path = os.path.join(os.getcwd(), "input.json")
            if not os.path.exists(path):
                raise Exception(
                    "If you are running the job locally, please provide input.json file in the base directory containing pyproject.toml"
                )

            try:
                with open(path, "r") as f:
                    input_data = json.load(f)
            except Exception as e:
                raise Exception("Error in reading input.json file: ", e)
        else:
            try:
                input_data = json.loads(os.environ.get("FINIC_INPUT"))
            except Exception as e:
                raise Exception("Error in parsing input data: ", e)

        @wraps(func)
        def wrapper():
            try:
                self.log_run_status("job_id", "running", "Job started")
                func(input_data)
                self.log_run_status("job_id", "success", "Job completed")
            except Exception as e:
                print("Error in job: ", e)

        return wrapper


class FinicSecretsManager:
    def __init__(self, api_key, environment: FinicEnvironment):
        self.api_key = api_key
        self.environment = environment

    def save_credentials(self, credentials: Dict, credential_id: str):
        if self.environment == FinicEnvironment.LOCAL:
            raise Exception(
                "Cannot save credentials in local environment. Save them in secrets.json for local testing"
            )
        else:
            # Save secrets in Finic API
            pass

    def get_credentials(self, credential_id: str):
        if self.environment == FinicEnvironment.LOCAL:
            # Check if secrets.json file is present
            path = os.path.join(os.getcwd(), "secrets.json")
            if not os.path.exists(path):
                raise Exception(
                    "If you are running the workflow locally, please provide secrets.json file in the base directory containing pyproject.toml"
                )

            try:
                with open(path, "r") as f:
                    secrets = json.load(f)
                    return secrets.get(credential_id, {})
            except Exception as e:
                raise Exception("Error in reading secrets.json file: ", e)
        else:
            # Fetch secrets from Finic API
            pass