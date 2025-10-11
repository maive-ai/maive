"""
Mock CRM project data for demos and local development.

This file contains hardcoded project data that can be easily removed
when switching to real CRM integrations.
"""

import random
from datetime import UTC, datetime

from src.integrations.crm.constants import Status
from src.integrations.crm.schemas import ContactInfo, Project, ProjectData

# Default phone number for all mock data
DEFAULT_PHONE_NUMBER = "+1-703-268-1917"


# Project statuses
PROJECT_STATUSES = [status.value for status in Status]


# Mock customer/project data using Pydantic models
MOCK_PROJECTS_RAW: list[ProjectData] = [
    ProjectData(
        id="st_001",
        customerName="John Smith",
        address="123 Main St, Austin, TX 78701",
        phone=DEFAULT_PHONE_NUMBER,
        email="john.smith@gmail.com",
        claimNumber="CLM-2024-001",
        dateOfLoss="2024-08-15",
        insuranceAgency="State Farm Insurance",
        insuranceAgencyContact=ContactInfo(
            name="Sarah Johnson",
            phone=DEFAULT_PHONE_NUMBER,
            email="sarah.johnson@statefarm.com",
        ),
        adjusterName="Mike Williams",
        adjusterContact=ContactInfo(
            name="Mike Williams",
            phone=DEFAULT_PHONE_NUMBER,
            email="mike.williams@statefarm.com",
        ),
        notes="Roof damage from hail storm. Customer prefers morning appointments.",
    ),
    ProjectData(
        id="jn_002",
        customerName="Emily Davis",
        address="456 Oak Avenue, Dallas, TX 75201",
        phone=DEFAULT_PHONE_NUMBER,
        email="emily.davis@gmail.com",
        claimNumber="CLM-2024-002",
        dateOfLoss="2024-09-01",
        insuranceAgency="Allstate Insurance",
        insuranceAgencyContact=ContactInfo(
            name="Robert Chen",
            phone=DEFAULT_PHONE_NUMBER,
            email="robert.chen@allstate.com",
        ),
        adjusterName="Lisa Rodriguez",
        adjusterContact=ContactInfo(
            name="Lisa Rodriguez",
            phone=DEFAULT_PHONE_NUMBER,
            email="lisa.rodriguez@allstate.com",
        ),
        notes="Wind damage to gutters and siding. Emergency tarp installed.",
    ),
    ProjectData(
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
        notes="Multiple shingle damage areas. Customer has military discount.",
    ),
    ProjectData(
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
        notes="Storm damage claim pending. Customer needs quick turnaround.",
    ),
    ProjectData(
        id="st_005",
        customerName="Robert Johnson",
        address="654 Cedar Lane, Fort Worth, TX 76101",
        phone=DEFAULT_PHONE_NUMBER,
        email="robert.johnson@gmail.com",
        notes="Maintenance customer. No insurance claim.",
    ),
    ProjectData(
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
        notes="Hail damage to roof and gutters. Urgent repair needed.",
    ),
    ProjectData(
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
        notes="Wind damage from storm. Customer has high deductible.",
    ),
    ProjectData(
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
        notes="Multiple shingle replacement needed. Customer prefers afternoon appointments.",
    ),
    ProjectData(
        id="jn_009",
        customerName="Mark Wilson",
        address="789 Oak Hill Lane, Irving, TX 75061",
        phone=DEFAULT_PHONE_NUMBER,
        email="mark.wilson@gmail.com",
        notes="Routine maintenance check. Long-term customer.",
    ),
    ProjectData(
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
        notes="Storm damage claim. Customer needs quick resolution.",
    ),
    ProjectData(
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
        notes="Hail damage assessment needed. Customer works from home.",
    ),
    ProjectData(
        id="jn_012",
        customerName="Rebecca Martinez",
        address="987 Elm Street, Carrollton, TX 75006",
        phone=DEFAULT_PHONE_NUMBER,
        email="rebecca.martinez@gmail.com",
        notes="Preventive maintenance customer. Annual inspection due.",
    ),
    ProjectData(
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
        notes="Wind and hail damage. Emergency tarp installed.",
    ),
    ProjectData(
        id="jn_014",
        customerName="Stephanie White",
        address="321 Valley View Road, Flower Mound, TX 75022",
        phone=DEFAULT_PHONE_NUMBER,
        email="stephanie.white@gmail.com",
        notes="New customer referral. Interested in full roof replacement.",
    ),
    ProjectData(
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
        notes="Large commercial claim. Multiple building assessment needed.",
    ),
    ProjectData(
        id="al_016",
        customerName="Patricia Garcia",
        address="654 Mountain View Circle, Euless, TX 76039",
        phone=DEFAULT_PHONE_NUMBER,
        email="patricia.garcia@gmail.com",
        notes="Maintenance customer. Gutter cleaning and inspection.",
    ),
    ProjectData(
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
        notes="Storm damage to shingles and flashing. Veteran discount applied.",
    ),
    ProjectData(
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
        notes="High-value home. Premium materials required.",
    ),
    ProjectData(
        id="al_019",
        customerName="Joseph Martinez",
        address="456 Creekside Lane, Colleyville, TX 76034",
        phone=DEFAULT_PHONE_NUMBER,
        email="joseph.martinez@gmail.com",
        notes="Regular maintenance customer. Quarterly inspections.",
    ),
    ProjectData(
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
        notes="Wind damage from recent storm. Customer needs quick estimate.",
    ),
    ProjectData(
        id="al_021",
        customerName="Steven Wilson",
        address="789 Meadowbrook Lane, Southlake, TX 76092",
        phone=DEFAULT_PHONE_NUMBER,
        email="steven.wilson@gmail.com",
        notes="New construction inspection. High-end residential project.",
    ),
    ProjectData(
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
        notes="Hail damage assessment. Customer has elderly parents living with them.",
    ),
    ProjectData(
        id="md_023",
        customerName="Richard Davis",
        address="123 Prairie View Drive, Cedar Hill, TX 75104",
        phone=DEFAULT_PHONE_NUMBER,
        email="richard.davis@gmail.com",
        notes="Routine maintenance customer. Annual roof cleaning.",
    ),
    ProjectData(
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
        notes="Storm damage to multiple areas. Complex claim requiring detailed assessment.",
    ),
    ProjectData(
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
        notes="Wind and hail damage. Customer works night shift, prefers daytime appointments.",
    ),
    ProjectData(
        id="md_026",
        customerName="Dorothy Lee",
        address="321 Brookside Drive, Duncanville, TX 75116",
        phone=DEFAULT_PHONE_NUMBER,
        email="dorothy.lee@gmail.com",
        notes="Senior citizen customer. Preventive maintenance and inspection.",
    ),
    ProjectData(
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
        notes="Large residential property. Multiple damage areas from recent storm.",
    ),
    ProjectData(
        id="md_028",
        customerName="Betty Anderson",
        address="654 Maple Ridge Circle, Red Oak, TX 75154",
        phone=DEFAULT_PHONE_NUMBER,
        email="betty.anderson@gmail.com",
        notes="Long-term customer. Quarterly gutter maintenance and roof inspection.",
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


def get_mock_projects() -> list[Project]:
    """
    Get mock projects with randomly assigned statuses.

    Returns a list of MockProject models with assigned statuses.
    """
    now = datetime.now(UTC).isoformat()

    projects = []
    for project_data in MOCK_PROJECTS_RAW:
        # Add Service Titan-like metadata with numeric tenant and job_id
        project_data.tenant = 1
        project_data.job_id = _derive_numeric_job_id(project_data.id)

        project = Project(
            project_data=project_data,
            status=random.choice(PROJECT_STATUSES),
            updated_at=now,
        )
        projects.append(project)

    return projects
