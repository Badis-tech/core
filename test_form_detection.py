#!/usr/bin/env python3
"""
Quick test script for form detection with profiling
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime

from automation.models import Candidate
from automation.form_filler import FormDetector, FormFiller
from automation.profiling import format_profiling_report


async def test_detect_form():
    """Test form detection on a real URL with profiling"""
    # German nursing schools with online forms
    test_urls = [
        # TIER 1 - Direct online forms (easiest to automate)
        "https://pflegeschule-passau.de/de/kontakt-bewerbung/bewerbungstool/",
        "https://pflegeschule-ahaus.de/kontakt-und-bewerbung/",
        "https://www.pflegeschulen-medius.de/bewerbung/",
        "https://pflegeschule-em.de/bewerbung-ausbildung-oder-studium/",
        "https://www.schulen.bfz.de/pflegeberufe/pflege",

        # TIER 2 - Larger institutions (may have CAPTCHAs)
        "https://www.eh-berlin.de/en/study-programs/bachelor/bachelor-of-nursing",
    ]

    # Create detector with profiling enabled
    detector = FormDetector(headless=True, enable_profiling=True)

    profiling_results = []

    for url in test_urls:
        print(f"\n{'='*70}")
        print(f"Testing: {url}")
        print(f"{'='*70}")

        try:
            schema, profiling = await detector.detect_form(url)

            print(f"\n✓ Form detected")
            print(f"  Fields found: {len(schema.fields)}")
            print(f"  CAPTCHA: {schema.captcha_type}")
            print(f"  Multistep: {schema.is_multistep}")

            print(f"\nDetected fields:")
            for i, field in enumerate(schema.fields, 1):
                print(
                    f"  {i}. {field.name:20} | "
                    f"Type: {field.field_type:12} | "
                    f"Required: {field.required} | "
                    f"Inferred: {field.inferred_candidate_field}"
                )

            # Display profiling report
            if profiling:
                print(format_profiling_report(profiling))
                profiling_results.append({
                    "url": url,
                    "duration_ms": profiling.total_duration_ms,
                    "field_count": len(schema.fields),
                    "profiling": profiling,
                })

            # Save schema to JSON for inspection
            schema_json = Path(f"form_schema_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(schema_json, "w") as f:
                schema_data = {
                    "url": schema.url,
                    "fields": [
                        {
                            "name": f.name,
                            "type": f.field_type,
                            "required": f.required,
                            "inferred": f.inferred_candidate_field,
                            "placeholder": f.placeholder,
                            "selector": f.selector,
                        }
                        for f in schema.fields
                    ],
                    "captcha_type": schema.captcha_type,
                    "submit_selector": schema.submit_selector,
                }
                if profiling:
                    schema_data["profiling"] = profiling.dict()
                json.dump(schema_data, f, indent=2, default=str)

            print(f"\n✓ Schema saved to {schema_json}")

        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback

            traceback.print_exc()

    # Summary comparison
    if profiling_results:
        print(f"\n\n{'='*70}")
        print("PROFILING SUMMARY")
        print(f"{'='*70}")
        print(f"{'URL':<50} {'Duration (ms)':<15}")
        print("-" * 70)
        for result in sorted(profiling_results, key=lambda x: x["duration_ms"], reverse=True):
            print(f"{result['url'][:50]:<50} {result['duration_ms']:>10.2f} ms")


async def test_fill_form():
    """Test form filling with a candidate"""
    # Create test candidate
    candidate = Candidate(
        id="test-candidate",
        name="John Doe",
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        phone="+49123456789",
        cv_file="/path/to/cv.pdf",  # Replace with real path
        certifications=["RN", "Deutsch B2"],
        languages=["English", "German"],
        motivation="Motivated to work in Germany",
    )

    print(f"\n{'='*60}")
    print("Test Candidate:")
    print(f"{'='*60}")
    print(f"  Name: {candidate.name}")
    print(f"  Email: {candidate.email}")
    print(f"  Phone: {candidate.phone}")
    print(f"  Certifications: {', '.join(candidate.certifications)}")
    print(f"  Languages: {', '.join(candidate.languages)}")


async def main():
    """Run tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║  Form Detection & Filling Test Suite                    ║")
    print("╚" + "=" * 58 + "╝")

    print("\n[1] Testing form detection...")
    await test_detect_form()

    print("\n[2] Testing candidate creation...")
    await test_fill_form()

    print("\n[✓] Test suite complete!")
    print("\nNext steps:")
    print("  1. Update test_urls with real German nursing school forms")
    print("  2. Run this script to detect forms")
    print("  3. Review form_schema.json")
    print("  4. Use API endpoints to fill and submit")


if __name__ == "__main__":
    asyncio.run(main())
