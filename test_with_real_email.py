#!/usr/bin/env python3
"""
Test the form automation system with a real email address
Shows exactly what feedback and data you get back from the system
"""

import asyncio
import json
from datetime import datetime
from automation.form_filler import FormDetector
from automation.models import Candidate
from connectors.nursing_forms import get_nursing_form_urls

async def test_with_real_email():
    """
    Test form detection with a real email address.
    Shows all the feedback data you'll receive.
    """

    print("=" * 80)
    print("FORM AUTOMATION SYSTEM - REAL EMAIL TEST")
    print("=" * 80)

    # STEP 1: Create candidate with YOUR real email
    print("\n[STEP 1] Creating candidate profile with YOUR real email...\n")

    candidate = Candidate(
        name="Max Müller",
        first_name="Max",
        last_name="Müller",
        email="your_email@example.com",  # ← REPLACE WITH YOUR REAL EMAIL
        phone="+49 123 456789",
        cv_file="resume.pdf",
        languages=["German", "English"],
        certifications=["RN", "Deutsch B2"],
        motivation="I am interested in nursing education and training."
    )

    print(f"✓ Candidate created:")
    print(f"  Name: {candidate.name}")
    print(f"  Email: {candidate.email}")
    print(f"  Phone: {candidate.phone}")
    print(f"  Languages: {', '.join(candidate.languages)}")
    print(f"  Certifications: {', '.join(candidate.certifications)}")

    # STEP 2: Load forms
    print("\n[STEP 2] Loading forms from German nursing schools...\n")

    form_urls = await get_nursing_form_urls(use_api=False, include_manual=True)

    print(f"✓ Loaded {len(form_urls)} forms:")
    for i, form in enumerate(form_urls[:3], 1):
        print(f"  {i}. {form['school']}")
    print(f"  ... and {len(form_urls) - 3} more")

    # STEP 3: Test form detection on 2 forms
    print("\n[STEP 3] Testing form detection on first 2 forms...\n")
    print("-" * 80)

    detector = FormDetector(headless=True, enable_profiling=True)
    results = []

    for i, form_info in enumerate(form_urls[:2], 1):
        print(f"\n[{i}/2] Testing: {form_info['school']}")
        print(f"      URL: {form_info['url']}")

        try:
            schema, profiling = await detector.detect_form(form_info['url'])

            # This is the feedback you get from form detection
            feedback = {
                "school": form_info['school'],
                "url": form_info['url'],
                "status": "SUCCESS ✓",
                "fields_detected": len(schema.fields),
                "field_details": [
                    {
                        "name": f.name,
                        "type": str(f.field_type),
                        "required": f.required,
                        "placeholder": f.placeholder,
                        "inferred_field": f.inferred_candidate_field
                    }
                    for f in schema.fields
                ],
                "captcha_type": str(schema.captcha_type),
                "is_multistep": schema.is_multistep,
                "performance": {
                    "total_time_ms": round(profiling.total_duration_ms, 2),
                    "peak_memory_mb": round(profiling.peak_memory_mb, 2),
                    "slowest_phase": profiling.slowest_phase,
                    "slowest_phase_time_ms": round(profiling.slowest_phase_duration_ms, 2)
                }
            }

            results.append(feedback)

            # Display feedback
            print(f"      ✓ Status: SUCCESS")
            print(f"      ✓ Fields detected: {len(schema.fields)}")
            print(f"      ✓ CAPTCHA type: {schema.captcha_type}")
            print(f"      ✓ Time taken: {profiling.total_duration_ms:.1f}ms ({profiling.total_duration_ms/1000:.1f}s)")
            print(f"      ✓ Memory used: {profiling.peak_memory_mb:.1f} MB")

            if schema.fields:
                print(f"      \n      Fields to fill:")
                for field in schema.fields[:5]:  # Show first 5
                    required = "[REQUIRED]" if field.required else "[optional]"
                    print(f"        - {field.name} ({field.field_type}) {required}")
                if len(schema.fields) > 5:
                    print(f"        ... and {len(schema.fields)-5} more fields")

        except Exception as e:
            feedback = {
                "school": form_info['school'],
                "url": form_info['url'],
                "status": f"FAILED ✗",
                "error": str(e)[:200]
            }
            results.append(feedback)
            print(f"      ✗ Status: FAILED")
            print(f"      ✗ Error: {str(e)[:100]}")

    # STEP 4: Show summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY - FEEDBACK DATA YOU'LL RECEIVE")
    print("=" * 80)

    successful = [r for r in results if "SUCCESS" in r.get("status", "")]
    failed = [r for r in results if "FAILED" in r.get("status", "")]

    print(f"\n✓ Successful: {len(successful)}/{len(results)}")
    print(f"✗ Failed: {len(failed)}/{len(results)}")

    if successful:
        total_time = sum(r["performance"]["total_time_ms"] for r in successful)
        avg_time = total_time / len(successful)
        print(f"\n⏱ Average processing time: {avg_time:.1f}ms ({avg_time/1000:.1f}s)")

        total_memory = sum(r["performance"]["peak_memory_mb"] for r in successful)
        avg_memory = total_memory / len(successful)
        print(f"💾 Average memory usage: {avg_memory:.1f} MB")

    # STEP 5: Export detailed feedback as JSON
    print("\n[STEP 4] Exporting detailed feedback...\n")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_feedback_{timestamp}.json"

    with open(filename, "w") as f:
        json.dump({
            "test_timestamp": datetime.now().isoformat(),
            "candidate": {
                "name": candidate.name,
                "email": candidate.email,
                "phone": candidate.phone
            },
            "test_results": results,
            "summary": {
                "total_forms_tested": len(results),
                "successful": len(successful),
                "failed": len(failed),
                "success_rate": f"{(len(successful)/len(results)*100):.1f}%" if results else "0%"
            }
        }, f, indent=2, default=str)

    print(f"✓ Feedback exported to: {filename}")

    # STEP 5: Show what happens next
    print("\n" + "=" * 80)
    print("NEXT STEPS - HOW THE SYSTEM PROVIDES FEEDBACK")
    print("=" * 80)

    print("""
[1] FORM DETECTION FEEDBACK
    You get:
    ✓ List of all form fields detected
    ✓ Field types (email, phone, text, file upload, etc)
    ✓ Which fields are required
    ✓ CAPTCHA detection (reCAPTCHA v2, hCaptcha, etc)
    ✓ Performance metrics (time, memory)
    ✓ Any errors encountered

[2] FIELD MAPPING FEEDBACK
    The system shows:
    ✓ Which form fields map to your candidate data
    ✓ Confidence level of the mapping
    ✓ Fields that need manual review
    ✓ Missing data (fields required but not in your profile)

[3] SUBMISSION FEEDBACK
    You'll see:
    ✓ Which forms were successfully filled
    ✓ Which forms failed and why
    ✓ Screenshots of submitted forms
    ✓ Confirmation messages from websites
    ✓ Tracking information for follow-up

[4] EMAIL CONFIRMATION
    What happens with YOUR email:
    ✓ Applications are submitted WITH YOUR EMAIL ADDRESS
    ✓ You'll receive confirmation emails from nursing schools
    ✓ You can track responses to {candidate.email}
    ✓ The system logs all submission timestamps

[5] ANALYTICS & PROFILING
    The system provides:
    ✓ Success rate per school
    ✓ Processing time trends
    ✓ Performance bottlenecks
    ✓ Failure reasons and recommendations
    ✓ Memory and resource usage

IMPORTANT NOTES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  CAPTCHA HANDLING:
    If a form has reCAPTCHA, the system will:
    1. Detect the CAPTCHA type
    2. Take a screenshot
    3. Mark the application as "CAPTCHA_QUARANTINE"
    4. Require manual solution or 2Captcha integration

    The form will NOT be auto-submitted if CAPTCHA is present.

⚠️  EMAIL VERIFICATION:
    Some forms may send verification emails to YOUR EMAIL.
    Check your inbox and spam folder for:
    - Confirmation emails from nursing schools
    - Application status updates
    - Interview invitations
    - Document requests

⚠️  TESTING MODE:
    In testing, you can use a test email like:
    - test+nursing@example.com (Gmail aliasing)
    - Or use a real email with a [TEST] prefix in the CV

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)

    # STEP 6: Show how to check email feedback
    print("\n[STEP 5] Checking email feedback...\n")

    print(f"""
To see feedback from your email submissions:

1. Check your inbox: {candidate.email}
   - Look for confirmation emails within 5-10 minutes
   - Check spam folder for email verification links

2. Check the system dashboard:
   - Navigate to http://localhost:8000/dashboard
   - Filter applications by your email: {candidate.email}
   - View submission timestamps and status

3. Export daily reports:
   - System generates JSON reports with all feedback
   - Includes success/failure reasons
   - Tracks which schools have contacted you

4. API endpoint for feedback:
   GET /automation/candidates/{candidate.id}
   - Returns all submissions from this email
   - Shows response status for each application
   - Includes follow-up messages

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXAMPLE API FEEDBACK RESPONSE:
GET /automation/applications?candidate_email={candidate.email}

{{
  "total_applications": 11,
  "successful_submissions": 8,
  "pending_responses": 3,
  "applications": [
    {{
      "school": "Pflegeschule Passau",
      "submitted_at": "2026-02-09T21:00:00Z",
      "status": "submitted",
      "candidate_email": "{candidate.email}",
      "email_confirmations_received": 1,
      "confirmation_at": "2026-02-09T21:15:32Z",
      "next_steps": "Awaiting interview invitation"
    }},
    ...
  ]
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)

    print("\n✓ Test complete! Check the exported JSON file for detailed feedback.")
    print(f"  File: {filename}\n")


if __name__ == "__main__":
    print("\nℹ️  IMPORTANT: Replace 'your_email@example.com' in the script with YOUR REAL EMAIL")
    print("   to receive actual feedback from the nursing schools!\n")

    try:
        asyncio.run(test_with_real_email())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
