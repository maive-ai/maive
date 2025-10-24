"""JobNimbus-specific constants."""


class JobNimbusEndpoints:
    """JobNimbus API endpoints."""

    BASE_URL = "https://app.jobnimbus.com/api1"

    # Jobs endpoints
    JOBS = "/jobs"
    JOB_BY_ID = "/jobs/{jnid}"

    # Contacts endpoints
    CONTACTS = "/contacts"
    CONTACT_BY_ID = "/contacts/{jnid}"

    # Activities endpoints (notes)
    ACTIVITIES = "/activities"
    ACTIVITY_BY_ID = "/activities/{jnid}"

    # Tasks endpoints
    TASKS = "/tasks"
    TASK_BY_ID = "/tasks/{jnid}"

    # Files endpoints
    FILES = "/files"
    FILE_BY_ID = "/files/{jnid}"
