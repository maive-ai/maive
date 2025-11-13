"""
Mock CRM project data for demos and local development.

This file contains hardcoded project data that can be easily removed
when switching to real CRM integrations.
"""

import uuid
from datetime import UTC, datetime

from src.integrations.crm.constants import CRMProvider, Status
from src.integrations.crm.providers.mock.schemas import ContactInfo, MockNote, MockProject
from src.integrations.crm.schemas import Note, Project

# Default phone number for all mock data
DEFAULT_PHONE_NUMBER = "+17032681917"

# Easy to modify name for demos
DEMO_NAME = "Brandi Ivy"
DEMO_EMAIL = DEMO_NAME.replace(" ", ".").lower() + "@gmail.com"


# Mock customer/project data as typed objects
MOCK_PROJECTS_RAW: list[MockProject] = [
    MockProject(
        id="jn_002",
        customerName="Emily Davis",
        address="456 Oak Avenue, Overland Park, KS 66213",
        phone=DEFAULT_PHONE_NUMBER,
        email="emily.davis@gmail.com",
        claimNumber="CLM-2024-002",
        dateOfLoss="2024-09-01",
        insuranceAgency="Allstate Insurance",
        insuranceAgencyContact=ContactInfo(
            name=DEMO_NAME,
            phone=DEFAULT_PHONE_NUMBER,
            email=DEMO_EMAIL,
        ),
        adjusterName=DEMO_NAME,
        adjusterContact=ContactInfo(
            name=DEMO_NAME,
            phone=DEFAULT_PHONE_NUMBER,
            email=DEMO_EMAIL,
        ),
        notes=[MockNote(text="Wind damage on muliple faces. Emergency tarp installed.")],
        status=Status.IN_PROGRESS.value,
    ),
    MockProject(
        id="st_001",
        customerName="John Smith",
        address="123 Main St, Coalville, UT 84017",
        phone=DEFAULT_PHONE_NUMBER,
        email="john.smith@gmail.com",
        claimNumber="CLM-2024-001",
        dateOfLoss="2024-08-15",
        insuranceAgency="State Farm Insurance",
        insuranceAgencyContact=ContactInfo(
            name="Rick Davis",
            phone=DEFAULT_PHONE_NUMBER,
            email="Rick.Davis@statefarm.com",
        ),
        adjusterName="Rick Davis",
        adjusterContact=ContactInfo(
            name="Rick Davis",
            phone=DEFAULT_PHONE_NUMBER,
            email="Rick.Davis@statefarm.com",
        ),
        notes=[MockNote(text="Roof damage from hail storm. Customer requests neon yellow roof.")],
        status=Status.IN_PROGRESS.value,
    ),
    MockProject(
        id="al_003",
        customerName="Michael Thompson",
        address="789 Pine Street, Houston, TX 77001",
        phone=DEFAULT_PHONE_NUMBER,
        email="michael.thompson@gmail.com",
        claimNumber="CLM-2024-003",
        dateOfLoss="2024-08-28",
        insuranceAgency="USAA Insurance",
        insuranceAgencyContact=ContactInfo(
            name="Jennifer Martinez",
            phone=DEFAULT_PHONE_NUMBER,
            email="jennifer.martinez@usaa.com",
        ),
        adjusterName="David Brown",
        adjusterContact=ContactInfo(
            name="David Brown",
            phone=DEFAULT_PHONE_NUMBER,
            email="david.brown@usaa.com",
        ),
        status=Status.DISPATCHED.value,
        notes=[MockNote(text="Multiple shingle damage areas. Customer has military discount.")],
    ),
    MockProject(
        id="md_004",
        customerName="Sarah Wilson",
        address="321 Elm Drive, San Antonio, TX 78201",
        phone=DEFAULT_PHONE_NUMBER,
        email="sarah.wilson@gmail.com",
        claimNumber="CLM-2024-004",
        dateOfLoss="2024-09-10",
        insuranceAgency="Farmers Insurance",
        insuranceAgencyContact=ContactInfo(
            name="Kevin Lee",
            phone=DEFAULT_PHONE_NUMBER,
            email="kevin.lee@farmersinsurance.com",
        ),
        adjusterName="Amanda Garcia",
        adjusterContact=ContactInfo(
            name="Amanda Garcia",
            phone=DEFAULT_PHONE_NUMBER,
            email="amanda.garcia@farmersinsurance.com",
        ),
        status=Status.SCHEDULED.value,
        notes=[MockNote(text="Storm damage claim pending. Customer needs quick turnaround.")],
    ),
    MockProject(
        id="st_005",
        customerName="Robert Johnson",
        address="654 Cedar Lane, Fort Worth, TX 76101",
        phone=DEFAULT_PHONE_NUMBER,
        email="robert.johnson@gmail.com",
        notes=[MockNote(text="Maintenance customer. No insurance claim.")],
        status=Status.SCHEDULED.value,
    ),
    MockProject(
        id="st_006",
        customerName="Jennifer Martinez",
        address="987 Maple Avenue, Plano, TX 75023",
        phone=DEFAULT_PHONE_NUMBER,
        email="jennifer.martinez@gmail.com",
        claimNumber="CLM-2024-005",
        dateOfLoss="2024-09-05",
        insuranceAgency="Liberty Mutual",
        insuranceAgencyContact=ContactInfo(
            name="Carlos Rivera",
            phone=DEFAULT_PHONE_NUMBER,
            email="carlos.rivera@libertymutual.com",
        ),
        adjusterName="Patricia Lee",
        adjusterContact=ContactInfo(
            name="Patricia Lee",
            phone=DEFAULT_PHONE_NUMBER,
            email="patricia.lee@libertymutual.com",
        ),
        status=Status.IN_PROGRESS.value,
        notes=[MockNote(text="Hail damage to roof and gutters. Urgent repair needed.")],
    ),
    MockProject(
        id="st_007",
        customerName="David Chen",
        address="456 Willow Street, Richardson, TX 75080",
        phone=DEFAULT_PHONE_NUMBER,
        email="david.chen@gmail.com",
        claimNumber="CLM-2024-006",
        dateOfLoss="2024-08-20",
        insuranceAgency="Progressive Insurance",
        insuranceAgencyContact=ContactInfo(
            name="Michelle Wong",
            phone=DEFAULT_PHONE_NUMBER,
            email="michelle.wong@progressive.com",
        ),
        adjusterName="Brian Taylor",
        adjusterContact=ContactInfo(
            name="Brian Taylor",
            phone=DEFAULT_PHONE_NUMBER,
            email="brian.taylor@progressive.com",
        ),
        status=Status.DISPATCHED.value,
        notes=[MockNote(text="Wind damage from storm. Customer has high deductible.")],
    ),
    MockProject(
        id="jn_008",
        customerName="Lisa Anderson",
        address="321 Sunset Drive, Garland, TX 75040",
        phone=DEFAULT_PHONE_NUMBER,
        email="lisa.anderson@gmail.com",
        claimNumber="CLM-2024-007",
        dateOfLoss="2024-09-12",
        insuranceAgency="Geico Insurance",
        insuranceAgencyContact=ContactInfo(
            name="Thomas Kim",
            phone=DEFAULT_PHONE_NUMBER,
            email="thomas.kim@geico.com",
        ),
        adjusterName="Rachel Green",
        adjusterContact=ContactInfo(
            name="Rachel Green",
            phone=DEFAULT_PHONE_NUMBER,
            email="rachel.green@geico.com",
        ),
        status=Status.IN_PROGRESS.value,
        notes=[MockNote(text="Multiple shingle replacement needed. Customer prefers afternoon appointments.")],
    ),
    MockProject(
        id="jn_009",
        customerName="Mark Wilson",
        address="789 Oak Hill Lane, Irving, TX 75061",
        phone=DEFAULT_PHONE_NUMBER,
        email="mark.wilson@gmail.com",
        notes=[MockNote(text="Routine maintenance check. Long-term customer.")],
        status=Status.SCHEDULED.value,
    ),
    MockProject(
        id="jn_010",
        customerName="Amanda Foster",
        address="654 Pine Ridge Court, Mesquite, TX 75149",
        phone=DEFAULT_PHONE_NUMBER,
        email="amanda.foster@gmail.com",
        claimNumber="CLM-2024-008",
        dateOfLoss="2024-08-30",
        insuranceAgency="Nationwide Insurance",
        insuranceAgencyContact=ContactInfo(
            name="Steven Park",
            phone=DEFAULT_PHONE_NUMBER,
            email="steven.park@nationwide.com",
        ),
        adjusterName="Nicole Brown",
        adjusterContact=ContactInfo(
            name="Nicole Brown",
            phone=DEFAULT_PHONE_NUMBER,
            email="nicole.brown@nationwide.com",
        ),
        status=Status.IN_PROGRESS.value,
        notes=[MockNote(text="Storm damage claim. Customer needs quick resolution.")],
    ),
    MockProject(
        id="jn_011",
        customerName="Christopher Davis",
        address="123 Cedar Creek Drive, Grand Prairie, TX 75050",
        phone=DEFAULT_PHONE_NUMBER,
        email="christopher.davis@gmail.com",
        claimNumber="CLM-2024-009",
        dateOfLoss="2024-09-08",
        insuranceAgency="Travelers Insurance",
        insuranceAgencyContact=ContactInfo(
            name="Jessica Liu",
            phone=DEFAULT_PHONE_NUMBER,
            email="jessica.liu@travelers.com",
        ),
        adjusterName="Kevin Murphy",
        adjusterContact=ContactInfo(
            name="Kevin Murphy",
            phone=DEFAULT_PHONE_NUMBER,
            email="kevin.murphy@travelers.com",
        ),
        status=Status.SCHEDULED.value,
        notes=[MockNote(text="Hail damage assessment needed. Customer works from home.")],
    ),
    MockProject(
        id="jn_012",
        customerName="Rebecca Martinez",
        address="987 Elm Street, Carrollton, TX 75006",
        phone=DEFAULT_PHONE_NUMBER,
        email="rebecca.martinez@gmail.com",
        notes=[MockNote(text="Preventive maintenance customer. Annual inspection due.")],
        status=Status.SCHEDULED.value,
    ),
    MockProject(
        id="jn_013",
        customerName="Daniel Rodriguez",
        address="456 Birch Lane, Lewisville, TX 75057",
        phone=DEFAULT_PHONE_NUMBER,
        email="daniel.rodriguez@gmail.com",
        claimNumber="CLM-2024-010",
        dateOfLoss="2024-09-15",
        insuranceAgency="Hartford Insurance",
        insuranceAgencyContact=ContactInfo(
            name="Maria Gonzalez",
            phone=DEFAULT_PHONE_NUMBER,
            email="maria.gonzalez@thehartford.com",
        ),
        adjusterName="James Wilson",
        adjusterContact=ContactInfo(
            name="James Wilson",
            phone=DEFAULT_PHONE_NUMBER,
            email="james.wilson@thehartford.com",
        ),
        status=Status.IN_PROGRESS.value,
        notes=[MockNote(text="Wind and hail damage. Emergency tarp installed.")],
    ),
    MockProject(
        id="jn_014",
        customerName="Stephanie White",
        address="321 Valley View Road, Flower Mound, TX 75022",
        phone=DEFAULT_PHONE_NUMBER,
        email="stephanie.white@gmail.com",
        notes=[MockNote(text="New customer referral. Interested in full roof replacement.")],
        status=Status.SCHEDULED.value,
    ),
    MockProject(
        id="al_015",
        customerName="Thomas Brown",
        address="789 Highland Park Drive, Arlington, TX 76010",
        phone=DEFAULT_PHONE_NUMBER,
        email="thomas.brown@gmail.com",
        claimNumber="CLM-2024-011",
        dateOfLoss="2024-09-03",
        insuranceAgency="Amica Insurance",
        insuranceAgencyContact=ContactInfo(
            name="Linda Johnson",
            phone=DEFAULT_PHONE_NUMBER,
            email="linda.johnson@amica.com",
        ),
        adjusterName="Robert Clark",
        adjusterContact=ContactInfo(
            name="Robert Clark",
            phone=DEFAULT_PHONE_NUMBER,
            email="robert.clark@amica.com",
        ),
        status=Status.HOLD.value,
        notes=[MockNote(text="Large commercial claim. Multiple building assessment needed.")],
    ),
    MockProject(
        id="al_016",
        customerName="Patricia Garcia",
        address="654 Mountain View Circle, Euless, TX 76039",
        phone=DEFAULT_PHONE_NUMBER,
        email="patricia.garcia@gmail.com",
        notes=[MockNote(text="Maintenance customer. Gutter cleaning and inspection.")],
        status=Status.SCHEDULED.value,
    ),
    MockProject(
        id="al_017",
        customerName="William Lee",
        address="123 Riverside Drive, Bedford, TX 76021",
        phone=DEFAULT_PHONE_NUMBER,
        email="william.lee@gmail.com",
        claimNumber="CLM-2024-012",
        dateOfLoss="2024-08-25",
        insuranceAgency="MetLife Insurance",
        insuranceAgencyContact=ContactInfo(
            name="Sandra Kim",
            phone=DEFAULT_PHONE_NUMBER,
            email="sandra.kim@metlife.com",
        ),
        adjusterName="Michael Davis",
        adjusterContact=ContactInfo(
            name="Michael Davis",
            phone=DEFAULT_PHONE_NUMBER,
            email="michael.davis@metlife.com",
        ),
        status=Status.DISPATCHED.value,
        notes=[MockNote(text="Storm damage to shingles and flashing. Veteran discount applied.")],
    ),
    MockProject(
        id="al_018",
        customerName="Michelle Taylor",
        address="987 Forest Glen Way, Hurst, TX 76053",
        phone=DEFAULT_PHONE_NUMBER,
        email="michelle.taylor@gmail.com",
        claimNumber="CLM-2024-013",
        dateOfLoss="2024-09-10",
        insuranceAgency="Chubb Insurance",
        insuranceAgencyContact=ContactInfo(
            name="David Chen",
            phone=DEFAULT_PHONE_NUMBER,
            email="david.chen@chubb.com",
        ),
        adjusterName="Jennifer Lopez",
        adjusterContact=ContactInfo(
            name="Jennifer Lopez",
            phone=DEFAULT_PHONE_NUMBER,
            email="jennifer.lopez@chubb.com",
        ),
        status=Status.DISPATCHED.value,
        notes=[MockNote(text="High-value home. Premium materials required.")],
    ),
    MockProject(
        id="al_019",
        customerName="Joseph Martinez",
        address="456 Creekside Lane, Colleyville, TX 76034",
        phone=DEFAULT_PHONE_NUMBER,
        email="joseph.martinez@gmail.com",
        notes=[MockNote(text="Regular maintenance customer. Quarterly inspections.")],
        status=Status.SCHEDULED.value,
    ),
    MockProject(
        id="al_020",
        customerName="Karen Anderson",
        address="321 Oakwood Drive, Grapevine, TX 76051",
        phone=DEFAULT_PHONE_NUMBER,
        email="karen.anderson@gmail.com",
        claimNumber="CLM-2024-014",
        dateOfLoss="2024-09-07",
        insuranceAgency="American Family Insurance",
        insuranceAgencyContact=ContactInfo(
            name="Robert Wang",
            phone=DEFAULT_PHONE_NUMBER,
            email="robert.wang@amfam.com",
        ),
        adjusterName="Lisa Thompson",
        adjusterContact=ContactInfo(
            name="Lisa Thompson",
            phone=DEFAULT_PHONE_NUMBER,
            email="lisa.thompson@amfam.com",
        ),
        status=Status.IN_PROGRESS.value,
        notes=[MockNote(text="Wind damage from recent storm. Customer needs quick estimate.")],
    ),
    MockProject(
        id="al_021",
        customerName="Steven Wilson",
        address="789 Meadowbrook Lane, Southlake, TX 76092",
        phone=DEFAULT_PHONE_NUMBER,
        email="steven.wilson@gmail.com",
        notes=[MockNote(text="New construction inspection. High-end residential project.")],
        status=Status.SCHEDULED.value,
    ),
    MockProject(
        id="md_022",
        customerName="Nancy Rodriguez",
        address="654 Sunset Boulevard, Mansfield, TX 76063",
        phone=DEFAULT_PHONE_NUMBER,
        email="nancy.rodriguez@gmail.com",
        claimNumber="CLM-2024-015",
        dateOfLoss="2024-09-02",
        insuranceAgency="Safeco Insurance",
        insuranceAgencyContact=ContactInfo(
            name="Mark Johnson",
            phone=DEFAULT_PHONE_NUMBER,
            email="mark.johnson@safeco.com",
        ),
        adjusterName="Carol Smith",
        adjusterContact=ContactInfo(
            name="Carol Smith",
            phone=DEFAULT_PHONE_NUMBER,
            email="carol.smith@safeco.com",
        ),
        status=Status.SCHEDULED.value,
        notes=[MockNote(text="Hail damage assessment. Customer has elderly parents living with them.")],
    ),
    MockProject(
        id="md_023",
        customerName="Richard Davis",
        address="123 Prairie View Drive, Cedar Hill, TX 75104",
        phone=DEFAULT_PHONE_NUMBER,
        email="richard.davis@gmail.com",
        notes=[MockNote(text="Routine maintenance customer. Annual roof cleaning.")],
        status=Status.COMPLETED.value,
    ),
    MockProject(
        id="md_024",
        customerName="Helen Garcia",
        address="987 Hillside Avenue, DeSoto, TX 75115",
        phone=DEFAULT_PHONE_NUMBER,
        email="helen.garcia@gmail.com",
        claimNumber="CLM-2024-016",
        dateOfLoss="2024-08-28",
        insuranceAgency="Auto-Owners Insurance",
        insuranceAgencyContact=ContactInfo(
            name="Paul Martinez",
            phone=DEFAULT_PHONE_NUMBER,
            email="paul.martinez@auto-owners.com",
        ),
        adjusterName="Susan Brown",
        adjusterContact=ContactInfo(
            name="Susan Brown",
            phone=DEFAULT_PHONE_NUMBER,
            email="susan.brown@auto-owners.com",
        ),
        status=Status.HOLD.value,
        notes=[MockNote(text="Storm damage to multiple areas. Complex claim requiring detailed assessment.")],
    ),
    MockProject(
        id="md_025",
        customerName="Paul Thompson",
        address="456 Garden Valley Road, Lancaster, TX 75146",
        phone=DEFAULT_PHONE_NUMBER,
        email="paul.thompson@gmail.com",
        claimNumber="CLM-2024-017",
        dateOfLoss="2024-09-11",
        insuranceAgency="Mutual of Omaha",
        insuranceAgencyContact=ContactInfo(
            name="Emily Davis",
            phone=DEFAULT_PHONE_NUMBER,
            email="emily.davis@mutualofomaha.com",
        ),
        adjusterName="Anthony Wilson",
        adjusterContact=ContactInfo(
            name="Anthony Wilson",
            phone=DEFAULT_PHONE_NUMBER,
            email="anthony.wilson@mutualofomaha.com",
        ),
        status=Status.IN_PROGRESS.value,
        notes=[MockNote(text="Wind and hail damage. Customer works night shift, prefers daytime appointments.")],
    ),
    MockProject(
        id="md_026",
        customerName="Dorothy Lee",
        address="321 Brookside Drive, Duncanville, TX 75116",
        phone=DEFAULT_PHONE_NUMBER,
        email="dorothy.lee@gmail.com",
        notes=[MockNote(text="Senior citizen customer. Preventive maintenance and inspection.")],
        status=Status.SCHEDULED.value,
    ),
    MockProject(
        id="md_027",
        customerName="Kenneth Martinez",
        address="789 Woodland Trail, Glenn Heights, TX 75154",
        phone=DEFAULT_PHONE_NUMBER,
        email="kenneth.martinez@gmail.com",
        claimNumber="CLM-2024-018",
        dateOfLoss="2024-09-04",
        insuranceAgency="Cincinnati Insurance",
        insuranceAgencyContact=ContactInfo(
            name="Angela Rodriguez",
            phone=DEFAULT_PHONE_NUMBER,
            email="angela.rodriguez@cinfin.com",
        ),
        adjusterName="Gregory Taylor",
        adjusterContact=ContactInfo(
            name="Gregory Taylor",
            phone=DEFAULT_PHONE_NUMBER,
            email="gregory.taylor@cinfin.com",
        ),
        status=Status.IN_PROGRESS.value,
        notes=[MockNote(text="Large residential property. Multiple damage areas from recent storm.")],
    ),
    MockProject(
        id="md_028",
        customerName="Betty Anderson",
        address="654 Maple Ridge Circle, Red Oak, TX 75154",
        phone=DEFAULT_PHONE_NUMBER,
        email="betty.anderson@gmail.com",
        notes=[MockNote(text="Long-term customer. Quarterly gutter maintenance and roof inspection.")],
        status=Status.COMPLETED.value,
    ),
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


def parse_raw_project_data(
    mock_project: MockProject, job_id: int | None = None, timestamp: str | None = None
) -> Project:
    """
    Parse a MockProject into a properly structured Project object.

    Args:
        mock_project: MockProject instance
        job_id: Optional job_id override (defaults to derived from project id)
        timestamp: ISO timestamp for created_at/updated_at (defaults to now)

    Returns:
        Project: Fully populated Project object
    """
    if timestamp is None:
        timestamp = datetime.now(UTC).isoformat()

    # Parse address components
    address = mock_project.address or ""
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

    # Derive job_id if not provided
    if job_id is None:
        job_id = _derive_numeric_job_id(mock_project.id)

    # Get adjuster info from adjusterContact or adjusterName
    adjuster_name = mock_project.adjuster_name
    adjuster_phone = None
    adjuster_email = None

    if mock_project.adjuster_contact:
        adjuster_name = adjuster_name or mock_project.adjuster_contact.name
        adjuster_phone = mock_project.adjuster_contact.phone
        adjuster_email = mock_project.adjuster_contact.email

    # Get insurance company from either field
    insurance_company = mock_project.insurance_company or mock_project.insurance_agency

    # Convert to provider_data dict for storage
    provider_data = mock_project.model_dump(by_alias=True, exclude_none=True)

    # Convert ContactInfo instances to dicts for storage
    if mock_project.insurance_agency_contact:
        provider_data["insuranceAgencyContact"] = mock_project.insurance_agency_contact.model_dump(exclude_none=True)
    if mock_project.adjuster_contact:
        provider_data["adjusterContact"] = mock_project.adjuster_contact.model_dump(exclude_none=True)

    provider_data["job_id"] = job_id
    provider_data["tenant"] = 1

    # Create universal Project
    project = Project(
        id=mock_project.id,
        name=mock_project.customer_name,
        number=str(job_id),
        status=mock_project.status,
        status_id=None,
        sub_status=None,
        sub_status_id=None,
        workflow_type="Restoration",
        description=None,
        customer_id=mock_project.id,
        customer_name=mock_project.customer_name,
        location_id=None,
        address_line1=address_line1,
        address_line2=None,
        city=city,
        state=state,
        postal_code=postal_code,
        country="USA",
        created_at=timestamp,
        updated_at=timestamp,
        start_date=None,
        target_completion_date=None,
        actual_completion_date=None,
        claim_number=mock_project.claim_number,
        date_of_loss=mock_project.date_of_loss,
        insurance_company=insurance_company,
        adjuster_name=adjuster_name,
        adjuster_phone=adjuster_phone,
        adjuster_email=adjuster_email,
        sales_rep_id=None,
        sales_rep_name=None,
        provider=CRMProvider.MOCK,
        provider_data=provider_data,
    )

    # Convert notes list to Note objects
    if mock_project.notes:
        project.notes = [
            Note(
                id=note.id or str(uuid.uuid4()),
                text=note.text,
                entity_id=mock_project.id,
                entity_type="project",
                created_by_id=None,
                created_by_name=None,
                created_at=timestamp,
                updated_at=timestamp,
                is_pinned=False,
                provider=CRMProvider.MOCK,
                provider_data={},
            )
            for note in mock_project.notes
        ]

    return project


def get_mock_projects() -> list[Project]:
    """
    Get mock projects with assigned statuses.

    Returns a list of universal Project models.
    """
    now = datetime.now(UTC).isoformat()

    projects = []
    for mock_project in MOCK_PROJECTS_RAW:
        # Use shared parsing logic
        project = parse_raw_project_data(mock_project, timestamp=now)
        projects.append(project)

    return projects
