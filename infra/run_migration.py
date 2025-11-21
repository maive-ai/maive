#!/usr/bin/env python3
"""
Script to run database migrations via ECS Fargate task.

This script is called by Pulumi during deployment to automatically
apply database migrations before updating ECS services.
"""

import json
import sys
import time
from typing import Any

import boto3


def run_migration(
    cluster_name: str,
    task_definition_arn: str,
    subnet_ids: list[str],
    security_group_id: str,
    log_group_name: str,
) -> int:
    """
    Run database migration task in ECS Fargate.

    Args:
        cluster_name: ECS cluster name
        task_definition_arn: Migration task definition ARN
        subnet_ids: List of subnet IDs for the task
        security_group_id: Security group ID for the task
        log_group_name: CloudWatch log group name for checking logs

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    ecs_client = boto3.client("ecs")
    logs_client = boto3.client("logs")

    print(f"🚀 Running database migrations...")
    print(f"   Cluster: {cluster_name}")
    print(f"   Task Definition: {task_definition_arn}")

    # Start the migration task
    try:
        response = ecs_client.run_task(
            cluster=cluster_name,
            taskDefinition=task_definition_arn,
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": subnet_ids,
                    "securityGroups": [security_group_id],
                    "assignPublicIp": "ENABLED",
                }
            },
        )

        if response.get("failures"):
            print(f"❌ Failed to start migration task: {response['failures']}")
            return 1

        task_arn = response["tasks"][0]["taskArn"]
        task_id = task_arn.split("/")[-1]
        print(f"✅ Migration task started: {task_id}")

    except Exception as e:
        print(f"❌ Error starting migration task: {e}")
        return 1

    # Wait for task to start running
    print("⏳ Waiting for task to start...")
    try:
        waiter = ecs_client.get_waiter("tasks_running")
        waiter.wait(
            cluster=cluster_name,
            tasks=[task_arn],
            WaiterConfig={"Delay": 5, "MaxAttempts": 60},
        )
        print("✅ Task is running")
    except Exception as e:
        print(f"⚠️  Task may not have started properly: {e}")

    # Wait for task to complete
    print("⏳ Waiting for migrations to complete...")
    try:
        waiter = ecs_client.get_waiter("tasks_stopped")
        waiter.wait(
            cluster=cluster_name,
            tasks=[task_arn],
            WaiterConfig={"Delay": 10, "MaxAttempts": 120},  # 20 minutes max
        )
    except Exception as e:
        print(f"❌ Error waiting for task to complete: {e}")
        return 1

    # Check exit code
    try:
        response = ecs_client.describe_tasks(cluster=cluster_name, tasks=[task_arn])
        container = response["tasks"][0]["containers"][0]
        exit_code = container.get("exitCode")

        if exit_code == 0:
            print("✅ Migrations completed successfully!")

            # Try to get the last few log lines
            try:
                log_stream_name = f"migration/{container['name']}/{task_id}"
                log_response = logs_client.get_log_events(
                    logGroupName=log_group_name,
                    logStreamName=log_stream_name,
                    limit=10,
                    startFromHead=False,
                )

                if log_response.get("events"):
                    print("\n📋 Last migration logs:")
                    for event in log_response["events"]:
                        print(f"   {event['message']}")
            except Exception:
                pass  # Log retrieval is optional

            return 0
        else:
            print(f"❌ Migration failed with exit code: {exit_code}")
            print(f"   Check logs at: CloudWatch Logs > {log_group_name}")
            print(
                f"   Log stream: migration/{container['name']}/{task_id}"
            )
            return 1

    except Exception as e:
        print(f"❌ Error checking task exit code: {e}")
        return 1


def main() -> int:
    """Main entry point."""
    if len(sys.argv) != 6:
        print("Usage: run_migration.py <cluster> <task_def> <subnet1,subnet2> <sg> <log_group>")
        return 1

    cluster_name = sys.argv[1]
    task_definition_arn = sys.argv[2]
    subnet_ids = sys.argv[3].split(",")
    security_group_id = sys.argv[4]
    log_group_name = sys.argv[5]

    return run_migration(
        cluster_name,
        task_definition_arn,
        subnet_ids,
        security_group_id,
        log_group_name,
    )


if __name__ == "__main__":
    sys.exit(main())
