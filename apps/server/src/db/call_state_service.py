"""
Call state service for managing active call sessions in DynamoDB.

Provides operations for storing, retrieving, and removing active call state.
"""

from botocore.exceptions import ClientError

from src.db.dynamodb_client import get_dynamodb_resource, get_table_name
from src.db.models import ActiveCallState
from src.utils.logger import logger


class CallStateService:
    """Service for managing active call state in DynamoDB."""

    def __init__(self):
        """Initialize the call state service with DynamoDB table."""
        self.dynamodb = get_dynamodb_resource()
        self.table_name = get_table_name()
        self.table = self.dynamodb.Table(self.table_name)
        logger.info(
            f"[CallStateService] Initialized with table: {self.table_name}"
        )

    async def set_active_call(self, call_state: ActiveCallState) -> None:
        """
        Store or update an active call in DynamoDB.

        Args:
            call_state: The active call state to store

        Raises:
            Exception: If the DynamoDB operation fails
        """
        try:
            item = call_state.to_dynamodb_item()
            self.table.put_item(Item=item)

            logger.info(
                f"[CallStateService] Stored active call {call_state.call_id} for user {call_state.user_id}"
            )

        except ClientError as e:
            error_msg = f"Failed to store active call: {e.response['Error']['Message']}"
            logger.error(f"[CallStateService] {error_msg}")
            raise Exception(error_msg) from e

    async def get_active_call(self, user_id: str) -> ActiveCallState | None:
        """
        Retrieve the active call for a user.

        Args:
            user_id: The Cognito user ID (sub)

        Returns:
            ActiveCallState if found, None otherwise

        Raises:
            Exception: If the DynamoDB operation fails
        """
        try:
            response = self.table.get_item(
                Key={"PK": f"user_{user_id}", "SK": f"ACTIVE#user_{user_id}"}
            )

            if "Item" not in response:
                logger.info(
                    f"[CallStateService] No active call found for user {user_id}"
                )
                return None

            call_state = ActiveCallState.from_dynamodb_item(response["Item"])
            logger.info(
                f"[CallStateService] Retrieved active call {call_state.call_id} for user {user_id}"
            )

            return call_state

        except ClientError as e:
            error_msg = (
                f"Failed to retrieve active call: {e.response['Error']['Message']}"
            )
            logger.error(f"[CallStateService] {error_msg}")
            raise Exception(error_msg) from e

    async def remove_active_call(self, user_id: str) -> None:
        """
        Remove the active call for a user.

        Args:
            user_id: The Cognito user ID (sub)

        Raises:
            Exception: If the DynamoDB operation fails
        """
        try:
            self.table.delete_item(
                Key={"PK": f"user_{user_id}", "SK": f"ACTIVE#user_{user_id}"}
            )

            logger.info(
                f"[CallStateService] Removed active call for user {user_id}"
            )

        except ClientError as e:
            error_msg = (
                f"Failed to remove active call: {e.response['Error']['Message']}"
            )
            logger.error(f"[CallStateService] {error_msg}")
            raise Exception(error_msg) from e
