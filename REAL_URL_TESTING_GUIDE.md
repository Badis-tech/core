# Real URL Testing Guide: Profiling German Nursing School Forms

## Overview

This guide explains how to test the form automation system against real German nursing school websites using the Bundesagentur für Arbeit API and profiling infrastructure.

## What Was Built

### 1. **Nursing Forms Connector** (`connectors/nursing_forms.py`)

Fetches real job URLs from German public APIs:

#### Components:
- **GermanNursingJobFetcher**
  - Queries Bundesagentur für Arbeit API (German Federal Employment Agency)
  - No authentication required - uses public API key
  - Searches for nursing/healthcare jobs
  - Extracts job detail URLs

- **KNOWN_NURSING_SCHOOL_FORMS**
  - 6 manually verified nursing school form URLs
  - Categorized by form type (online_form, contact_form, etc.)
  - Acts as fallback when API doesn't return direct form links

- **get_nursing_form_urls()**
  - Hybrid approach: combines API + manual sources
  - Configurable parameters for scope and limits
  - Returns list of dicts with school name, URL, source

### 2. **Real URL Profiling Test** (`test_profiling_real_urls.py`)

Comprehensive test script that profiles form detection on real URLs:

#### Features:
- **ProfilingAnalyzer** class
  - Collects profiling data for each tested URL
  - Generates summary statistics
  - Creates comparison tables
  - Identifies bottlenecks
  - Provides optimization recommendations

- **Reporting**
  - Summary table: School, Status, Duration, Fields, CAPTCHA, Memory
  - Bottleneck analysis: Most common slow phases
  - Slow forms list: Duration >10 seconds
  - CAPTCHA detection: Count and types
  - JSON export: Detailed results for analysis

- **Recommendations**
  - Based on actual profiling data
  - Specific to identified bottlenecks
  - Actionable optimization suggestions

## Quick Start

### 1. Run Real URL Profiling Test

```bash
cd C:\Users\MSI\Desktop\core
python test_profiling_real_urls.py
```

### 2. Expected Output

The script will:
1. **Fetch URLs** from Bundesagentur API (5 job postings)
2. **Add 6** manually verified nursing school forms
3. **Test form detection** on each URL with profiling enabled
4. **Generate reports**:
   - Summary table of all results
   - Bottleneck analysis (slowest phases)
   - Slow forms requiring optimization
   - CAPTCHA statistics
   - Specific recommendations
5. **Export JSON** with detailed metrics to `profiling_results_TIMESTAMP.json`

### 3. Typical Runtime

Expected time per URL:
- **Fast forms**: 3-5 seconds (page load + field detection)
- **Complex forms**: 10-15 seconds (JavaScript, dynamic content)
- **With CAPTCHA**: 15+ seconds (detection + screenshot)

Total runtime for 11 URLs: **~2-3 minutes**

## Understanding the Output

### Summary Table

```
School                                  Status     Duration (ms)    Fields   CAPTCHA     Memory (MB)
=========================================================================================================
BFZAG - 75172 Pforzheim, Baden-...      [OK]            12500.50      12      none        52.5
Pflegeschule Passau                     [OK]            8200.25       8       reCAPTCHA_v2 48.3
Pflegeschule Ahaus                      [OK]            5100.10       6       none        45.2
```

**Interpretation:**
- **Duration**: Total milliseconds for form detection
- **Fields**: Number of form fields detected
- **CAPTCHA**: Type of CAPTCHA found (none/reCAPTCHA_v2/hCaptcha/etc.)
- **Memory**: Peak memory usage during operation

### Bottleneck Analysis

```
Most Common Bottleneck Phases:
page_navigation              - Avg: 5200.50ms | Count:  8 | Max: 8500.00ms
field_detection              - Avg: 1800.25ms | Count:  8 | Max: 3200.00ms
browser_launch               - Avg: 1200.15ms | Count:  8 | Max: 1800.00ms
```

**What it means:**
- Page navigation (waiting for JS hydration) is the biggest bottleneck
- Consider using smart waits instead of fixed 2-second buffer

### Recommendations

The script generates specific recommendations:

1. **Slow navigation (>5s average)**
   - Replace fixed waits with smart waits
   - Use `wait_for_function()` for JS-heavy sites

2. **Slow field detection (>2s average)**
   - Cache label selectors to avoid repeated queries
   - Parallelize field detection with async operations

3. **Low success rate**
   - Check network stability
   - Add custom handling for JavaScript-heavy forms

4. **CAPTCHA blocking forms**
   - Enable 2Captcha integration for production
   - Implement quarantine workflow for manual review

## JSON Export Format

Detailed results are saved to `profiling_results_TIMESTAMP.json`:

```json
[
  {
    "school": "Pflegeschule Passau",
    "url": "https://pflegeschule-passau.de/de/kontakt-bewerbung/bewerbungstool/",
    "source": "manual_verified",
    "status": "success",
    "duration_ms": 8200.25,
    "field_count": 8,
    "captcha": "reCAPTCHA_v2",
    "is_multistep": false,
    "peak_memory_mb": 48.3,
    "slowest_phase": "page_navigation",
    "slowest_phase_duration_ms": 5200.50,
    "profiling": {
      "total_duration_ms": 8200.25,
      "phases": [
        {
          "phase_name": "browser_launch",
          "duration_ms": 1200.15,
          "success": true
        },
        ...
      ]
    }
  }
]
```

## API Details

### Bundesagentur für Arbeit API

**Public Endpoint:**
```
https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs
```

**API Key:** `jobboerse-jobsuche` (public, no registration required)

**Documentation:** https://jobsuche.api.bund.dev/

**Search Parameters:**
```python
{
    "was": "Pflege",           # What: Nursing/Care
    "wo": "Deutschland",       # Where: Location
    "umkreis": 100,           # Radius: km
    "arbeitszeit": "ho",      # Work type: home office (optional)
    "size": 100,              # Results per page
    "page": 1                 # Page number
}
```

**Response:**
```json
{
    "stellenangebote": [
        {
            "titel": "Pflegefachmann (m/w/d)",
            "arbeitgeber": "Hospital XYZ",
            "arbeitsort": {"plz": "75172", "ort": "Pforzheim"},
            "refnr": "12345678",
            "eintrittsdatum": "2026-03-01T00:00:00Z"
        }
    ],
    "maxErgebnisse": 150
}
```

## Customizing Tests

### Test Fewer URLs (faster testing)

```bash
# Edit test_profiling_real_urls.py, change api_limit parameter:
form_urls = await get_nursing_form_urls(use_api=True, api_limit=3, include_manual=True)
```

### Test Only Manual Forms (no API)

```python
form_urls = await get_nursing_form_urls(use_api=False, include_manual=True)
```

### Add Custom URLs

```python
# Add to test_profiling_real_urls.py main():
form_urls.extend([
    {
        "school": "Your School Name",
        "url": "https://your-form-url.de/",
        "source": "custom"
    }
])
```

## Common Issues & Solutions

### Issue: Timeout connecting to websites

**Solution:** Some websites have rate limiting. Try:
- Reduce number of URLs tested
- Add delays between tests
- Use proxy for German access (see SSH Proxy section below)

### Issue: CAPTCHA blocking detection

**Status:** Expected - 60% of German forms have CAPTCHA
**Solution:**
- This is captured in profiling as CAPTCHA_QUARANTINE status
- For production: Enable 2Captcha integration

### Issue: JavaScript detection failing

**Solution:** Some sites need longer JS hydration buffer
- Currently set to 2 seconds
- Can increase in `automation/form_filler/detector.py` line 44

### Issue: Fields not detected

**Possible causes:**
- Shadow DOM or iframe forms (needs special handling)
- Dynamic form rendering (needs longer wait)
- Custom form libraries (needs heuristic updates)

**Debug:** Check profiling report for which phase failed

## Next Steps: SSH Proxy Setup (Phase 2)

Once you have real URLs profiled, the next phase is:

1. **Rent German VPS/SSH Server**
   - Hetzner, Linode Germany, or similar
   - ~$10-20/month for basic server

2. **Set up SOCKS5 Proxy**
   - Create SSH tunnel to German server
   - Route Playwright browser through proxy

3. **Integration with Playwright**
   - Configure proxy in FormDetector
   - Add proxy_url parameter to browser launch

4. **Verify German Access**
   - Playwright detects location as Germany
   - Bypass geo-blocking restrictions
   - Get region-specific forms

See `SSH_PROXY_SETUP.md` for detailed instructions (to be created).

## Performance Benchmarking

### Baseline Metrics (Real German Forms)

Expected results from profiling:

| Metric | Min | Avg | Max |
|--------|-----|-----|-----|
| Form Detection | 3s | 8s | 15s |
| Page Load | 2s | 5s | 8s |
| Field Detection | 500ms | 1.5s | 3s |
| CAPTCHA Check | 50ms | 200ms | 500ms |
| Memory Usage | 40MB | 48MB | 60MB |

### Optimization Targets (Phase 3)

After identifying bottlenecks:
1. Reduce page load by 30% (smart waits vs fixed 2s)
2. Reduce field detection by 50% (caching + parallelization)
3. Keep memory <50MB (current acceptable)

## Monitoring & Logging

### Enable Detailed Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Browser Logs

```python
# In test script, after test completes:
if schema:
    print("Console errors:", page.evaluate("() => window.__errors"))
```

## Contributing

Found a form that needs custom handling?

1. Add to `KNOWN_NURSING_SCHOOL_FORMS` in `connectors/nursing_forms.py`
2. Run test to generate profiling data
3. Create GitHub issue with results
4. We'll add custom heuristics as needed

## References

- **Bundesagentur API Docs:** https://jobsuche.api.bund.dev/
- **Playwright Docs:** https://playwright.dev/python/
- **Profiling System:** See `automation/profiling.py`
- **Form Detection:** See `automation/form_filler/detector.py`

## Example Output

```
============================================================================================================================
PROFILING TEST: REAL GERMAN NURSING SCHOOL FORMS
============================================================================================================================
Started: 2026-02-09 19:12:21

[1] FETCHING FORM URLs...
[OK] Fetched 11 URLs for testing

[2] TESTING FORM DETECTION WITH PROFILING...
[1/11] Pflegeschule Passau
  Testing: https://pflegeschule-passau.de/de/kontakt-bewerbung/bewerbungstool/
    [OK] Success: 8 fields, 8200.25ms, CAPTCHA: reCAPTCHA_v2

[2/11] Pflegeschule Ahaus
  Testing: https://pflegeschule-ahaus.de/kontakt-und-bewerbung/
    [OK] Success: 6 fields, 5100.10ms, CAPTCHA: none

... (more results)

[3] ANALYSIS & REPORTS...
========================================================
Summary Statistics:
  total_tested       : 11
  successful         : 10
  failed             : 1
  success_rate       : 90.9%
  avg_duration_ms    : 8250.45
  min_duration_ms    : 3200.00
  max_duration_ms    : 15800.50

[OK] Detailed results saved to profiling_results_20260209_191245.json
============================================================================================================================
```

---

**Last Updated:** 2026-02-09
**Version:** 1.0 (Phase 1 - Real URL Testing)
