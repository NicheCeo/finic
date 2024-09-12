import io
from fastapi import UploadFile
from typing import List, Optional, Tuple, Dict
from models.models import (
    AppConfig,
    User,
    FinicEnvironment,
    Agent,
    Execution,
    ExecutionStatus,
    ExecutionAttempt,
)
from supabase import create_client, Client
import os
from storage3.utils import StorageException

from io import StringIO
from bs4 import BeautifulSoup
import pandas as pd
import httpx
import datetime
import tempfile
import pdb
from collections import deque
from database import Database
import json
from google.cloud import run_v2
from google.oauth2 import service_account
import uuid


class AgentRunner:
    def __init__(
        self,
    ):
        service_account_info = json.loads(os.getenv("GCLOUD_SERVICE_ACCOUNT"))
        self.credentials = service_account.Credentials.from_service_account_info(
            service_account_info
        )
        self.project = os.getenv("GCLOUD_PROJECT")
        self.location = os.getenv("GCLOUD_LOCATION")

    async def start_agent(
        self, secret_key: str, agent: Agent, input: Dict
    ) -> Execution:
        client = run_v2.JobsClient(credentials=self.credentials)
        execution_id = str(uuid.uuid4())
        print("secret_key", secret_key)
        request = run_v2.RunJobRequest(
            name=f"projects/{self.project}/locations/{self.location}/jobs/{Agent.get_cloud_job_id(agent)}",
            overrides={
                "container_overrides": [
                    {
                        "env": [
                            {"name": "FINIC_ENV", "value": FinicEnvironment.PROD.value},
                            {"name": "FINIC_INPUT", "value": json.dumps(input)},
                            {"name": "FINIC_API_KEY", "value": secret_key},
                            {"name": "FINIC_AGENT_ID", "value": agent.id},
                            {"name": "FINIC_EXECUTION_ID", "value": execution_id},
                        ]
                    }
                ]
            },
        )
        operation = client.run_job(request)

        execution_path = operation.metadata.name
        cloud_provider_id = execution_path.split("/")[-1]
        print(f"Started execution: {execution_id}")
        return Execution(
            id=execution_id,
            finic_agent_id=agent.finic_id,
            user_defined_agent_id=agent.id,
            app_id=agent.app_id,
            cloud_provider_id=cloud_provider_id,
            status=ExecutionStatus.running,
            start_time=datetime.datetime.now(),
        )

    async def update_execution(
        self,
        agent: Agent,
        execution: Execution,
        attempt: ExecutionAttempt,
        results: Dict,
    ):
        # Update the execution status
        if attempt.success:
            execution.status = ExecutionStatus.successful
            execution.end_time = datetime.datetime.now()
        elif len(execution.attempts) == agent.num_retries:
            execution.status = ExecutionStatus.failed
            execution.end_time = datetime.datetime.now()
        else:
            execution.status = ExecutionStatus.running

        # Add the attempt to the execution
        execution.attempts.append(attempt.dict())

        execution.results = results

        return execution
