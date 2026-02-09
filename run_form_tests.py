#!/usr/bin/env python3
"""
Form Detection Test Runner
Tests German nursing school application forms
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

from automation.form_filler.detector import FormDetector
from automation.models import FieldType, CaptchaType


# German nursing schools to test
TEST_URLS = [
    {
        "name": "Pflegeschulen Passau",
        "url": "https://pflegeschule-passau.de/de/kontakt-bewerbung/bewerbungstool/",
        "difficulty": "EASY",
    },
    {
        "name": "Pflegeschule Ahaus",
        "url": "https://pflegeschule-ahaus.de/kontakt-und-bewerbung/",
        "difficulty": "MEDIUM",
    },
    {
        "name": "Pflegeschulen Medius",
        "url": "https://www.pflegeschulen-medius.de/bewerbung/",
        "difficulty": "EASY",
    },
    {
        "name": "Pflegeschule-EM",
        "url": "https://pflegeschule-em.de/bewerbung-ausbildung-oder-studium/",
        "difficulty": "MEDIUM",
    },
    {
        "name": "BFZ Schulen (Bayern)",
        "url": "https://www.schulen.bfz.de/pflegeberufe/pflege",
        "difficulty": "HARD",
    },
    {
        "name": "EH Berlin",
        "url": "https://www.eh-berlin.de/en/study-programs/bachelor/bachelor-of-nursing",
        "difficulty": "HARD",
    },
]


class TestRunner:
    def __init__(self, results_dir: str = "./form_detection_results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        self.detector = FormDetector(headless=True, timeout=30000)
        self.results = []

    async def test_url(self, test_case: dict) -> dict:
        """Test a single URL"""
        name = test_case["name"]
        url = test_case["url"]
        difficulty = test_case["difficulty"]

        print(f"\n{'='*70}")
        print(f"Testing: {name} [{difficulty}]")
        print(f"URL: {url}")
        print(f"{'='*70}")

        result = {
            "name": name,
            "url": url,
            "difficulty": difficulty,
            "status": "UNKNOWN",
            "fields_found": 0,
            "captcha": None,
            "error": None,
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            print("Detecting form...", end="", flush=True)
            schema = await self.detector.detect_form(url)
            print(" OK")

            result["status"] = "SUCCESS"
            result["fields_found"] = len(schema.fields)
            result["captcha"] = schema.captcha_type

            print(f"Fields found: {len(schema.fields)}")
            print(f"CAPTCHA type: {schema.captcha_type}")
            print(f"Multi-step form: {schema.is_multistep}")

            if schema.fields:
                print(f"\nDetected fields:")
                for i, field in enumerate(schema.fields, 1):
                    print(
                        f"  {i:2}. {field.name:25} | "
                        f"{str(field.field_type):12} | "
                        f"Required: {str(field.required):5} | "
                        f"Inferred: {field.inferred_candidate_field}"
                    )

                # Save detailed schema
                schema_file = self.results_dir / f"{name.replace(' ', '_')}_schema.json"
                with open(schema_file, "w") as f:
                    schema_data = {
                        "url": schema.url,
                        "detected_at": schema.detected_at.isoformat(),
                        "fields": [
                            {
                                "name": f.name,
                                "html_type": f.html_type,
                                "field_type": f.field_type,
                                "required": f.required,
                                "placeholder": f.placeholder,
                                "label_text": f.label_text,
                                "inferred_candidate_field": f.inferred_candidate_field,
                                "selector": f.selector,
                            }
                            for f in schema.fields
                        ],
                        "captcha_type": schema.captcha_type,
                        "submit_selector": schema.submit_selector,
                        "is_multistep": schema.is_multistep,
                    }
                    json.dump(schema_data, f, indent=2, default=str)

                print(f"Schema saved: {schema_file}")

        except Exception as e:
            result["status"] = "FAILED"
            result["error"] = str(e)
            print(f" FAILED")
            print(f"Error: {e}")

        self.results.append(result)
        return result

    async def run_all(self):
        """Run all tests"""
        print("\n")
        print("╔" + "=" * 68 + "╗")
        print("║  German Nursing School Form Detection Test Suite                ║")
        print("╚" + "=" * 68 + "╝")

        for test_case in TEST_URLS:
            await self.test_url(test_case)

        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*70}")
        print("TEST SUMMARY")
        print(f"{'='*70}\n")

        passed = sum(1 for r in self.results if r["status"] == "SUCCESS")
        failed = sum(1 for r in self.results if r["status"] == "FAILED")
        total = len(self.results)

        print(f"Total tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success rate: {(passed/total*100):.1f}%\n")

        print("Results by difficulty:")
        for difficulty in ["EASY", "MEDIUM", "HARD"]:
            d_results = [r for r in self.results if r["difficulty"] == difficulty]
            d_passed = sum(1 for r in d_results if r["status"] == "SUCCESS")
            if d_results:
                print(
                    f"  {difficulty:6} - {d_passed}/{len(d_results)} passed "
                    f"({d_passed/len(d_results)*100:.0f}%)"
                )

        print("\nDetailed results:")
        for result in self.results:
            status_icon = "OK" if result["status"] == "SUCCESS" else "FAIL"
            captcha_info = (
                f" [CAPTCHA: {result['captcha']}]"
                if result["captcha"] and result["captcha"] != "none"
                else ""
            )
            print(
                f"  {status_icon:4} | {result['name']:20} | "
                f"Fields: {result['fields_found']:2}{captcha_info}"
            )

        # Save results
        results_file = self.results_dir / "test_results.json"
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"\nDetailed results saved to: {results_file}")
        print(f"Individual schemas saved to: {self.results_dir}/")

        print("\nNext steps:")
        print("  1. Review test_results.json for summary")
        print("  2. Check individual schema files for field details")
        print("  3. Use successful forms to test batch submission")


async def main():
    """Run test suite"""
    runner = TestRunner()
    await runner.run_all()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
