from enum import Enum


class Role(str, Enum):
    """User roles in the system."""

    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


class Permission(str, Enum):
    """System permissions."""

    # Content management
    CREATE_CONTENT = "create_content"
    EDIT_CONTENT = "edit_content"
    DELETE_CONTENT = "delete_content"
    VIEW_CONTENT = "view_content"

    # Organization management
    VIEW_ORGANIZATION = "view_organization"
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"


class CookieNames(str, Enum):
    """Cookie names used in the authentication system."""

    SESSION_TOKEN = "session_token"
    REFRESH_TOKEN = "refresh_token"


class SameSite(str, Enum):
    """SameSite cookie settings."""

    LAX = "lax"
    STRICT = "strict"
    NONE = "none"


class TimeInSeconds(int):
    """Time constants in seconds."""

    ONE_HOUR = 3600
    ONE_DAY = 86400
    THIRTY_DAYS = 2592000


class OAuthEndpoints(str, Enum):
    """AWS Cognito endpoint constants."""

    TOKEN_ENDPOINT = "/oauth2/token"
    USERINFO_ENDPOINT = "/oauth2/userInfo"
