# Customer CRM Seeder

This script seeds your DynamoDB customers table with mock CRM data from all supported CRM systems.

## What Gets Seeded

- **28 total customers** across 4 CRM systems:
  - **ServiceTitan**: 7 customers (st_001 - st_007)
  - **JobNimbus**: 8 customers (jn_002, jn_008 - jn_014)
  - **AccuLynx**: 8 customers (al_003, al_015 - al_021)
  - **Monday.com**: 5 customers (md_004, md_022 - md_028)

## Setup

```bash
# Make scripts executable
chmod +x scripts/seed-customers/setup.sh
chmod +x scripts/seed-customers/seed_customers.py

# Run setup
./scripts/seed-customers/setup.sh
```

## Usage

```bash
# Activate the virtual environment
source scripts/seed-customers/venv/bin/activate

# Dry run first (see what would happen)
python scripts/seed-customers/seed_customers.py --stack-name david-dev --dry-run

# Actually seed the data
python scripts/seed-customers/seed_customers.py --stack-name david-dev
```

## Prerequisites

1. **Deploy your Pulumi stack first** to create the DynamoDB table:
   ```bash
   cd infra
   pulumi up
   ```

2. **Configure AWS credentials** for the target region (`us-gov-west-1`)

## Data Structure

Each customer record includes:
- Basic info: name, address, phone, email
- CRM source: servicetitan, jobnimbus, acculynx, monday
- Insurance claim data (if applicable): claim number, date of loss, insurance agency
- Contact details: adjuster info, agency contacts
- Notes: customer preferences and special requirements

## Example Output

```
🌱 Seeding customers table: maive-customers-table-david-dev
📍 Region: us-gov-west-1
🔍 Dry run: false

✅ Found table: maive-customers-table-david-dev
📝 Processing 28 customers...

  • John Smith (st_001) - servicetitan
  • Emily Davis (jn_002) - jobnimbus
  • Michael Thompson (al_003) - acculynx
  ...

✅ Successfully processed: 28
🎉 Seeding complete! 28 customers added to maive-customers-table-david-dev
```
