from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class FieldType(str, Enum):
    """Form field classifications"""
    EMAIL = "email"
    PHONE = "phone"
    TEXT = "text"
    LONG_TEXT = "long_text"
    CHECKBOX = "checkbox"
    DROPDOWN = "dropdown"
    FILE_UPLOAD = "file_upload"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    DATE = "date"
    UNKNOWN = "unknown"


class CaptchaType(str, Enum):
    """CAPTCHA types found on forms"""
    RECAPTCHA_V2 = "reCAPTCHA_v2"
    RECAPTCHA_V3 = "reCAPTCHA_v3"
    HCAPTCHA = "hCaptcha"
    CLOUDFLARE = "Cloudflare_Turnstile"
    NONE = "none"


class ApplicationStatus(str, Enum):
    """Application submission status"""
    PENDING = "pending"
    FILLED = "filled"
    CAPTCHA_QUARANTINE = "captcha_quarantine"
    SUBMITTED = "submitted"
    FAILED = "failed"
    SUCCESS = "success"


class ErrorType(str, Enum):
    """Error classifications for retry logic"""
    CAPTCHA = "captcha"
    VALIDATION = "validation"
    NETWORK = "network"
    FIELD_NOT_FOUND = "field_not_found"
    SUBMIT_FAILED = "submit_failed"
    UNKNOWN = "unknown"


class FormField(BaseModel):
    """Detected form field"""
    selector: str  # CSS selector to find element
    name: str  # HTML name attribute
    html_type: str  # HTML type (email, text, file, etc)
    field_type: FieldType  # Our classification
    required: bool
    placeholder: Optional[str] = None
    label_text: Optional[str] = None
    inferred_candidate_field: Optional[str] = None  # e.g., "candidate.email"
    user_confirmed: bool = False  # User manually verified this field

    class Config:
        use_enum_values = False


class FormSchema(BaseModel):
    """Learned form structure"""
    id: Optional[str] = None
    url: str
    url_pattern: Optional[str] = None  # Pattern for multiple pages
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    last_verified: datetime = Field(default_factory=datetime.utcnow)
    fields: List[FormField]
    captcha_type: CaptchaType = CaptchaType.NONE
    submit_selector: str  # CSS selector for submit button
    is_multistep: bool = False
    success_indicator: Optional[str] = None  # Selector for success message
    form_type: Optional[str] = None  # "nursing_school", "eldercare", etc

    class Config:
        use_enum_values = False


class Candidate(BaseModel):
    """Candidate profile for applications"""
    id: Optional[str] = None
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str
    phone: str
    cv_file: str  # Path to PDF file
    certifications: List[str] = []  # ["RN", "Deutsch B2"]
    languages: List[str] = []  # ["English", "German"]
    motivation: Optional[str] = None  # Cover letter text
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = False


class ApplicationRecord(BaseModel):
    """Track a single form submission attempt"""
    id: Optional[str] = None
    candidate_id: str
    form_schema_id: str
    url: str
    status: ApplicationStatus = ApplicationStatus.PENDING
    attempt_count: int = 0
    max_attempts: int = 3
    last_error: Optional[str] = None
    error_type: Optional[ErrorType] = None
    submitted_at: Optional[datetime] = None
    screenshot_path: Optional[str] = None
    form_data_submitted: Optional[Dict[str, str]] = None
    requires_manual_action: bool = False
    manual_action_type: Optional[str] = None  # "captcha", "field_mapping", etc
    batch_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = False


class FormMappingRequest(BaseModel):
    """User manually maps form fields"""
    form_schema_id: str
    field_mappings: Dict[str, str]  # {selector: "candidate.email", ...}
    notes: Optional[str] = None


class BatchApplyRequest(BaseModel):
    """Request to apply to multiple forms"""
    candidate_id: str
    urls: List[str]
    auto_detect: bool = True  # Try to detect & fill without user confirmation
    skip_captcha: bool = False  # Skip forms with CAPTCHAs
