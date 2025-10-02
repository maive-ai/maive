"""
Standalone script to test Vapi Voice AI integration via HTTP endpoint.

This script makes an HTTP request to the running FastAPI server
to create an outbound call with test customer data.
"""

import asyncio

import httpx

from src.utils.logger import logger


async def main():
    """Create a test outbound call by calling the HTTP endpoint."""
    logger.info("Starting Vapi endpoint test script")

    # Server configuration
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/api/voice-ai/calls"

    # Create the call request payload
    call_payload = {
        "phone_number": "703-268-1917",
        "customer_id": "123",
        "customer_name": "Karik Gupta",
        "company_name": "Robinhood Roofing",
        "customer_address": "2140 Taylor St, San Francisco, CA",
        "claim_number": "5678",
        "date_of_loss": "1/1/2025",
        "insurance_agency": "Statefarm",
        "adjuster_name": "Bruce Lee",
        "adjuster_phone": "703-268-1917",
    }

    logger.info(f"Making POST request to: {endpoint}")
    logger.info(f"Customer: {call_payload['customer_name']}")
    logger.info(f"Phone: {call_payload['phone_number']}")

    # Make HTTP request to the endpoint
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                endpoint,
                json=call_payload,
                # Note: This endpoint requires authentication
                # You may need to add auth headers here
                # headers={"Authorization": "Bearer YOUR_TOKEN"}
            )

            logger.info(f"Response status: {response.status_code}")

            if response.status_code == 201:
                result = response.json()
                logger.info("✅ Call created successfully!")
                logger.info(f"Call ID: {result.get('call_id')}")
                logger.info(f"Status: {result.get('status')}")
                logger.info(f"Provider: {result.get('provider')}")
                logger.info(f"Created at: {result.get('created_at')}")
            else:
                logger.error(f"❌ Call creation failed with status {response.status_code}")
                logger.error(f"Response: {response.text}")

    except httpx.ConnectError:
        logger.error("❌ Could not connect to server. Is it running on localhost:8000?")
        logger.error("Start the server with: cd apps/server && esc run maive/maive-infra/david-dev -- uv run fastapi dev src/main.py")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

