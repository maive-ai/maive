"""
Mock CRM project data for demos and local development.

This file contains hardcoded project data that can be easily removed
when switching to real CRM integrations.
"""

from datetime import UTC, datetime

from src.integrations.crm.constants import CRMProvider, Status
from src.integrations.crm.schemas import Project

# Default phone number for all mock data
DEFAULT_PHONE_NUMBER = "+1-703-268-1917"


# Project statuses
PROJECT_STATUSES = [status.value for status in Status]


# Mock customer/project data as dictionaries
MOCK_PROJECTS_RAW = [
    {
        "id": "st_001",
        "customerName": "John Smith",
        "address": "123 Main St, Austin, TX 78701",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "john.smith@gmail.com",
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
            "name": "Mike Williams",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "mike.williams@statefarm.com",
        },
        "notes": "Roof damage from hail storm. Customer prefers morning appointments.",
    },
    {
        "id": "jn_002",
        "customerName": "Emily Davis",
        "address": "456 Oak Avenue, Dallas, TX 75201",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "emily.davis@gmail.com",
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
            "name": "Lisa Rodriguez",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "lisa.rodriguez@allstate.com",
        },
        "notes": "Wind damage to gutters and siding. Emergency tarp installed.",
    },
    {
        "id": "al_003",
        "customerName": "Michael Thompson",
        "address": "789 Pine Street, Houston, TX 77001",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "michael.thompson@gmail.com",
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
            "name": "David Brown",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "david.brown@usaa.com",
        },
        "notes": "Multiple shingle damage areas. Customer has military discount.",
    },
    {
        "id": "md_004",
        "customerName": "Sarah Wilson",
        "address": "321 Elm Drive, San Antonio, TX 78201",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "sarah.wilson@gmail.com",
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
            "name": "Amanda Garcia",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "amanda.garcia@farmersinsurance.com",
        },
        "notes": "Storm damage claim pending. Customer needs quick turnaround.",
    },
    {
        "id": "st_005",
        "customerName": "Robert Johnson",
        "address": "654 Cedar Lane, Fort Worth, TX 76101",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "robert.johnson@gmail.com",
        "notes": "Maintenance customer. No insurance claim.",
    },
    {
        "id": "st_006",
        "customerName": "Jennifer Martinez",
        "address": "987 Maple Avenue, Plano, TX 75023",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "jennifer.martinez@gmail.com",
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
            "name": "Patricia Lee",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "patricia.lee@libertymutual.com",
        },
        "notes": "Hail damage to roof and gutters. Urgent repair needed.",
    },
    {
        "id": "st_007",
        "customerName": "David Chen",
        "address": "456 Willow Street, Richardson, TX 75080",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "david.chen@gmail.com",
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
            "name": "Brian Taylor",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "brian.taylor@progressive.com",
        },
        "notes": "Wind damage from storm. Customer has high deductible.",
    },
    {
        "id": "jn_008",
        "customerName": "Lisa Anderson",
        "address": "321 Sunset Drive, Garland, TX 75040",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "lisa.anderson@gmail.com",
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
            "name": "Rachel Green",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "rachel.green@geico.com",
        },
        "notes": "Multiple shingle replacement needed. Customer prefers afternoon appointments.",
    },
    {
        "id": "jn_009",
        "customerName": "Mark Wilson",
        "address": "789 Oak Hill Lane, Irving, TX 75061",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "mark.wilson@gmail.com",
        "notes": "Routine maintenance check. Long-term customer.",
    },
    {
        "id": "jn_010",
        "customerName": "Amanda Foster",
        "address": "654 Pine Ridge Court, Mesquite, TX 75149",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "amanda.foster@gmail.com",
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
            "name": "Nicole Brown",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "nicole.brown@nationwide.com",
        },
        "notes": "Storm damage claim. Customer needs quick resolution.",
    },
    {
        "id": "jn_011",
        "customerName": "Christopher Davis",
        "address": "123 Cedar Creek Drive, Grand Prairie, TX 75050",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "christopher.davis@gmail.com",
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
            "name": "Kevin Murphy",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "kevin.murphy@travelers.com",
        },
        "notes": "Hail damage assessment needed. Customer works from home.",
    },
    {
        "id": "jn_012",
        "customerName": "Rebecca Martinez",
        "address": "987 Elm Street, Carrollton, TX 75006",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "rebecca.martinez@gmail.com",
        "notes": "Preventive maintenance customer. Annual inspection due.",
    },
    {
        "id": "jn_013",
        "customerName": "Daniel Rodriguez",
        "address": "456 Birch Lane, Lewisville, TX 75057",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "daniel.rodriguez@gmail.com",
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
            "name": "James Wilson",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "james.wilson@thehartford.com",
        },
        "notes": "Wind and hail damage. Emergency tarp installed.",
    },
    {
        "id": "jn_014",
        "customerName": "Stephanie White",
        "address": "321 Valley View Road, Flower Mound, TX 75022",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "stephanie.white@gmail.com",
        "notes": "New customer referral. Interested in full roof replacement.",
    },
    {
        "id": "al_015",
        "customerName": "Thomas Brown",
        "address": "789 Highland Park Drive, Arlington, TX 76010",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "thomas.brown@gmail.com",
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
            "name": "Robert Clark",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "robert.clark@amica.com",
        },
        "notes": "Large commercial claim. Multiple building assessment needed.",
    },
    {
        "id": "al_016",
        "customerName": "Patricia Garcia",
        "address": "654 Mountain View Circle, Euless, TX 76039",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "patricia.garcia@gmail.com",
        "notes": "Maintenance customer. Gutter cleaning and inspection.",
    },
    {
        "id": "al_017",
        "customerName": "William Lee",
        "address": "123 Riverside Drive, Bedford, TX 76021",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "william.lee@gmail.com",
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
            "name": "Michael Davis",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "michael.davis@metlife.com",
        },
        "notes": "Storm damage to shingles and flashing. Veteran discount applied.",
    },
    {
        "id": "al_018",
        "customerName": "Michelle Taylor",
        "address": "987 Forest Glen Way, Hurst, TX 76053",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "michelle.taylor@gmail.com",
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
            "name": "Jennifer Lopez",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "jennifer.lopez@chubb.com",
        },
        "notes": "High-value home. Premium materials required.",
    },
    {
        "id": "al_019",
        "customerName": "Joseph Martinez",
        "address": "456 Creekside Lane, Colleyville, TX 76034",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "joseph.martinez@gmail.com",
        "notes": "Regular maintenance customer. Quarterly inspections.",
    },
    {
        "id": "al_020",
        "customerName": "Karen Anderson",
        "address": "321 Oakwood Drive, Grapevine, TX 76051",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "karen.anderson@gmail.com",
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
            "name": "Lisa Thompson",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "lisa.thompson@amfam.com",
        },
        "notes": "Wind damage from recent storm. Customer needs quick estimate.",
    },
    {
        "id": "al_021",
        "customerName": "Steven Wilson",
        "address": "789 Meadowbrook Lane, Southlake, TX 76092",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "steven.wilson@gmail.com",
        "notes": "New construction inspection. High-end residential project.",
    },
    {
        "id": "md_022",
        "customerName": "Nancy Rodriguez",
        "address": "654 Sunset Boulevard, Mansfield, TX 76063",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "nancy.rodriguez@gmail.com",
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
            "name": "Carol Smith",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "carol.smith@safeco.com",
        },
        "notes": "Hail damage assessment. Customer has elderly parents living with them.",
    },
    {
        "id": "md_023",
        "customerName": "Richard Davis",
        "address": "123 Prairie View Drive, Cedar Hill, TX 75104",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "richard.davis@gmail.com",
        "notes": "Routine maintenance customer. Annual roof cleaning.",
    },
    {
        "id": "md_024",
        "customerName": "Helen Garcia",
        "address": "987 Hillside Avenue, DeSoto, TX 75115",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "helen.garcia@gmail.com",
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
            "name": "Susan Brown",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "susan.brown@auto-owners.com",
        },
        "notes": "Storm damage to multiple areas. Complex claim requiring detailed assessment.",
    },
    {
        "id": "md_025",
        "customerName": "Paul Thompson",
        "address": "456 Garden Valley Road, Lancaster, TX 75146",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "paul.thompson@gmail.com",
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
            "name": "Anthony Wilson",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "anthony.wilson@mutualofomaha.com",
        },
        "notes": "Wind and hail damage. Customer works night shift, prefers daytime appointments.",
    },
    {
        "id": "md_026",
        "customerName": "Dorothy Lee",
        "address": "321 Brookside Drive, Duncanville, TX 75116",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "dorothy.lee@gmail.com",
        "notes": "Senior citizen customer. Preventive maintenance and inspection.",
    },
    {
        "id": "md_027",
        "customerName": "Kenneth Martinez",
        "address": "789 Woodland Trail, Glenn Heights, TX 75154",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "kenneth.martinez@gmail.com",
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
            "name": "Gregory Taylor",
            "phone": DEFAULT_PHONE_NUMBER,
            "email": "gregory.taylor@cinfin.com",
        },
        "notes": "Large residential property. Multiple damage areas from recent storm.",
    },
    {
        "id": "md_028",
        "customerName": "Betty Anderson",
        "address": "654 Maple Ridge Circle, Red Oak, TX 75154",
        "phone": DEFAULT_PHONE_NUMBER,
        "email": "betty.anderson@gmail.com",
        "notes": "Long-term customer. Quarterly gutter maintenance and roof inspection.",
    },
]


def _derive_numeric_job_id(project_id: str) -> int:
    """Derive a numeric-like job_id from a project_id string for demo purposes.

    Prefer digits in the id; fallback to a stable hash-based integer.
    """
    digits = "".join(ch for ch in project_id if ch.isdigit())
    if digits:
        try:
            return int(digits)
        except ValueError:
            pass
    # Stable positive int from hash
    return abs(hash(project_id)) % 1_000_000


def get_mock_projects() -> list[Project]:
    """
    Get mock projects with assigned statuses.

    Returns a list of universal Project models.
    """
    now = datetime.now(UTC).isoformat()

    # Manually assigned statuses based on notes content
    project_statuses = [
        Status.IN_PROGRESS.value,  # st_001 - Roof damage from hail storm
        Status.IN_PROGRESS.value,  # jn_002 - Wind damage, emergency tarp installed
        Status.DISPATCHED.value,  # al_003 - Multiple shingle damage, military discount
        Status.SCHEDULED.value,  # md_004 - Storm damage claim pending
        Status.SCHEDULED.value,  # st_005 - Maintenance customer, no claim
        Status.IN_PROGRESS.value,  # st_006 - Urgent repair needed
        Status.DISPATCHED.value,  # st_007 - Wind damage, high deductible
        Status.IN_PROGRESS.value,  # jn_008 - Multiple shingle replacement
        Status.SCHEDULED.value,  # jn_009 - Routine maintenance
        Status.IN_PROGRESS.value,  # jn_010 - Storm damage, quick resolution needed
        Status.SCHEDULED.value,  # jn_011 - Hail damage assessment needed
        Status.SCHEDULED.value,  # jn_012 - Preventive maintenance
        Status.IN_PROGRESS.value,  # jn_013 - Wind and hail damage, emergency tarp
        Status.SCHEDULED.value,  # jn_014 - New customer referral
        Status.HOLD.value,  # al_015 - Large commercial claim, multiple buildings
        Status.SCHEDULED.value,  # al_016 - Maintenance customer
        Status.DISPATCHED.value,  # al_017 - Storm damage, veteran discount
        Status.DISPATCHED.value,  # al_018 - High-value home, premium materials
        Status.SCHEDULED.value,  # al_019 - Regular maintenance
        Status.IN_PROGRESS.value,  # al_020 - Wind damage, quick estimate needed
        Status.SCHEDULED.value,  # al_021 - New construction inspection
        Status.SCHEDULED.value,  # md_022 - Hail damage assessment
        Status.COMPLETED.value,  # md_023 - Routine maintenance
        Status.HOLD.value,  # md_024 - Complex claim, detailed assessment
        Status.IN_PROGRESS.value,  # md_025 - Wind and hail damage
        Status.SCHEDULED.value,  # md_026 - Senior citizen preventive maintenance
        Status.IN_PROGRESS.value,  # md_027 - Large property, multiple damage areas
        Status.COMPLETED.value,  # md_028 - Long-term customer maintenance
    ]

    projects = []
    for idx, data in enumerate(MOCK_PROJECTS_RAW):
        # Parse address components
        address = data.get("address", "")
        address_parts = [p.strip() for p in address.split(",")]

        address_line1 = address_parts[0] if len(address_parts) > 0 else None
        city = address_parts[1] if len(address_parts) > 1 else None

        # Parse state and zip from last part (e.g., "TX 78701")
        state = None
        postal_code = None
        if len(address_parts) > 2:
            state_zip = address_parts[2].split()
            state = state_zip[0] if len(state_zip) > 0 else None
            postal_code = state_zip[1] if len(state_zip) > 1 else None

        # Add mock job_id to data
        job_id = _derive_numeric_job_id(data["id"])

        # Create universal Project
        project = Project(
            id=data["id"],
            name=data.get("customerName"),
            number=str(job_id),
            status=project_statuses[idx],
            status_id=None,
            sub_status=None,
            sub_status_id=None,
            workflow_type="Restoration",
            description=data.get("notes"),
            customer_id=data["id"],  # Use project ID as customer ID
            customer_name=data.get("customerName"),
            location_id=None,
            address_line1=address_line1,
            address_line2=None,
            city=city,
            state=state,
            postal_code=postal_code,
            country="USA",
            created_at=now,
            updated_at=now,
            start_date=None,
            target_completion_date=None,
            actual_completion_date=None,
            claim_number=data.get("claimNumber"),
            date_of_loss=data.get("dateOfLoss"),
            insurance_company=data.get("insuranceAgency"),
            adjuster_name=data.get("adjusterName") or data.get("adjusterContact", {}).get("name"),
            adjuster_phone=data.get("adjusterContact", {}).get("phone"),
            adjuster_email=data.get("adjusterContact", {}).get("email"),
            sales_rep_id=None,
            sales_rep_name=None,
            provider=CRMProvider.MOCK,
            provider_data={**data, "tenant": 1, "job_id": job_id},
        )
        projects.append(project)

    return projects
