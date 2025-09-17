# Interactive Customer Creator

An interactive command-line tool to add new customers to your CRM DynamoDB table.

## Features

- 🎯 **Interactive prompts** with smart defaults
- 📱 **Phone number validation** and formatting
- 📧 **Email validation** and auto-generation
- 🏢 **Quick insurance agency selection**
- 🆔 **Automatic customer ID generation**
- 👀 **Preview before saving**
- 🔍 **Dry run mode** for testing
- ⚡ **Fast workflow** for quick customer entry

## Quick Start

```bash
# Install dependencies
pip install -r scripts/add-customer/requirements.txt

# Add a customer (interactive)
python scripts/add-customer/add_customer.py --stack-name david-dev

# Preview without saving
python scripts/add-customer/add_customer.py --stack-name david-dev --dry-run
```

## Usage Examples

### Basic Customer (Required Fields Only)
```
Customer Name: John Smith
Address: 123 Main St, Austin, TX 78701
Phone Number [+1-703-268-1917]: 
Email [john.smith@email.com]: 
Select CRM Source: 1 (ServiceTitan)
```

### Full Customer with Insurance Claim
```
Customer Name: Jane Doe
Address: 456 Oak Ave, Dallas, TX 75201
Phone Number [+1-703-268-1917]: 214-555-0123
Email [jane.doe@email.com]: jane@example.com
Select CRM Source: 1 (ServiceTitan)
Claim Number: CLM-2024-001
Date of Loss (YYYY-MM-DD): 2024-09-15
Select Insurance Agency: 1 (State Farm Insurance)
Notes: Roof damage from recent hail storm
```

## Smart Features

### Automatic ID Generation
- **ServiceTitan**: `st_1726234567`
- **JobNimbus**: `jn_1726234567` 
- **AccuLynx**: `al_1726234567`
- **Monday.com**: `md_1726234567`

### Phone Number Formatting
- Input: `2145550123` → Output: `+1-214-555-0123`
- Input: `(214) 555-0123` → Output: `+1-214-555-0123`
- Input: `214.555.0123` → Output: `+1-214-555-0123`

### Email Auto-Generation
- Input: `John Smith` → Suggests: `john.smith@email.com`
- Input: `Mary Jane Watson` → Suggests: `mary.jane.watson@email.com`

### Quick Insurance Selection
Common agencies available for quick selection:
- State Farm Insurance
- Allstate Insurance  
- USAA Insurance
- Farmers Insurance
- Liberty Mutual
- Progressive Insurance
- And more...

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--stack-name` | Pulumi stack name (required) | - |
| `--region` | AWS region | `us-gov-west-1` |
| `--dry-run` | Preview without saving | `false` |

## Workflow

1. **Required Info**: Name, address, phone, email, CRM source
2. **Optional Info**: Claim details, insurance info, notes
3. **Preview**: Review all entered data
4. **Confirm**: Save to database or cancel
5. **Success**: Customer immediately available in frontend

## Integration

The script uses the same DynamoDB table and data format as your existing customer CRM system:
- ✅ Compatible with existing frontend search
- ✅ Works with voice AI call system
- ✅ Supports all CRM sources (ServiceTitan, JobNimbus, etc.)
- ✅ Includes all optional fields (insurance, claims, etc.)
