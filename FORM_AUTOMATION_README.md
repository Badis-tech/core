# Form Automation System - Nursing Ausbildung Bot

**Current Status:** MVP Architecture Complete - Ready for Testing

## Architecture Overview

```
┌─────────────────────────────────────────┐
│ Phase 1: Form Detection (COMPLETE)     │
├─────────────────────────────────────────┤
│ ✓ Playwright-based form field scanner  │
│ ✓ Field type classification             │
│ ✓ CAPTCHA detection                     │
│ ✓ User manual field mapping             │
│ ✓ Form schema storage                   │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ Phase 2: Form Filling (COMPLETE)       │
├─────────────────────────────────────────┤
│ ✓ Candidate data mapping                │
│ ✓ Field value injection                 │
│ ✓ File upload handling                  │
│ ✓ Form submission                       │
│ ✓ Success detection                     │
│ ✓ Screenshot capture                    │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│ Phase 3: API Layer (COMPLETE)          │
├─────────────────────────────────────────┤
│ ✓ REST endpoints                        │
│ ✓ Batch processing                      │
│ ✓ Application tracking                  │
│ ✓ Retry logic                           │
│ ✓ Background task queueing              │
└─────────────────────────────────────────┘
```

## Project Structure

```
automation/
├── __init__.py
├── models.py              # Data models (Candidate, FormSchema, ApplicationRecord)
├── form_filler/
│   ├── __init__.py
│   ├── detector.py        # FormDetector - finds & classifies form fields
│   └── filler.py          # FormFiller - fills & submits forms
api/
└── routes/
    └── automation.py      # FastAPI endpoints
```

## Core Components

### 1. **FormDetector** (`automation/form_filler/detector.py`)
Analyzes web pages and extracts form structure.

**What it does:**
- Navigates to URL with Playwright
- Waits for JavaScript rendering (React/Vue/Angular)
- Scans all `<input>`, `<textarea>`, `<select>` elements
- Classifies fields (email, phone, text, file, etc.)
- Detects CAPTCHA (reCAPTCHA v2/v3, hCaptcha, Cloudflare)
- Identifies submit button
- Returns structured `FormSchema` for user confirmation

**Supported field types:**
- `FieldType.EMAIL` - email addresses
- `FieldType.PHONE` - phone numbers
- `FieldType.TEXT` - single-line text
- `FieldType.LONG_TEXT` - multiline text (textarea)
- `FieldType.FILE_UPLOAD` - file inputs
- `FieldType.CHECKBOX` - boolean fields
- `FieldType.DROPDOWN` - select fields
- `FieldType.DATE` - date inputs

### 2. **FormFiller** (`automation/form_filler/filler.py`)
Fills and submits forms with candidate data.

**What it does:**
- Maps candidate attributes to form fields
- Fills text/email/phone inputs
- Handles file uploads (CV/resume)
- Checks & handles CAPTCHAs (pauses for manual solving)
- Submits form
- Captures before/after screenshots
- Returns `ApplicationRecord` with status

**Supported field mappings:**
```python
Candidate.email → form[email_field]
Candidate.phone → form[phone_field]
Candidate.name → form[name_field]
Candidate.cv_file → form[file_input]
Candidate.motivation → form[textarea]
Candidate.certifications → stored in metadata
```

### 3. **API Endpoints** (`api/routes/automation.py`)

#### Create/Manage Candidates
```
POST /automation/candidates
  Body: { name, email, phone, cv_file, certifications, languages }
  Returns: { id, name, email }

GET /automation/candidates/{candidate_id}
  Returns: Full candidate profile
```

#### Detect Forms
```
POST /automation/form-detect?url=https://...
  Returns: { schema_id, fields[], captcha_type, is_multistep }

  Field structure:
  {
    "name": "email",
    "type": "email",
    "required": true,
    "placeholder": "user@example.com",
    "inferred_candidate_field": "candidate.email"
  }
```

#### Confirm Field Mapping
```
POST /automation/form-mapping
  Body: { schema_id, field_mappings: {field_name: "candidate.email"} }
  Returns: { schema_id, status: "mapping_confirmed" }
```

#### Batch Apply
```
POST /automation/batch-apply
  Body: {
    candidate_id: "...",
    urls: ["https://form1.de", "https://form2.de", ...],
    auto_detect: true,
    skip_captcha: false
  }
  Returns: { batch_id, total_queued, applications[] }
```

#### Track Applications
```
GET /automation/applications?candidate_id=...&status=...&limit=100
  Returns: { total, applications[] }

GET /automation/applications/{app_id}
  Returns: Full application record with error details

POST /automation/applications/{app_id}/retry
  Returns: { status: "queued", attempt_count }
```

## Data Models

### Candidate
```python
{
  id: str
  name: str
  first_name: str (optional)
  last_name: str (optional)
  email: str
  phone: str
  cv_file: str  # Path to PDF
  certifications: ["RN", "Deutsch B2"]
  languages: ["English", "German"]
  motivation: str (optional)
}
```

### ApplicationRecord
```python
{
  id: str
  candidate_id: str
  form_schema_id: str
  url: str
  status: "pending" | "filled" | "captcha_quarantine" | "submitted" | "failed" | "success"
  attempt_count: int
  max_attempts: 3
  last_error: str (optional)
  error_type: "captcha" | "validation" | "network" | "field_not_found" | "submit_failed"
  submitted_at: datetime (optional)
  screenshot_path: str (optional)
  requires_manual_action: bool
  manual_action_type: "captcha" | "field_mapping" | etc
}
```

## Usage Example

### 1. Create Candidate
```bash
curl -X POST http://localhost:8000/automation/candidates \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+49123456789",
    "cv_file": "/data/john_doe_cv.pdf",
    "certifications": ["RN", "Deutsch B2"],
    "languages": ["English", "German"],
    "motivation": "Motivated to work in Germany"
  }'
```

### 2. Detect Form
```bash
curl -X POST 'http://localhost:8000/automation/form-detect?url=https://nursing-school.de/apply'
```

Response shows detected fields. User reviews and confirms mapping.

### 3. Batch Apply
```bash
curl -X POST http://localhost:8000/automation/batch-apply \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_id": "cand-123",
    "urls": [
      "https://nursing-school-1.de/apply",
      "https://nursing-school-2.de/apply",
      "https://nursing-school-3.de/apply"
    ],
    "auto_detect": true
  }'
```

### 4. Track Status
```bash
curl http://localhost:8000/automation/applications?candidate_id=cand-123
curl http://localhost:8000/automation/applications/app-456
```

### 5. Retry Failed
```bash
curl -X POST http://localhost:8000/automation/applications/app-456/retry
```

## CAPTCHA Handling

### Current Implementation
Forms with CAPTCHA are flagged as `captcha_quarantine` status with `requires_manual_action: true`.

**Options:**
1. **Manual intervention** - User solves CAPTCHA in browser
2. **2Captcha integration** - (Optional) Auto-solve using external service

### Enable 2Captcha (Optional)
```python
from twocaptcha import TwoCaptcha

# In filler.py, when CAPTCHA detected:
solver = TwoCaptcha('YOUR_API_KEY')
token = solver.recaptcha(sitekey, pageurl)
# Inject token into form
```

Cost: ~$0.001 per CAPTCHA solve (negligible for testing)

## Testing

### Quick Test
```bash
cd /c/Users/MSI/Desktop/core
/c/Users/MSI/Desktop/core/venv/Scripts/python.exe test_form_detection.py
```

### Test with Real Form
1. Update `test_urls` in `test_form_detection.py` with German nursing school form URLs
2. Run test to generate `form_schema.json`
3. Review detected fields
4. Create candidate profile via API
5. Queue batch application

## Next Steps

### Phase 4: Database Integration (Week 1)
- [ ] Replace in-memory storage with PostgreSQL
- [ ] Add Alembic migrations for `candidates`, `form_schemas`, `applications` tables
- [ ] Add indexing for performance

### Phase 5: Scheduler (Week 2)
- [ ] Add Celery worker for async form submissions
- [ ] Implement 24/7 monitoring dashboard
- [ ] Add retry scheduling with exponential backoff

### Phase 6: Form Scraper (Week 3)
- [ ] Build Scrapy crawler to find nursing school forms
- [ ] Auto-detect new forms daily
- [ ] Alert when new positions available

### Phase 7: Smart Detection (Week 4)
- [ ] Train ML model on collected form mappings
- [ ] Auto-predict field types for new forms
- [ ] Reduce manual mapping effort to <10%

## Performance Considerations

### Memory
- Playwright browser instance: ~200MB per instance
- Recommended: 2-3 concurrent instances max on local machine
- Each instance can handle ~10 forms/minute (accounting for JS render time)

### Rate Limiting
- Default delay: 3-5 seconds between submissions
- Some forms have strict rate limits (detect via IP ban)
- Solution: Implement proxy rotation for scale phase

### Database
- `applications` table: Indexes on `candidate_id`, `status`, `url`
- `form_schemas` table: Index on `url` for fast lookup
- Retention: 90 days of application records

## Troubleshooting

### "Field not found" errors
- Form changed since last detection
- Run `POST /form-detect` again to re-scan
- Update `form_schema.last_verified` timestamp

### "CAPTCHA detected"
- Expected behavior - forms flagged for manual solving
- User solves CAPTCHA, then resubmits
- Or integrate 2Captcha for auto-solving

### "Screenshot not saved"
- Check `screenshot_dir` path exists
- Verify Playwright has write permissions
- Check disk space

## Security Notes

- ✓ No credentials stored in code (use env variables)
- ✓ CV files stored locally, not sent externally
- ✓ Rate limiting prevents bot detection
- ✓ Screenshots contain PII - secure storage required
- ⚠️ TODO: Add request signing for API endpoints
- ⚠️ TODO: Add IP whitelisting

## License

Part of Core project - Palantir-inspired data platform
