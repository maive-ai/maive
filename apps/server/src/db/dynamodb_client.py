"""
DynamoDB client initialization and configuration.

Provides a singleton DynamoDB resource for accessing tables.
"""

import os
from functools import lru_cache

import boto3
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource

from src.utils.logger import logger


@lru_cache(maxsize=1)
def get_dynamodb_resource() -> DynamoDBServiceResource:
    """
    Get a cached DynamoDB resource instance.

    Returns:
        DynamoDBServiceResource: Boto3 DynamoDB resource

    Raises:
        ValueError: If required environment variables are not set
    """
    region = os.getenv("AWS_REGION")
    if not region:
        raise ValueError("AWS_REGION environment variable is required")

    logger.info(f"[DynamoDB Client] Initializing DynamoDB resource in region: {region}")

    # Initialize DynamoDB resource
    dynamodb = boto3.resource("dynamodb", region_name=region)

    return dynamodb


def get_table_name() -> str:
    """
    Get the DynamoDB table name from environment variables.

    Returns:
        str: The table name

    Raises:
        ValueError: If DYNAMODB_ACTIVE_CALLS is not set
    """
    table_name = os.getenv("DYNAMODB_ACTIVE_CALLS")
    if not table_name:
        raise ValueError("DYNAMODB_ACTIVE_CALLS environment variable is required")

    return table_name
