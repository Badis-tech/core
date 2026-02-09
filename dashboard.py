#!/usr/bin/env python3
"""
Interactive CLI Dashboard for Form Automation Testing
Allows clients to test the system with their own data
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.syntax import Syntax
    from rich import box
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "tabulate"])
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.syntax import Syntax
    from rich import box

from automation.form_filler import FormDetector
from connectors.nursing_forms import get_nursing_form_urls
from automation.models import Candidate

console = Console()


@dataclass
class TestSession:
    """Holds state for a testing session"""
    candidate: Optional[Candidate] = None
    form_urls: List[Dict] = None
    results: List[Dict] = None

    def __post_init__(self):
        if self.form_urls is None:
            self.form_urls = []
        if self.results is None:
            self.results = []


class CLIDashboard:
    """Interactive CLI dashboard for form automation testing"""

    def __init__(self):
        self.session = TestSession()
        self.detector = FormDetector(headless=True, enable_profiling=True)

    def clear_screen(self):
        """Clear terminal screen"""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')

    def show_header(self):
        """Display application header"""
        self.clear_screen()
        header = """
        ╔═══════════════════════════════════════════════════════════╗
        ║                                                           ║
        ║     FORM AUTOMATION SYSTEM - CLI TEST DASHBOARD           ║
        ║                                                           ║
        ║     Automated form detection & application system         ║
        ║     for German nursing school forms                       ║
        ║                                                           ║
        ╚═══════════════════════════════════════════════════════════╝
        """
        console.print(header, style="cyan")

    def show_main_menu(self):
        """Display main menu"""
        console.print("\n[bold cyan]━━ MAIN MENU ━━[/bold cyan]\n")

        status = ""
        if self.session.candidate:
            status += f"✓ Candidate: {self.session.candidate.name}\n"
        if self.session.form_urls:
            status += f"✓ Forms loaded: {len(self.session.form_urls)}\n"

        if status:
            console.print("[green]" + status + "[/green]")

        console.print("""
[bold]1.[/bold] Create/Edit Candidate Profile
[bold]2.[/bold] Scan for Available Forms
[bold]3.[/bold] Manage Form Selection
[bold]4.[/bold] Run Auto-Application (Batch)
[bold]5.[/bold] View Results & Analytics
[bold]6.[/bold] Export Report
[bold]7.[/bold] Settings
[bold]0.[/bold] Exit
        """)

    async def create_candidate(self):
        """Step 1: Create candidate profile"""
        self.show_header()
        console.print("[bold cyan]STEP 1: CREATE CANDIDATE PROFILE[/bold cyan]\n")

        name = Prompt.ask("Full name", default="Test User")
        first_name = Prompt.ask("First name (optional)", default="")
        last_name = Prompt.ask("Last name (optional)", default="")
        email = Prompt.ask("Email address", default="test@example.de")
        phone = Prompt.ask("Phone number", default="+49 123 456789")
        cv_file = Prompt.ask("CV file path", default="cv.pdf")

        languages_input = Prompt.ask("Languages (comma-separated)", default="German,English")
        languages = [l.strip() for l in languages_input.split(",")]

        certs_input = Prompt.ask("Certifications (comma-separated, optional)", default="")
        certifications = [c.strip() for c in certs_input.split(",")] if certs_input else []

        motivation = Prompt.ask("Cover letter (optional)", default="")

        self.session.candidate = Candidate(
            name=name,
            first_name=first_name or None,
            last_name=last_name or None,
            email=email,
            phone=phone,
            cv_file=cv_file,
            languages=languages,
            certifications=certifications,
            motivation=motivation or None
        )

        console.print("\n[green bold]✓ Candidate profile created![/green bold]")
        self._show_candidate_summary()

        Prompt.ask("\nPress Enter to continue")

    def _show_candidate_summary(self):
        """Display candidate profile summary"""
        if not self.session.candidate:
            return

        table = Table(title="Candidate Profile", box=box.ROUNDED)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")

        c = self.session.candidate
        table.add_row("Name", c.name)
        table.add_row("Email", c.email)
        table.add_row("Phone", c.phone)
        table.add_row("CV File", c.cv_file)
        table.add_row("Languages", ", ".join(c.languages))
        if c.certifications:
            table.add_row("Certifications", ", ".join(c.certifications))

        console.print(table)

    async def scan_forms(self):
        """Step 2: Scan for available forms"""
        self.show_header()
        console.print("[bold cyan]STEP 2: SCAN FOR AVAILABLE FORMS[/bold cyan]\n")

        console.print("Choose form source:\n")
        console.print("[bold]1.[/bold] German API + Manual (Recommended)")
        console.print("[bold]2.[/bold] Manual verified forms only")
        console.print("[bold]3.[/bold] Enter custom URL")

        choice = Prompt.ask("Select option", choices=["1", "2", "3"])

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Scanning for forms...", total=None)

            if choice == "1":
                self.session.form_urls = await get_nursing_form_urls(
                    use_api=True,
                    api_limit=5,
                    include_manual=True
                )
            elif choice == "2":
                self.session.form_urls = await get_nursing_form_urls(
                    use_api=False,
                    include_manual=True
                )
            else:
                url = Prompt.ask("Enter URL")
                self.session.form_urls = [{"school": "Custom URL", "url": url, "source": "custom"}]

        console.print(f"\n[green bold]✓ Found {len(self.session.form_urls)} forms![/green bold]\n")
        self._show_forms_table()

        Prompt.ask("\nPress Enter to continue")

    def _show_forms_table(self):
        """Display available forms in table"""
        if not self.session.form_urls:
            console.print("[yellow]No forms loaded[/yellow]")
            return

        table = Table(title="Available Forms", box=box.ROUNDED)
        table.add_column("#", style="cyan", width=3)
        table.add_column("School Name", style="white")
        table.add_column("Source", style="magenta")

        for i, form in enumerate(self.session.form_urls[:15], 1):
            table.add_row(
                str(i),
                form.get("school", "Unknown")[:50],
                form.get("source", "unknown")
            )

        if len(self.session.form_urls) > 15:
            table.add_row("...", f"+{len(self.session.form_urls)-15} more forms", "")

        console.print(table)

    def manage_form_selection(self):
        """Step 3: Manage which forms to apply for"""
        self.show_header()
        console.print("[bold cyan]STEP 3: MANAGE FORM SELECTION[/bold cyan]\n")

        if not self.session.form_urls:
            console.print("[yellow]No forms loaded. Please scan for forms first.[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        self._show_forms_table()

        console.print("\nOptions:\n")
        console.print("[bold]1.[/bold] Apply to all forms")
        console.print("[bold]2.[/bold] Select specific forms by number")
        console.print("[bold]3.[/bold] Limit to first N forms")

        choice = Prompt.ask("Select option", choices=["1", "2", "3"])

        if choice == "1":
            # Keep all forms
            console.print(f"\n[green]✓ Will apply to all {len(self.session.form_urls)} forms[/green]")
        elif choice == "2":
            selected = Prompt.ask("Enter form numbers (e.g., 1,3,5)")
            try:
                indices = [int(x.strip()) - 1 for x in selected.split(",")]
                self.session.form_urls = [self.session.form_urls[i] for i in indices if 0 <= i < len(self.session.form_urls)]
                console.print(f"\n[green]✓ Selected {len(self.session.form_urls)} forms[/green]")
            except (ValueError, IndexError):
                console.print("[red]Invalid selection[/red]")
        elif choice == "3":
            limit = int(Prompt.ask("Apply to first N forms", default="5"))
            self.session.form_urls = self.session.form_urls[:limit]
            console.print(f"\n[green]✓ Limited to {len(self.session.form_urls)} forms[/green]")

        Prompt.ask("\nPress Enter to continue")

    async def run_batch_application(self):
        """Step 4: Run batch application process"""
        if not self.session.candidate:
            console.print("[red]Error: Please create a candidate profile first[/red]")
            Prompt.ask("\nPress Enter to continue")
            return

        if not self.session.form_urls:
            console.print("[red]Error: Please load forms first[/red]")
            Prompt.ask("\nPress Enter to continue")
            return

        self.show_header()
        console.print("[bold cyan]STEP 4: AUTO-APPLICATION PROCESS[/bold cyan]\n")

        console.print(f"Candidate: [bold]{self.session.candidate.name}[/bold]")
        console.print(f"Forms to apply for: [bold]{len(self.session.form_urls)}[/bold]\n")

        if not Confirm.ask("Start batch application?"):
            return

        self.session.results = []

        with Progress(
            SpinnerColumn(),
            BarColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            expand=True
        ) as progress:
            task = progress.add_task("Scanning forms...", total=len(self.session.form_urls))

            for i, form_info in enumerate(self.session.form_urls, 1):
                progress.update(task, description=f"[cyan]Processing {i}/{len(self.session.form_urls)}: {form_info['school'][:40]}...")

                try:
                    # Detect form
                    schema, profiling = await self.detector.detect_form(form_info["url"])

                    result = {
                        "school": form_info["school"],
                        "url": form_info["url"],
                        "status": "success",
                        "field_count": len(schema.fields) if schema else 0,
                        "captcha": str(schema.captcha_type) if schema else "unknown",
                        "duration_ms": profiling.total_duration_ms if profiling else 0,
                        "memory_mb": profiling.peak_memory_mb if profiling else 0,
                    }
                except Exception as e:
                    result = {
                        "school": form_info["school"],
                        "url": form_info["url"],
                        "status": "failed",
                        "error": str(e)[:100],
                        "field_count": 0,
                        "captcha": "unknown",
                        "duration_ms": 0,
                        "memory_mb": 0,
                    }

                self.session.results.append(result)
                progress.update(task, advance=1)

        console.print("\n[green bold]✓ Batch processing complete![/green bold]")
        self._show_results_summary()

        Prompt.ask("\nPress Enter to continue")

    def _show_results_summary(self):
        """Display results summary"""
        if not self.session.results:
            console.print("[yellow]No results to display[/yellow]")
            return

        successful = [r for r in self.session.results if r["status"] == "success"]
        failed = [r for r in self.session.results if r["status"] == "failed"]

        # Summary stats
        console.print("\n[bold cyan]SUMMARY STATISTICS[/bold cyan]\n")

        stats_table = Table(box=box.ROUNDED)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="white")

        stats_table.add_row("Total Forms Processed", str(len(self.session.results)))
        stats_table.add_row("Successful", f"[green]{len(successful)}[/green]")
        stats_table.add_row("Failed", f"[red]{len(failed)}[/red]")

        success_rate = (len(successful) / len(self.session.results) * 100) if self.session.results else 0
        stats_table.add_row("Success Rate", f"{success_rate:.1f}%")

        if successful:
            durations = [r["duration_ms"] for r in successful if r.get("duration_ms")]
            if durations:
                avg_duration = sum(durations) / len(durations)
                min_duration = min(durations)
                max_duration = max(durations)
                stats_table.add_row("Avg Time per Form", f"{avg_duration:.1f}ms")
                stats_table.add_row("Min Time", f"{min_duration:.1f}ms")
                stats_table.add_row("Max Time", f"{max_duration:.1f}ms")

                memories = [r["memory_mb"] for r in successful if r.get("memory_mb")]
                if memories:
                    avg_memory = sum(memories) / len(memories)
                    stats_table.add_row("Avg Memory", f"{avg_memory:.1f}MB")

        console.print(stats_table)

        # Results table
        console.print("\n[bold cyan]DETAILED RESULTS[/bold cyan]\n")

        results_table = Table(box=box.ROUNDED)
        results_table.add_column("#", style="cyan", width=3)
        results_table.add_column("School", style="white")
        results_table.add_column("Status", style="white")
        results_table.add_column("Fields", style="magenta")
        results_table.add_column("CAPTCHA", style="yellow")
        results_table.add_column("Time (ms)", style="green")

        for i, result in enumerate(self.session.results, 1):
            status_icon = "✓" if result["status"] == "success" else "✗"
            status_color = "green" if result["status"] == "success" else "red"

            results_table.add_row(
                str(i),
                result["school"][:30],
                f"[{status_color}]{status_icon}[/{status_color}]",
                str(result.get("field_count", "0")),
                result.get("captcha", "unknown")[:15],
                f"{result.get('duration_ms', 0):.0f}"
            )

        console.print(results_table)

        # Bottleneck analysis
        if successful:
            console.print("\n[bold cyan]PERFORMANCE INSIGHTS[/bold cyan]\n")

            avg_duration = sum(r["duration_ms"] for r in successful) / len(successful)
            slowest = max(successful, key=lambda r: r.get("duration_ms", 0))
            fastest = min(successful, key=lambda r: r.get("duration_ms", float("inf")))

            insight = f"""
[cyan]Slowest Form:[/cyan] {slowest['school'][:40]} ({slowest.get('duration_ms', 0):.1f}ms)
[cyan]Fastest Form:[/cyan] {fastest['school'][:40]} ({fastest.get('duration_ms', 0):.1f}ms)
[cyan]Average Time:[/cyan] {avg_duration:.1f}ms per form

[yellow]Recommendation:[/yellow]
"""

            if avg_duration > 30000:
                insight += "Forms are taking >30s. Consider optimizing page navigation or checking network."
            elif avg_duration > 15000:
                insight += "Average performance is good (~15s). Monitor for outliers."
            else:
                insight += "Excellent performance! All forms completed quickly."

            console.print(insight)

    def view_results(self):
        """Step 5: View detailed results"""
        self.show_header()
        console.print("[bold cyan]STEP 5: VIEW RESULTS & ANALYTICS[/bold cyan]\n")

        if not self.session.results:
            console.print("[yellow]No results available. Please run batch application first.[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        self._show_results_summary()
        Prompt.ask("\nPress Enter to continue")

    def export_report(self):
        """Step 6: Export results to file"""
        self.show_header()
        console.print("[bold cyan]STEP 6: EXPORT REPORT[/bold cyan]\n")

        if not self.session.results:
            console.print("[yellow]No results to export[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        console.print("\nExport formats:\n")
        console.print("[bold]1.[/bold] JSON (full data)")
        console.print("[bold]2.[/bold] CSV (spreadsheet)")
        console.print("[bold]3.[/bold] HTML (formatted report)")

        choice = Prompt.ask("Select format", choices=["1", "2", "3"])

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if choice == "1":
            filename = f"form_automation_report_{timestamp}.json"
            with open(filename, "w") as f:
                json.dump(self.session.results, f, indent=2, default=str)
            console.print(f"\n[green]✓ Report exported to {filename}[/green]")

        elif choice == "2":
            filename = f"form_automation_report_{timestamp}.csv"
            import csv
            with open(filename, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.session.results[0].keys())
                writer.writeheader()
                writer.writerows(self.session.results)
            console.print(f"\n[green]✓ Report exported to {filename}[/green]")

        elif choice == "3":
            filename = f"form_automation_report_{timestamp}.html"
            html = self._generate_html_report()
            with open(filename, "w") as f:
                f.write(html)
            console.print(f"\n[green]✓ Report exported to {filename}[/green]")

        Prompt.ask("\nPress Enter to continue")

    def _generate_html_report(self) -> str:
        """Generate HTML report"""
        successful = [r for r in self.session.results if r["status"] == "success"]
        failed = [r for r in self.session.results if r["status"] == "failed"]

        rows_html = ""
        for result in self.session.results:
            status = "✓ SUCCESS" if result["status"] == "success" else "✗ FAILED"
            rows_html += f"""
            <tr>
                <td>{result['school']}</td>
                <td>{status}</td>
                <td>{result.get('field_count', 0)}</td>
                <td>{result.get('duration_ms', 0):.0f}</td>
                <td>{result.get('memory_mb', 0):.1f}</td>
            </tr>
            """

        success_rate = (len(successful) / len(self.session.results) * 100) if self.session.results else 0

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Form Automation Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ background: white; padding: 20px; border-radius: 8px; max-width: 1200px; margin: 0 auto; }}
                h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
                h2 {{ color: #555; margin-top: 30px; }}
                .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
                .stat-box {{ background: #f9f9f9; padding: 15px; border-radius: 5px; border-left: 4px solid #007bff; }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
                .stat-label {{ font-size: 12px; color: #666; margin-top: 5px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th {{ background: #007bff; color: white; padding: 12px; text-align: left; }}
                td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
                tr:hover {{ background: #f9f9f9; }}
                .success {{ color: green; }}
                .failed {{ color: red; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Form Automation Test Report</h1>
                <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

                <h2>Summary Statistics</h2>
                <div class="stats">
                    <div class="stat-box">
                        <div class="stat-value">{len(self.session.results)}</div>
                        <div class="stat-label">Total Forms</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" style="color: green;">{len(successful)}</div>
                        <div class="stat-label">Successful</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value" style="color: red;">{len(failed)}</div>
                        <div class="stat-label">Failed</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-value">{success_rate:.1f}%</div>
                        <div class="stat-label">Success Rate</div>
                    </div>
                </div>

                <h2>Detailed Results</h2>
                <table>
                    <thead>
                        <tr>
                            <th>School Name</th>
                            <th>Status</th>
                            <th>Fields Detected</th>
                            <th>Time (ms)</th>
                            <th>Memory (MB)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>

                <div class="footer">
                    <p>Report generated by Form Automation System CLI Dashboard</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def settings(self):
        """Settings menu"""
        self.show_header()
        console.print("[bold cyan]SETTINGS[/bold cyan]\n")

        console.print("""
[bold]1.[/bold] Browser Settings (headless, timeout, etc)
[bold]2.[/bold] Profiling Settings
[bold]3.[/bold] Form Source Settings
[bold]0.[/bold] Back to main menu
        """)

        choice = Prompt.ask("Select option", choices=["1", "2", "3", "0"])

        if choice == "0":
            return

        console.print("\n[yellow]Settings configuration coming in next version[/yellow]")
        Prompt.ask("\nPress Enter to continue")

    async def run(self):
        """Main event loop"""
        while True:
            self.show_header()
            self.show_main_menu()

            choice = Prompt.ask("Select option", choices=["0", "1", "2", "3", "4", "5", "6", "7"])

            if choice == "0":
                console.print("\n[yellow]Goodbye![/yellow]\n")
                break
            elif choice == "1":
                await self.create_candidate()
            elif choice == "2":
                await self.scan_forms()
            elif choice == "3":
                self.manage_form_selection()
            elif choice == "4":
                await self.run_batch_application()
            elif choice == "5":
                self.view_results()
            elif choice == "6":
                self.export_report()
            elif choice == "7":
                self.settings()


async def main():
    """Entry point"""
    dashboard = CLIDashboard()
    await dashboard.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
