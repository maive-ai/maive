#!/usr/bin/env python3
"""
Interactive script to add a new customer to the CRM DynamoDB table.

Usage:
    python scripts/add-customer/add_customer.py --stack-name your-stack-name

Requirements:
    pip install boto3 python-dotenv
"""

import argparse
import re
import sys
from datetime import datetime
from typing import Dict, Optional

import boto3
from botocore.exceptions import ClientError

# Default values for quick testing
DEFAULT_PHONE_NUMBER = "+1-415-980-4313"
DEFAULT_EMAIL_DOMAIN = "@email.com"
DEFAULT_ADDRESS = "123 Main St, Austin, TX 78701"

# Default insurance contact information
DEFAULT_INSURANCE_CONTACT_NAME = "Angela Rodriguez"
DEFAULT_INSURANCE_CONTACT_PHONE = "+1-415-980-4313"
DEFAULT_INSURANCE_CONTACT_EMAIL = "angela.rodriguez@cinfin.com"

# Default adjuster information
DEFAULT_ADJUSTER_NAME = "Gregory Taylor"
DEFAULT_ADJUSTER_PHONE = "+1-707-653-0601"
DEFAULT_ADJUSTER_EMAIL = "gregory.taylor@cinfin.com"

# CRM source options
CRM_SOURCES = ["servicetitan", "jobnimbus", "acculynx", "monday"]
DEFAULT_CRM_SOURCE = "servicetitan"

# Common insurance agencies for quick selection
COMMON_INSURANCE_AGENCIES = [
    "State Farm Insurance",
    "Allstate Insurance", 
    "USAA Insurance",
    "Farmers Insurance",
    "Liberty Mutual",
    "Progressive Insurance",
    "Geico Insurance",
    "Nationwide Insurance",
    "Travelers Insurance",
    "Hartford Insurance",
    "Other (enter custom)"
]


def get_table_name(stack_name: str) -> str:
    """Get the DynamoDB table name for the given stack."""
    return f"maive-customers-table-{stack_name}"


def prompt_input(prompt: str, default: Optional[str] = None, required: bool = True) -> str:
    """Prompt for user input with optional default value."""
    if default:
        display_prompt = f"{prompt} [{default}]: "
    else:
        display_prompt = f"{prompt}: "
    
    while True:
        value = input(display_prompt).strip()
        
        if not value and default:
            return default
        elif not value and required:
            print("❌ This field is required. Please enter a value.")
            continue
        elif not value and not required:
            return ""
        else:
            return value


def prompt_choice(prompt: str, choices: list, default_index: int = 0) -> str:
    """Prompt user to select from a list of choices."""
    print(f"\n{prompt}")
    for i, choice in enumerate(choices):
        marker = "→" if i == default_index else " "
        print(f"{marker} {i + 1}. {choice}")
    
    while True:
        try:
            choice_input = input(f"\nSelect option (1-{len(choices)}) [{default_index + 1}]: ").strip()
            
            if not choice_input:
                return choices[default_index]
            
            choice_num = int(choice_input)
            if 1 <= choice_num <= len(choices):
                return choices[choice_num - 1]
            else:
                print(f"❌ Please enter a number between 1 and {len(choices)}")
        except ValueError:
            print("❌ Please enter a valid number")


def validate_phone(phone: str) -> str:
    """Validate and format phone number."""
    # Remove all non-digit characters
    digits = re.sub(r'[^\d]', '', phone)
    
    # Check if it's a valid US phone number
    if len(digits) == 10:
        # Format as +1-XXX-XXX-XXXX
        return f"+1-{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits.startswith('1'):
        # Format as +1-XXX-XXX-XXXX
        return f"+1-{digits[1:4]}-{digits[4:7]}-{digits[7:]}"
    else:
        return phone  # Return as-is if not a standard format


def validate_email(email: str) -> str:
    """Validate email format."""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(email_pattern, email):
        return email.lower()
    else:
        raise ValueError("Invalid email format")


def generate_customer_id(name: str, crm_source: str) -> str:
    """Generate a customer ID based on name and CRM source."""
    # Get CRM prefix
    crm_prefixes = {
        "servicetitan": "st",
        "jobnimbus": "jn", 
        "acculynx": "al",
        "monday": "md"
    }
    prefix = crm_prefixes.get(crm_source, "st")
    
    # Use timestamp for uniqueness
    timestamp = int(datetime.utcnow().timestamp())
    
    return f"{prefix}_{timestamp}"


def collect_customer_info() -> Dict:
    """Collect customer information interactively."""
    print("🏠 Customer Information")
    print("=" * 40)
    
    # Required fields
    homeowner_name = prompt_input("Customer Name", required=True)
    address = prompt_input("Address", DEFAULT_ADDRESS, required=True)
    
    # Generate default email from name
    default_email = homeowner_name.lower().replace(" ", ".") + DEFAULT_EMAIL_DOMAIN
    
    phone_number = prompt_input("Phone Number", DEFAULT_PHONE_NUMBER)
    phone_number = validate_phone(phone_number)
    
    while True:
        try:
            email = prompt_input("Email", default_email)
            email = validate_email(email)
            break
        except ValueError as e:
            print(f"❌ {e}")
    
    # CRM Source
    crm_source = prompt_choice("Select CRM Source:", CRM_SOURCES)
    
    # Generate customer ID
    customer_id = generate_customer_id(homeowner_name, crm_source)
    
    print("\n📋 Optional Information (press Enter to skip)")
    print("-" * 40)
    
    # Optional fields
    claim_number = prompt_input("Claim Number", required=False)
    date_of_loss = prompt_input("Date of Loss (YYYY-MM-DD)", required=False)
    
    # Insurance agency
    insurance_agency = ""
    insurance_contact_name = ""
    insurance_contact_phone = ""
    insurance_contact_email = ""
    
    if claim_number or date_of_loss:
        insurance_choice = prompt_choice("Select Insurance Agency:", COMMON_INSURANCE_AGENCIES)
        if insurance_choice == "Other (enter custom)":
            insurance_agency = prompt_input("Insurance Agency Name", required=False)
        else:
            insurance_agency = insurance_choice
        
        # Insurance Agency Contact Information
        if insurance_agency:
            print("\n📞 Insurance Agency Contact Information")
            print("-" * 40)
            insurance_contact_name = prompt_input("Insurance Contact Name", DEFAULT_INSURANCE_CONTACT_NAME, required=False)
            
            if insurance_contact_name:
                insurance_contact_phone = prompt_input("Insurance Contact Phone", DEFAULT_INSURANCE_CONTACT_PHONE, required=False)
                if insurance_contact_phone:
                    insurance_contact_phone = validate_phone(insurance_contact_phone)
                
                # Use default email for insurance contact
                while True:
                    try:
                        insurance_contact_email = prompt_input("Insurance Contact Email", DEFAULT_INSURANCE_CONTACT_EMAIL, required=False)
                        if insurance_contact_email:
                            insurance_contact_email = validate_email(insurance_contact_email)
                        break
                    except ValueError as e:
                        print(f"❌ {e}")
    
    # Adjuster Information
    print("\n🔍 Adjuster Information")
    print("-" * 40)
    adjuster_name = prompt_input("Adjuster Name", DEFAULT_ADJUSTER_NAME, required=False)
    adjuster_phone = ""
    adjuster_email = ""
    
    if adjuster_name:
        adjuster_phone = prompt_input("Adjuster Phone", DEFAULT_ADJUSTER_PHONE, required=False)
        if adjuster_phone:
            adjuster_phone = validate_phone(adjuster_phone)
        
        # Use default email for adjuster
        while True:
            try:
                adjuster_email = prompt_input("Adjuster Email", DEFAULT_ADJUSTER_EMAIL, required=False)
                if adjuster_email:
                    adjuster_email = validate_email(adjuster_email)
                break
            except ValueError as e:
                print(f"❌ {e}")
    
    notes = prompt_input("Notes", required=False)
    
    # Build customer data
    customer_data = {
        "id": customer_id,
        "homeownerName": homeowner_name,
        "address": address,
        "phoneNumber": phone_number,
        "email": email,
        "crmSource": crm_source,
    }
    
    # Add optional fields
    if claim_number:
        customer_data["claimNumber"] = claim_number
    if date_of_loss:
        customer_data["dateOfLoss"] = date_of_loss
    if insurance_agency:
        customer_data["insuranceAgency"] = insurance_agency
    if insurance_contact_name:
        customer_data["insuranceContactName"] = insurance_contact_name
    if insurance_contact_phone:
        customer_data["insuranceContactPhone"] = insurance_contact_phone
    if insurance_contact_email:
        customer_data["insuranceContactEmail"] = insurance_contact_email
    if adjuster_name:
        customer_data["adjusterName"] = adjuster_name
    if adjuster_phone:
        customer_data["adjusterPhone"] = adjuster_phone
    if adjuster_email:
        customer_data["adjusterEmail"] = adjuster_email
    if notes:
        customer_data["notes"] = notes
    
    return customer_data


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
    optional_fields = [
        ("email", "email"),
        ("claimNumber", "claim_number"),
        ("dateOfLoss", "date_of_loss"),
        ("insuranceAgency", "insurance_agency"),
        ("adjusterName", "adjuster_name"),
        ("notes", "notes"),
    ]
    
    for frontend_field, db_field in optional_fields:
        if frontend_field in customer:
            item[db_field] = customer[frontend_field]
    
    # Handle insurance agency contact as nested object
    if (customer.get("insuranceContactName") or 
        customer.get("insuranceContactPhone") or 
        customer.get("insuranceContactEmail")):
        insurance_contact = {}
        if customer.get("insuranceContactName"):
            insurance_contact["name"] = customer["insuranceContactName"]
        if customer.get("insuranceContactPhone"):
            insurance_contact["phone"] = customer["insuranceContactPhone"]
        if customer.get("insuranceContactEmail"):
            insurance_contact["email"] = customer["insuranceContactEmail"]
        
        if insurance_contact:
            item["insurance_agency_contact"] = insurance_contact
    
    # Handle adjuster contact as nested object
    if customer.get("adjusterPhone") or customer.get("adjusterEmail"):
        adjuster_contact = {}
        if customer.get("adjusterPhone"):
            adjuster_contact["phone"] = customer["adjusterPhone"]
        if customer.get("adjusterEmail"):
            adjuster_contact["email"] = customer["adjusterEmail"]
        
        if adjuster_contact:
            item["adjuster_contact"] = adjuster_contact
    
    return item


def preview_customer(customer_data: Dict) -> None:
    """Show a preview of the customer data."""
    print("\n📋 Customer Preview")
    print("=" * 40)
    print(f"ID: {customer_data['id']}")
    print(f"Name: {customer_data['homeownerName']}")
    print(f"Address: {customer_data['address']}")
    print(f"Phone: {customer_data['phoneNumber']}")
    print(f"Email: {customer_data['email']}")
    print(f"CRM Source: {customer_data['crmSource']}")
    
    if customer_data.get('claimNumber'):
        print(f"Claim Number: {customer_data['claimNumber']}")
    if customer_data.get('dateOfLoss'):
        print(f"Date of Loss: {customer_data['dateOfLoss']}")
    if customer_data.get('insuranceAgency'):
        print(f"Insurance Agency: {customer_data['insuranceAgency']}")
    
    # Insurance Contact Information
    if customer_data.get('insuranceContactName'):
        print("\n📞 Insurance Contact:")
        print(f"  Name: {customer_data['insuranceContactName']}")
        if customer_data.get('insuranceContactPhone'):
            print(f"  Phone: {customer_data['insuranceContactPhone']}")
        if customer_data.get('insuranceContactEmail'):
            print(f"  Email: {customer_data['insuranceContactEmail']}")
    
    # Adjuster Information
    if customer_data.get('adjusterName'):
        print("\n🔍 Adjuster:")
        print(f"  Name: {customer_data['adjusterName']}")
        if customer_data.get('adjusterPhone'):
            print(f"  Phone: {customer_data['adjusterPhone']}")
        if customer_data.get('adjusterEmail'):
            print(f"  Email: {customer_data['adjusterEmail']}")
    
    if customer_data.get('notes'):
        print(f"\nNotes: {customer_data['notes']}")


def add_customer_to_database(customer_data: Dict, stack_name: str, region: str = "us-gov-west-1", dry_run: bool = False) -> bool:
    """Add the customer to DynamoDB."""
    table_name = get_table_name(stack_name)
    
    print("\n🚀 Adding Customer to Database")
    print("=" * 40)
    print(f"Table: {table_name}")
    print(f"Region: {region}")
    
    if dry_run:
        print("🔍 DRY RUN - No data will be written")
        return True
    
    try:
        # Initialize DynamoDB client
        dynamodb = boto3.resource("dynamodb", region_name=region)
        table = dynamodb.Table(table_name)
        
        # Check if table exists
        table.load()
        
        # Transform data for DynamoDB
        item = transform_customer_for_dynamodb(customer_data)
        
        # Check if customer already exists
        try:
            existing = table.get_item(Key={"customer_id": customer_data["id"]})
            if "Item" in existing:
                print(f"⚠️  Customer with ID {customer_data['id']} already exists!")
                overwrite = input("Do you want to overwrite? (y/N): ").strip().lower()
                if overwrite != 'y':
                    print("❌ Operation cancelled")
                    return False
        except ClientError:
            pass  # Customer doesn't exist, which is fine
        
        # Add customer to database
        table.put_item(Item=item)
        
        print("✅ Customer added successfully!")
        print(f"🆔 Customer ID: {customer_data['id']}")
        
        return True
        
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"❌ Table not found: {table_name}")
            print("Make sure you've deployed your Pulumi stack first!")
        else:
            print(f"❌ AWS Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Interactively add a new customer to the CRM database")
    parser.add_argument("--stack-name", required=True, help="Pulumi stack name (e.g., david-dev)")
    parser.add_argument("--region", default="us-gov-west-1", help="AWS region")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be done without making changes")
    
    args = parser.parse_args()
    
    print("🏠 Interactive Customer Creator")
    print("=" * 40)
    print("This script will guide you through adding a new customer to your CRM database.")
    print("Press Ctrl+C at any time to cancel.\n")
    
    try:
        # Collect customer information
        customer_data = collect_customer_info()
        
        # Show preview
        preview_customer(customer_data)
        
        # Confirm before adding
        print("\n" + "=" * 40)
        confirm = input("Add this customer to the database? (Y/n): ").strip().lower()
        
        if confirm in ['', 'y', 'yes']:
            success = add_customer_to_database(customer_data, args.stack_name, args.region, args.dry_run)
            if success:
                print("\n🎉 Customer successfully added to your CRM!")
                print(f"You can now search for '{customer_data['homeownerName']}' in your frontend.")
            else:
                print("\n💥 Failed to add customer")
                sys.exit(1)
        else:
            print("\n❌ Operation cancelled")
            
    except KeyboardInterrupt:
        print("\n\n👋 Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
