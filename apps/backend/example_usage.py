#!/usr/bin/env python3
"""Example usage of the Rilla API client.

This script demonstrates how to use the RillaClient to export data from Rilla.
Make sure to set the RILLA_API_KEY environment variable before running.

Usage:
    RILLA_API_KEY=your-api-key uv run python example_usage.py
"""

import asyncio
import os
from datetime import datetime, timedelta

from backend.rilla import (
    RillaClient,
    ConversationsExportRequest,
    TeamsExportRequest,
    UsersExportRequest,
    RillaAuthenticationError,
    RillaBadRequestError,
)


async def main():
    """Main example function."""
    # Check if API key is set
    api_key = os.getenv("RILLA_API_KEY")
    if not api_key:
        print("❌ Please set the RILLA_API_KEY environment variable")
        print("   Example: RILLA_API_KEY=your-api-key uv run python example_usage.py")
        return

    print("🚀 Rilla API Client Example")
    print("=" * 50)

    # Define date range (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    print(f"📅 Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print()

    try:
        async with RillaClient(api_key=api_key) as client:
            # Example 1: Export conversations (first page)
            print("💬 Exporting conversations (first page)...")
            conversations_request = ConversationsExportRequest(
                from_date=start_date,
                to_date=end_date,
                page=1,
                limit=5  # Small limit for demo
            )

            conversations_response = await client.export_conversations(conversations_request)
            print(f"   Found {conversations_response.total_conversations} total conversations")
            print(f"   Showing page {conversations_response.current_page} of {conversations_response.total_pages}")
            print(f"   Conversations on this page: {len(conversations_response.conversations)}")

            for i, conv in enumerate(conversations_response.conversations[:3], 1):
                duration_mins = conv.duration // 60
                print(f"   {i}. {conv.title} ({duration_mins}m) - {conv.user.name}")

            print()

            # Example 2: Export teams
            print("👥 Exporting teams...")
            teams_request = TeamsExportRequest(
                from_date=start_date,
                to_date=end_date
            )

            teams_response = await client.export_teams(teams_request)
            print(f"   Found {len(teams_response.teams)} teams")

            for i, team in enumerate(teams_response.teams[:3], 1):
                compliance = team.recording_compliance * 100
                print(f"   {i}. {team.name}: {team.conversations_recorded} conversations ({compliance:.1f}% compliance)")

            print()

            # Example 3: Export users
            print("👤 Exporting users...")
            users_request = UsersExportRequest(
                from_date=start_date,
                to_date=end_date
            )

            users_response = await client.export_users(users_request)
            print(f"   Found {len(users_response.users)} users")

            for i, user in enumerate(users_response.users[:3], 1):
                talk_ratio = user.talk_ratio_average * 100 if user.talk_ratio_average else 0
                print(f"   {i}. {user.name} ({user.role}): {user.conversations_recorded} conversations ({talk_ratio:.1f}% talk ratio)")

            print()

            # Example 4: Auto-pagination (be careful with large datasets!)
            print("🔄 Demonstrating auto-pagination (limited to 10 conversations)...")
            small_request = ConversationsExportRequest(
                from_date=start_date,
                to_date=end_date,
                limit=5  # Small pages for demo
            )

            # Get all conversations (this could be many!)
            all_conversations = await client.get_all_conversations(small_request)
            print(f"   Retrieved {len(all_conversations)} conversations across all pages")

            # Show summary stats
            if all_conversations:
                total_duration = sum(conv.duration for conv in all_conversations)
                avg_duration = total_duration / len(all_conversations)
                print(f"   Average conversation duration: {avg_duration/60:.1f} minutes")

                # Count by outcome
                outcomes = {}
                for conv in all_conversations:
                    outcome = conv.outcome or "unknown"
                    outcomes[outcome] = outcomes.get(outcome, 0) + 1

                print("   Outcomes:")
                for outcome, count in outcomes.items():
                    print(f"     {outcome}: {count}")

    except RillaAuthenticationError:
        print("❌ Authentication failed. Please check your API key.")
    except RillaBadRequestError as e:
        print(f"❌ Bad request: {e.message}")
        if e.response_data:
            print(f"   Details: {e.response_data}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise

    print()
    print("✅ Example completed successfully!")
    print()
    print("💡 Tips:")
    print("   - Use environment variables for configuration (RILLA_BASE_URL, RILLA_TIMEOUT, etc.)")
    print("   - Enable request/response logging with RILLA_LOG_REQUESTS=true")
    print("   - Use specific user email filters to reduce data volume")
    print("   - Be mindful of rate limits when processing large datasets")


if __name__ == "__main__":
    asyncio.run(main())
