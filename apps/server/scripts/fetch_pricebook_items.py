"""
Script to fetch and log all pricebook items from Service Titan.

This script fetches materials, services, and equipment from the Service Titan
Pricebook API and logs them in a structured format.

Usage:
    uv run python scripts/fetch_pricebook_items.py
"""

import asyncio
import json
from pathlib import Path

from src.integrations.crm.config import get_crm_settings
from src.integrations.crm.providers.service_titan import ServiceTitanProvider
from src.integrations.crm.schemas import PricebookItemsRequest
from src.utils.logger import logger


async def fetch_all_items(
    provider: ServiceTitanProvider, item_type: str, max_pages: int | None = None
) -> list[dict]:
    """
    Fetch all items of a specific type from the pricebook.

    Args:
        provider: ServiceTitanProvider instance
        item_type: Type of items to fetch ("materials", "services", or "equipment")
        max_pages: Maximum number of pages to fetch (None for all pages)

    Returns:
        List of all items
    """
    config = get_crm_settings()
    tenant_id = config.provider_config.tenant_id

    all_items = []
    page = 1
    has_more = True

    while has_more and (max_pages is None or page <= max_pages):
        request = PricebookItemsRequest(
            tenant=tenant_id, page=page, page_size=50, active="True"
        )

        if item_type == "materials":
            response = await provider.get_pricebook_materials(request)
        elif item_type == "services":
            response = await provider.get_pricebook_services(request)
        elif item_type == "equipment":
            response = await provider.get_pricebook_equipment(request)
        else:
            raise ValueError(f"Invalid item type: {item_type}")

        # Convert Pydantic models to dicts
        items = [item.model_dump(by_alias=True) for item in response.data]
        all_items.extend(items)

        has_more = response.has_more
        total_count = response.total_count

        logger.info(
            f"Fetched page {page} of {item_type} "
            f"({len(items)} items, {len(all_items)} total"
            f"{f', {total_count} available' if total_count else ''})"
        )

        if has_more:
            page += 1
        else:
            break

    return all_items


async def main():
    """Main function to fetch and log all pricebook items."""
    logger.info("=" * 80)
    logger.info("Starting Service Titan Pricebook Items Fetch")
    logger.info("=" * 80)

    provider = ServiceTitanProvider()

    try:
        # Fetch all materials
        logger.info("\n" + "=" * 80)
        logger.info("FETCHING MATERIALS")
        logger.info("=" * 80)
        materials = await fetch_all_items(provider, "materials")
        logger.info(f"\n✓ Total materials fetched: {len(materials)}")

        # Log sample materials
        if materials:
            logger.info("\nSample materials (first 3):")
            for material in materials[:3]:
                logger.info(
                    f"  - {material['displayName']} (ID: {material['id']}, Code: {material['code']})"
                )
                logger.info(
                    f"    Price: ${material.get('price', 0)}, Cost: ${material.get('cost', 0)}"
                )

        # Fetch all services
        logger.info("\n" + "=" * 80)
        logger.info("FETCHING SERVICES")
        logger.info("=" * 80)
        services = await fetch_all_items(provider, "services")
        logger.info(f"\n✓ Total services fetched: {len(services)}")

        # Log sample services
        if services:
            logger.info("\nSample services (first 3):")
            for service in services[:3]:
                logger.info(
                    f"  - {service['displayName']} (ID: {service['id']}, Code: {service['code']})"
                )
                logger.info(f"    Price: ${service.get('price', 0)}")

        # Fetch all equipment
        logger.info("\n" + "=" * 80)
        logger.info("FETCHING EQUIPMENT")
        logger.info("=" * 80)
        equipment = await fetch_all_items(provider, "equipment")
        logger.info(f"\n✓ Total equipment fetched: {len(equipment)}")

        # Log sample equipment
        if equipment:
            logger.info("\nSample equipment (first 3):")
            for item in equipment[:3]:
                logger.info(
                    f"  - {item['displayName']} (ID: {item['id']}, Code: {item['code']})"
                )
                logger.info(
                    f"    Price: ${item.get('price', 0)}, Cost: ${item.get('cost', 0)}"
                )

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Materials: {len(materials)}")
        logger.info(f"Total Services: {len(services)}")
        logger.info(f"Total Equipment: {len(equipment)}")
        logger.info(f"Grand Total: {len(materials) + len(services) + len(equipment)}")

        # Save to file (optional)
        output_dir = Path("scripts/output")
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "pricebook_items.json"

        output_data = {
            "materials": materials,
            "services": services,
            "equipment": equipment,
            "summary": {
                "total_materials": len(materials),
                "total_services": len(services),
                "total_equipment": len(equipment),
                "grand_total": len(materials) + len(services) + len(equipment),
            },
        }

        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=2)

        logger.info(f"\n✓ Results saved to {output_file}")

    except Exception as e:
        logger.error(f"\n✗ Error fetching pricebook items: {e}", exc_info=True)
        raise
    finally:
        await provider.close()
        logger.info("\n" + "=" * 80)
        logger.info("Script completed")
        logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
