#!/usr/bin/env python3
"""
Script to seed the customers DynamoDB table with mock CRM data.

Usage:
    python scripts/seed-customers/seed_customers.py --stack-name your-stack-name

Requirements:
    pip install boto3 python-dotenv
"""

import argparse
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

# Mock customer data (converted from TypeScript)
DEFAULT_PHONE_NUMBER = "+1-703-268-1917"

MOCK_CUSTOMERS = [
    {
        "id": "st_001",
        "homeownerName": "John Smith",
        "address": "123 Main St, Austin, TX 78701",
        "claimNumber": "CLM-2024-001",
        "dateOfLoss": "2024-08-15",
        "insuranceAgency": "State Farm Insurance",
        "insuranceAgencyContact": {
            "name": "Sarah Johnson",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "sarah.johnson@statefarm.com",
        },
        "adjusterName": "Mike Williams",
        "adjusterContact": {
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "mike.williams@statefarm.com",
        },
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "john.smith@email.com",
        "crmSource": "servicetitan",
        "notes": "Roof damage from hail storm. Customer prefers morning appointments.",
    },
    {
        "id": "jn_002",
        "homeownerName": "Emily Davis",
        "address": "456 Oak Avenue, Dallas, TX 75201",
        "claimNumber": "CLM-2024-002",
        "dateOfLoss": "2024-09-01",
        "insuranceAgency": "Allstate Insurance",
        "insuranceAgencyContact": {
            "name": "Robert Chen",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "robert.chen@allstate.com",
        },
        "adjusterName": "Lisa Rodriguez",
        "adjusterContact": {
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "lisa.rodriguez@allstate.com",
        },
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "emily.davis@email.com",
        "crmSource": "jobnimbus",
        "notes": "Wind damage to gutters and siding. Emergency tarp installed.",
    },
    {
        "id": "al_003",
        "homeownerName": "Michael Thompson",
        "address": "789 Pine Street, Houston, TX 77001",
        "claimNumber": "CLM-2024-003",
        "dateOfLoss": "2024-08-28",
        "insuranceAgency": "USAA Insurance",
        "insuranceAgencyContact": {
            "name": "Jennifer Martinez",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "jennifer.martinez@usaa.com",
        },
        "adjusterName": "David Brown",
        "adjusterContact": {
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "david.brown@usaa.com",
        },
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "michael.thompson@email.com",
        "crmSource": "acculynx",
        "notes": "Multiple shingle damage areas. Customer has military discount.",
    },
    {
        "id": "md_004",
        "homeownerName": "Sarah Wilson",
        "address": "321 Elm Drive, San Antonio, TX 78201",
        "claimNumber": "CLM-2024-004",
        "dateOfLoss": "2024-09-10",
        "insuranceAgency": "Farmers Insurance",
        "insuranceAgencyContact": {
            "name": "Kevin Lee",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "kevin.lee@farmersinsurance.com",
        },
        "adjusterName": "Amanda Garcia",
        "adjusterContact": {
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "amanda.garcia@farmersinsurance.com",
        },
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "sarah.wilson@email.com",
        "crmSource": "monday",
        "notes": "Storm damage claim pending. Customer needs quick turnaround.",
    },
    {
        "id": "st_005",
        "homeownerName": "Robert Johnson",
        "address": "654 Cedar Lane, Fort Worth, TX 76101",
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "robert.johnson@email.com",
        "crmSource": "servicetitan",
        "notes": "Maintenance customer. No insurance claim.",
    },
    {
        "id": "st_006",
        "homeownerName": "Jennifer Martinez",
        "address": "987 Maple Avenue, Plano, TX 75023",
        "claimNumber": "CLM-2024-005",
        "dateOfLoss": "2024-09-05",
        "insuranceAgency": "Liberty Mutual",
        "insuranceAgencyContact": {
            "name": "Carlos Rivera",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "carlos.rivera@libertymutual.com",
        },
        "adjusterName": "Patricia Lee",
        "adjusterContact": {
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "patricia.lee@libertymutual.com",
        },
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "jennifer.martinez@email.com",
        "crmSource": "servicetitan",
        "notes": "Hail damage to roof and gutters. Urgent repair needed.",
    },
    {
        "id": "st_007",
        "homeownerName": "David Chen",
        "address": "456 Willow Street, Richardson, TX 75080",
        "claimNumber": "CLM-2024-006",
        "dateOfLoss": "2024-08-20",
        "insuranceAgency": "Progressive Insurance",
        "insuranceAgencyContact": {
            "name": "Michelle Wong",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "michelle.wong@progressive.com",
        },
        "adjusterName": "Brian Taylor",
        "adjusterContact": {
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "brian.taylor@progressive.com",
        },
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "david.chen@email.com",
        "crmSource": "servicetitan",
        "notes": "Wind damage from storm. Customer has high deductible.",
    },
    # JobNimbus customers
    {
        "id": "jn_008",
        "homeownerName": "Lisa Anderson",
        "address": "321 Sunset Drive, Garland, TX 75040",
        "claimNumber": "CLM-2024-007",
        "dateOfLoss": "2024-09-12",
        "insuranceAgency": "Geico Insurance",
        "insuranceAgencyContact": {
            "name": "Thomas Kim",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "thomas.kim@geico.com",
        },
        "adjusterName": "Rachel Green",
        "adjusterContact": {
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "rachel.green@geico.com",
        },
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "lisa.anderson@email.com",
        "crmSource": "jobnimbus",
        "notes": "Multiple shingle replacement needed. Customer prefers afternoon appointments.",
    },
    {
        "id": "jn_009",
        "homeownerName": "Mark Wilson",
        "address": "789 Oak Hill Lane, Irving, TX 75061",
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "mark.wilson@email.com",
        "crmSource": "jobnimbus",
        "notes": "Routine maintenance check. Long-term customer.",
    },
    {
        "id": "jn_010",
        "homeownerName": "Amanda Foster",
        "address": "654 Pine Ridge Court, Mesquite, TX 75149",
        "claimNumber": "CLM-2024-008",
        "dateOfLoss": "2024-08-30",
        "insuranceAgency": "Nationwide Insurance",
        "insuranceAgencyContact": {
            "name": "Steven Park",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "steven.park@nationwide.com",
        },
        "adjusterName": "Nicole Brown",
        "adjusterContact": {
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "nicole.brown@nationwide.com",
        },
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "amanda.foster@email.com",
        "crmSource": "jobnimbus",
        "notes": "Storm damage claim. Customer needs quick resolution.",
    },
    {
        "id": "jn_011",
        "homeownerName": "Christopher Davis",
        "address": "123 Cedar Creek Drive, Grand Prairie, TX 75050",
        "claimNumber": "CLM-2024-009",
        "dateOfLoss": "2024-09-08",
        "insuranceAgency": "Travelers Insurance",
        "insuranceAgencyContact": {
            "name": "Jessica Liu",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "jessica.liu@travelers.com",
        },
        "adjusterName": "Kevin Murphy",
        "adjusterContact": {
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "kevin.murphy@travelers.com",
        },
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "christopher.davis@email.com",
        "crmSource": "jobnimbus",
        "notes": "Hail damage assessment needed. Customer works from home.",
    },
    {
        "id": "jn_012",
        "homeownerName": "Rebecca Martinez",
        "address": "987 Elm Street, Carrollton, TX 75006",
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "rebecca.martinez@email.com",
        "crmSource": "jobnimbus",
        "notes": "Preventive maintenance customer. Annual inspection due.",
    },
    {
        "id": "jn_013",
        "homeownerName": "Daniel Rodriguez",
        "address": "456 Birch Lane, Lewisville, TX 75057",
        "claimNumber": "CLM-2024-010",
        "dateOfLoss": "2024-09-15",
        "insuranceAgency": "Hartford Insurance",
        "insuranceAgencyContact": {
            "name": "Maria Gonzalez",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "maria.gonzalez@thehartford.com",
        },
        "adjusterName": "James Wilson",
        "adjusterContact": {
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "james.wilson@thehartford.com",
        },
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "daniel.rodriguez@email.com",
        "crmSource": "jobnimbus",
        "notes": "Wind and hail damage. Emergency tarp installed.",
    },
    {
        "id": "jn_014",
        "homeownerName": "Stephanie White",
        "address": "321 Valley View Road, Flower Mound, TX 75022",
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "stephanie.white@email.com",
        "crmSource": "jobnimbus",
        "notes": "New customer referral. Interested in full roof replacement.",
    },
    # AccuLynx customers
    {
        "id": "al_015",
        "homeownerName": "Thomas Brown",
        "address": "789 Highland Park Drive, Arlington, TX 76010",
        "claimNumber": "CLM-2024-011",
        "dateOfLoss": "2024-09-03",
        "insuranceAgency": "Amica Insurance",
        "insuranceAgencyContact": {
            "name": "Linda Johnson",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "linda.johnson@amica.com",
        },
        "adjusterName": "Robert Clark",
        "adjusterContact": {
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "robert.clark@amica.com",
        },
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "thomas.brown@email.com",
        "crmSource": "acculynx",
        "notes": "Large commercial claim. Multiple building assessment needed.",
    },
    {
        "id": "al_016",
        "homeownerName": "Patricia Garcia",
        "address": "654 Mountain View Circle, Euless, TX 76039",
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "patricia.garcia@email.com",
        "crmSource": "acculynx",
        "notes": "Maintenance customer. Gutter cleaning and inspection.",
    },
    {
        "id": "al_017",
        "homeownerName": "William Lee",
        "address": "123 Riverside Drive, Bedford, TX 76021",
        "claimNumber": "CLM-2024-012",
        "dateOfLoss": "2024-08-25",
        "insuranceAgency": "MetLife Insurance",
        "insuranceAgencyContact": {
            "name": "Sandra Kim",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "sandra.kim@metlife.com",
        },
        "adjusterName": "Michael Davis",
        "adjusterContact": {
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "michael.davis@metlife.com",
        },
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "william.lee@email.com",
        "crmSource": "acculynx",
        "notes": "Storm damage to shingles and flashing. Veteran discount applied.",
    },
    {
        "id": "al_018",
        "homeownerName": "Michelle Taylor",
        "address": "987 Forest Glen Way, Hurst, TX 76053",
        "claimNumber": "CLM-2024-013",
        "dateOfLoss": "2024-09-10",
        "insuranceAgency": "Chubb Insurance",
        "insuranceAgencyContact": {
            "name": "David Chen",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "david.chen@chubb.com",
        },
        "adjusterName": "Jennifer Lopez",
        "adjusterContact": {
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "jennifer.lopez@chubb.com",
        },
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "michelle.taylor@email.com",
        "crmSource": "acculynx",
        "notes": "High-value home. Premium materials required.",
    },
    {
        "id": "al_019",
        "homeownerName": "Joseph Martinez",
        "address": "456 Creekside Lane, Colleyville, TX 76034",
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "joseph.martinez@email.com",
        "crmSource": "acculynx",
        "notes": "Regular maintenance customer. Quarterly inspections.",
    },
    {
        "id": "al_020",
        "homeownerName": "Karen Anderson",
        "address": "321 Oakwood Drive, Grapevine, TX 76051",
        "claimNumber": "CLM-2024-014",
        "dateOfLoss": "2024-09-07",
        "insuranceAgency": "American Family Insurance",
        "insuranceAgencyContact": {
            "name": "Robert Wang",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "robert.wang@amfam.com",
        },
        "adjusterName": "Lisa Thompson",
        "adjusterContact": {
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "lisa.thompson@amfam.com",
        },
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "karen.anderson@email.com",
        "crmSource": "acculynx",
        "notes": "Wind damage from recent storm. Customer needs quick estimate.",
    },
    {
        "id": "al_021",
        "homeownerName": "Steven Wilson",
        "address": "789 Meadowbrook Lane, Southlake, TX 76092",
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "steven.wilson@email.com",
        "crmSource": "acculynx",
        "notes": "New construction inspection. High-end residential project.",
    },
    # Monday.com customers
    {
        "id": "md_022",
        "homeownerName": "Nancy Rodriguez",
        "address": "654 Sunset Boulevard, Mansfield, TX 76063",
        "claimNumber": "CLM-2024-015",
        "dateOfLoss": "2024-09-02",
        "insuranceAgency": "Safeco Insurance",
        "insuranceAgencyContact": {
            "name": "Mark Johnson",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "mark.johnson@safeco.com",
        },
        "adjusterName": "Carol Smith",
        "adjusterContact": {
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "carol.smith@safeco.com",
        },
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "nancy.rodriguez@email.com",
        "crmSource": "monday",
        "notes": "Hail damage assessment. Customer has elderly parents living with them.",
    },
    {
        "id": "md_023",
        "homeownerName": "Richard Davis",
        "address": "123 Prairie View Drive, Cedar Hill, TX 75104",
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "richard.davis@email.com",
        "crmSource": "monday",
        "notes": "Routine maintenance customer. Annual roof cleaning.",
    },
    {
        "id": "md_024",
        "homeownerName": "Helen Garcia",
        "address": "987 Hillside Avenue, DeSoto, TX 75115",
        "claimNumber": "CLM-2024-016",
        "dateOfLoss": "2024-08-28",
        "insuranceAgency": "Auto-Owners Insurance",
        "insuranceAgencyContact": {
            "name": "Paul Martinez",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "paul.martinez@auto-owners.com",
        },
        "adjusterName": "Susan Brown",
        "adjusterContact": {
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "susan.brown@auto-owners.com",
        },
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "helen.garcia@email.com",
        "crmSource": "monday",
        "notes": "Storm damage to multiple areas. Complex claim requiring detailed assessment.",
    },
    {
        "id": "md_025",
        "homeownerName": "Paul Thompson",
        "address": "456 Garden Valley Road, Lancaster, TX 75146",
        "claimNumber": "CLM-2024-017",
        "dateOfLoss": "2024-09-11",
        "insuranceAgency": "Mutual of Omaha",
        "insuranceAgencyContact": {
            "name": "Emily Davis",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "emily.davis@mutualofomaha.com",
        },
        "adjusterName": "Anthony Wilson",
        "adjusterContact": {
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "anthony.wilson@mutualofomaha.com",
        },
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "paul.thompson@email.com",
        "crmSource": "monday",
        "notes": "Wind and hail damage. Customer works night shift, prefers daytime appointments.",
    },
    {
        "id": "md_026",
        "homeownerName": "Dorothy Lee",
        "address": "321 Brookside Drive, Duncanville, TX 75116",
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "dorothy.lee@email.com",
        "crmSource": "monday",
        "notes": "Senior citizen customer. Preventive maintenance and inspection.",
    },
    {
        "id": "md_027",
        "homeownerName": "Kenneth Martinez",
        "address": "789 Woodland Trail, Glenn Heights, TX 75154",
        "claimNumber": "CLM-2024-018",
        "dateOfLoss": "2024-09-04",
        "insuranceAgency": "Cincinnati Insurance",
        "insuranceAgencyContact": {
            "name": "Angela Rodriguez",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "angela.rodriguez@cinfin.com",
        },
        "adjusterName": "Gregory Taylor",
        "adjusterContact": {
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "gregory.taylor@cinfin.com",
        },
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "kenneth.martinez@email.com",
        "crmSource": "monday",
        "notes": "Large residential property. Multiple damage areas from recent storm.",
    },
    {
        "id": "md_028",
        "homeownerName": "Betty Anderson",
        "address": "654 Maple Ridge Circle, Red Oak, TX 75154",
        "phoneNumber": DEFAULT_PHONE_NUMBER,
        "email": "betty.anderson@email.com",
        "crmSource": "monday",
        "notes": "Long-term customer. Quarterly gutter maintenance and roof inspection.",
    },
]


def get_table_name(stack_name: str) -> str:
    """Get the DynamoDB table name for the given stack."""
    return f"maive-customers-table-{stack_name}"


def transform_customer_for_dynamodb(customer: Dict) -> Dict:
    """Transform customer data for DynamoDB storage."""
    now = datetime.utcnow().isoformat()
    
    # Create the DynamoDB item
    item = {
        "customer_id": customer["id"],
        "homeowner_name": customer["homeownerName"],
        "homeowner_name_lower": customer["homeownerName"].lower(),
        "address": customer["address"],
        "phone_number": customer["phoneNumber"],
        "crm_source": customer["crmSource"],
        "created_at": now,
        "updated_at": now,
    }
    
    # Add optional fields if they exist
    if "email" in customer:
        item["email"] = customer["email"]
    
    if "claimNumber" in customer:
        item["claim_number"] = customer["claimNumber"]
    
    if "dateOfLoss" in customer:
        item["date_of_loss"] = customer["dateOfLoss"]
    
    if "insuranceAgency" in customer:
        item["insurance_agency"] = customer["insuranceAgency"]
    
    if "insuranceAgencyContact" in customer:
        item["insurance_agency_contact"] = customer["insuranceAgencyContact"]
    
    if "adjusterName" in customer:
        item["adjuster_name"] = customer["adjusterName"]
    
    if "adjusterContact" in customer:
        item["adjuster_contact"] = customer["adjusterContact"]
    
    if "notes" in customer:
        item["notes"] = customer["notes"]
    
    return item


def seed_customers_table(stack_name: str, region: str = "us-gov-west-1", dry_run: bool = False) -> None:
    """Seed the customers table with mock data."""
    table_name = get_table_name(stack_name)
    
    print(f"🌱 Seeding customers table: {table_name}")
    print(f"📍 Region: {region}")
    print(f"🔍 Dry run: {dry_run}")
    print()
    
    if dry_run:
        print("DRY RUN - No data will be written to DynamoDB")
        print()
    
    # Initialize DynamoDB client
    try:
        dynamodb = boto3.resource("dynamodb", region_name=region)
        table = dynamodb.Table(table_name)
        
        # Check if table exists
        table.load()
        print(f"✅ Found table: {table_name}")
        
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"❌ Table not found: {table_name}")
            print("Make sure you've deployed your Pulumi stack first!")
            return
        else:
            raise
    
    # Transform and batch write customers
    success_count = 0
    error_count = 0
    
    print(f"📝 Processing {len(MOCK_CUSTOMERS)} customers...")
    print()
    
    for customer in MOCK_CUSTOMERS:
        try:
            item = transform_customer_for_dynamodb(customer)
            
            print(f"  • {item['homeowner_name']} ({item['customer_id']}) - {item['crm_source']}")
            
            if not dry_run:
                table.put_item(Item=item)
            
            success_count += 1
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            error_count += 1
    
    print()
    print(f"✅ Successfully processed: {success_count}")
    if error_count > 0:
        print(f"❌ Errors: {error_count}")
    
    if not dry_run:
        print(f"🎉 Seeding complete! {success_count} customers added to {table_name}")
    else:
        print("🔍 Dry run complete - no data was written")


def main():
    parser = argparse.ArgumentParser(description="Seed customers DynamoDB table with mock data")
    parser.add_argument("--stack-name", required=True, help="Pulumi stack name (e.g., david-dev)")
    parser.add_argument("--region", default="us-gov-west-1", help="AWS region")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    
    args = parser.parse_args()
    
    print("🚀 Customer CRM Table Seeder")
    print("=" * 40)
    
    try:
        seed_customers_table(args.stack_name, args.region, args.dry_run)
    except Exception as e:
        print(f"💥 Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
