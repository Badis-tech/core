#!/usr/bin/env python3
"""
Test form detection and profiling against real German nursing school URLs

This script:
1. Fetches URLs from the Bundesagentur für Arbeit API
2. Adds manually verified nursing school form URLs
3. Tests form detection with profiling enabled
4. Generates comparison reports
5. Identifies bottlenecks and optimization opportunities
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from connectors.nursing_forms import get_nursing_form_urls
from automation.form_filler import FormDetector
from automation.profiling import format_profiling_report


class ProfilingAnalyzer:
    """Analyze and compare profiling data across multiple forms"""

    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def add_result(self, school: str, url: str, schema, profiling, source: str):
        """Add a test result"""
        if profiling:
            self.results.append({
                "school": school,
                "url": url,
                "source": source,
                "status": "success",
                "duration_ms": profiling.total_duration_ms,
                "field_count": len(schema.fields) if schema else 0,
                "captcha": schema.captcha_type if schema else None,
                "is_multistep": schema.is_multistep if schema else None,
                "peak_memory_mb": profiling.peak_memory_mb,
                "slowest_phase": profiling.slowest_phase,
                "slowest_phase_duration_ms": profiling.slowest_phase_duration_ms,
                "profiling": profiling,
                "schema": schema,
            })

    def add_error(self, school: str, url: str, error: str, source: str):
        """Add an error result"""
        self.results.append({
            "school": school,
            "url": url,
            "source": source,
            "status": "error",
            "error": error,
        })

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        successful = [r for r in self.results if r["status"] == "success"]
        failed = [r for r in self.results if r["status"] == "error"]

        if not successful:
            return {
                "total_tested": len(self.results),
                "successful": 0,
                "failed": len(failed),
                "success_rate": 0,
            }

        durations = [r["duration_ms"] for r in successful]
        memory_usage = [r["peak_memory_mb"] for r in successful if r.get("peak_memory_mb")]

        return {
            "total_tested": len(self.results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": f"{(len(successful) / len(self.results) * 100):.1f}%",
            "avg_duration_ms": f"{sum(durations) / len(durations):.2f}",
            "min_duration_ms": f"{min(durations):.2f}",
            "max_duration_ms": f"{max(durations):.2f}",
            "avg_memory_mb": f"{sum(memory_usage) / len(memory_usage):.2f}" if memory_usage else "N/A",
        }

    def print_summary_table(self):
        """Print a summary table of all results"""
        if not self.results:
            print("No results to display")
            return

        print("\n" + "=" * 120)
        print("PROFILING RESULTS SUMMARY")
        print("=" * 120)
        print(
            f"{'School':<40} {'Status':<10} {'Duration (ms)':<15} "
            f"{'Fields':<8} {'CAPTCHA':<12} {'Memory (MB)':<12}"
        )
        print("-" * 120)

        for result in sorted(
            self.results,
            key=lambda x: x.get("duration_ms", 999999),
            reverse=True
        ):
            school = result["school"][:40]
            status = result["status"]
            duration = f"{result.get('duration_ms', 'N/A'):.2f}" if result.get("duration_ms") else "ERROR"
            fields = result.get("field_count", "N/A")
            captcha = result.get("captcha", "N/A")
            memory = f"{result.get('peak_memory_mb', 'N/A'):.1f}" if result.get("peak_memory_mb") else "N/A"

            status_icon = "[OK]" if status == "success" else "[FAIL]"
            print(
                f"{school:<40} {status_icon:<10} {duration:<15} "
                f"{fields:<8} {str(captcha):<12} {memory:<12}"
            )

        print("=" * 120)

    def print_bottleneck_analysis(self):
        """Identify and display bottleneck patterns"""
        if not self.results:
            return

        print("\n" + "=" * 120)
        print("BOTTLENECK ANALYSIS")
        print("=" * 120)

        successful = [r for r in self.results if r["status"] == "success"]
        if not successful:
            print("No successful results to analyze")
            return

        # Group by slowest phase
        phase_times = {}
        for result in successful:
            if slowest := result.get("slowest_phase"):
                if slowest not in phase_times:
                    phase_times[slowest] = []
                phase_times[slowest].append(result.get("slowest_phase_duration_ms", 0))

        print("\nMost Common Bottleneck Phases:")
        print("-" * 120)
        for phase, times in sorted(phase_times.items(), key=lambda x: sum(x[1]) / len(x[1]), reverse=True):
            avg_time = sum(times) / len(times)
            print(f"  {phase:<35} - Avg: {avg_time:>8.2f}ms | Count: {len(times):>3} | "
                  f"Max: {max(times):>8.2f}ms")

        # Identify slow forms
        print("\nSlowest Forms (>10 seconds):")
        print("-" * 120)
        slow_forms = [r for r in successful if r["duration_ms"] > 10000]
        for result in sorted(slow_forms, key=lambda x: x["duration_ms"], reverse=True):
            print(f"  {result['school']:<40} - {result['duration_ms']:>8.2f}ms "
                  f"(Bottleneck: {result['slowest_phase']})")

        # CAPTCHA analysis
        captcha_forms = [r for r in successful if r.get("captcha") and r["captcha"] != "none"]
        if captcha_forms:
            print(f"\nForms with CAPTCHA: {len(captcha_forms)} out of {len(successful)}")
            print("-" * 120)
            for result in captcha_forms[:5]:
                print(f"  {result['school']:<40} - {result['captcha']}")

    def print_recommendations(self):
        """Print optimization recommendations based on profiling data"""
        print("\n" + "=" * 120)
        print("OPTIMIZATION RECOMMENDATIONS")
        print("=" * 120)

        successful = [r for r in self.results if r["status"] == "success"]
        if not successful:
            print("Not enough data for recommendations")
            return

        recommendations = []

        # Check for common slow phases
        page_nav_times = []
        field_detect_times = []
        browser_launch_times = []

        for result in successful:
            profiling = result.get("profiling")
            if profiling:
                for phase in profiling.phases:
                    if "page_navigation" in phase.phase_name:
                        page_nav_times.append(phase.duration_ms)
                    elif "field_detection" in phase.phase_name:
                        field_detect_times.append(phase.duration_ms)
                    elif "browser_launch" in phase.phase_name:
                        browser_launch_times.append(phase.duration_ms)

        if page_nav_times and sum(page_nav_times) / len(page_nav_times) > 5000:
            recommendations.append(
                "Page navigation is slow (>5s avg). Consider:\n"
                "    - Implementing smart waits instead of fixed 2s buffer\n"
                "    - Using wait_for_function for JS-heavy sites"
            )

        if field_detect_times and sum(field_detect_times) / len(field_detect_times) > 2000:
            recommendations.append(
                "Field detection is slow (>2s avg). Consider:\n"
                "    - Caching label selectors to avoid repeated queries\n"
                "    - Parallelizing field detection with Promise.all"
            )

        if len(successful) < len(self.results) * 0.8:
            recommendations.append(
                f"Form detection success rate is low ({self.get_summary()['success_rate']}). Consider:\n"
                "    - Checking network conditions and site stability\n"
                "    - Adding custom handling for JavaScript-heavy forms"
            )

        captcha_count = len([r for r in successful if r.get("captcha") and r["captcha"] != "none"])
        if captcha_count > 0:
            recommendations.append(
                f"{captcha_count} forms have CAPTCHA. Consider:\n"
                "    - Enabling 2Captcha integration for production\n"
                "    - Implementing CAPTCHA quarantine workflow for manual review"
            )

        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"\n{i}. {rec}")
        else:
            print("\nNo optimization opportunities identified. System is performing well!")

    def save_results(self, filename: str = "profiling_results.json"):
        """Save detailed results to JSON"""
        export_data = []
        for result in self.results:
            export_result = {k: v for k, v in result.items() if k not in ["profiling", "schema"]}
            if result.get("profiling"):
                export_result["profiling"] = result["profiling"].dict()
            export_data.append(export_result)

        with open(filename, "w") as f:
            json.dump(export_data, f, indent=2, default=str)
        print(f"\n[OK] Detailed results saved to {filename}")


async def test_url(url: str, detector: FormDetector, analyzer: ProfilingAnalyzer, school: str, source: str):
    """Test a single URL"""
    print(f"\n  Testing: {url[:70]}")
    try:
        schema, profiling = await detector.detect_form(url)
        if schema:
            analyzer.add_result(school, url, schema, profiling, source)
            if profiling:
                print(
                    f"    [OK] Success: {len(schema.fields)} fields, "
                    f"{profiling.total_duration_ms:.2f}ms, "
                    f"CAPTCHA: {schema.captcha_type}"
                )
        else:
            analyzer.add_error(school, url, "No schema returned", source)
            print("    [FAIL] Error: No schema returned")
    except Exception as e:
        analyzer.add_error(school, url, str(e), source)
        print(f"    [FAIL] Error: {str(e)[:60]}")


async def main():
    """Main test function"""
    print("\n" + "=" * 120)
    print("PROFILING TEST: REAL GERMAN NURSING SCHOOL FORMS")
    print("=" * 120)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Fetch URLs
    print("\n[1] FETCHING FORM URLs...")
    print("-" * 120)
    form_urls = await get_nursing_form_urls(use_api=True, api_limit=5, include_manual=True)
    print(f"\n[OK] Fetched {len(form_urls)} URLs for testing")

    # Test forms with profiling
    print("\n[2] TESTING FORM DETECTION WITH PROFILING...")
    print("-" * 120)
    detector = FormDetector(headless=True, enable_profiling=True)
    analyzer = ProfilingAnalyzer()

    for i, form_info in enumerate(form_urls, 1):
        print(f"\n[{i}/{len(form_urls)}] {form_info['school']}")
        await test_url(
            form_info["url"],
            detector,
            analyzer,
            form_info["school"],
            form_info.get("source", "unknown")
        )

    # Generate reports
    print("\n[3] ANALYSIS & REPORTS...")
    print("-" * 120)

    analyzer.print_summary_table()
    print("\nSummary Statistics:")
    for key, value in analyzer.get_summary().items():
        print(f"  {key:<20}: {value}")

    analyzer.print_bottleneck_analysis()
    analyzer.print_recommendations()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    analyzer.save_results(f"profiling_results_{timestamp}.json")

    print("\n" + "=" * 120)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 120)


if __name__ == "__main__":
    asyncio.run(main())
