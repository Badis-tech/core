import asyncio
import logging
from typing import List, Optional, Tuple
from playwright.async_api import async_playwright, Page, Browser

from automation.models import FormField, FormSchema, FieldType, CaptchaType
from automation.profiling import ProfilerCollector, ProfilingData

logger = logging.getLogger(__name__)


class FormDetector:
    """Detect and classify form fields on web pages"""

    FIELD_CLASSIFICATIONS = {
        "email": (FieldType.EMAIL, ["email", "mail"]),
        "phone": (FieldType.PHONE, ["phone", "mobile", "tel", "telefon"]),
        "first_name": (FieldType.FIRST_NAME, ["first", "fname", "vorname"]),
        "last_name": (FieldType.LAST_NAME, ["last", "lname", "surname", "nachname"]),
        "file": (FieldType.FILE_UPLOAD, ["file", "cv", "resume", "lebenslauf", "upload"]),
        "checkbox": (FieldType.CHECKBOX, ["checkbox"]),
        "dropdown": (FieldType.DROPDOWN, ["select"]),
    }

    def __init__(self, headless: bool = True, timeout: int = 30000, enable_profiling: bool = False):
        self.headless = headless
        self.timeout = timeout
        self.enable_profiling = enable_profiling
        self.browser: Optional[Browser] = None
        self._profiler: Optional[ProfilerCollector] = None

    async def detect_form(self, url: str) -> Tuple[FormSchema, Optional[ProfilingData]]:
        """
        Detect all form fields on a page.
        Returns tuple of (FormSchema, ProfilingData).
        """
        if self.enable_profiling:
            self._profiler = ProfilerCollector("form_detection")
            self._profiler.start()

        logger.info(f"Detecting form on {url}")

        async with async_playwright() as p:
            # Phase 1: Browser Launch
            if self._profiler:
                async with self._profiler.profile_phase("browser_launch"):
                    browser = await p.chromium.launch(headless=self.headless)
                    page = await browser.new_page()
            else:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()

            try:
                # Phase 2: Page Navigation
                if self._profiler:
                    async with self._profiler.profile_phase("page_navigation", url=url):
                        await page.goto(url, wait_until="networkidle", timeout=self.timeout)
                else:
                    await page.goto(url, wait_until="networkidle", timeout=self.timeout)

                # Phase 3: Page Stabilization
                if self._profiler:
                    async with self._profiler.profile_phase("page_stabilization"):
                        await page.wait_for_load_state("networkidle")
                        await asyncio.sleep(2)  # Buffer for hydration
                else:
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(2)

                # Phase 4: Field Detection
                if self._profiler:
                    async with self._profiler.profile_phase("field_detection"):
                        fields = await self._detect_fields(page)
                    self._profiler.metadata['field_count'] = len(fields)
                else:
                    fields = await self._detect_fields(page)

                # Phase 5: CAPTCHA Detection
                if self._profiler:
                    async with self._profiler.profile_phase("captcha_detection"):
                        captcha = await self._detect_captcha(page)
                else:
                    captcha = await self._detect_captcha(page)

                # Phase 6: Submit Button Detection
                if self._profiler:
                    async with self._profiler.profile_phase("submit_detection"):
                        submit_selector = await self._find_submit_button(page)
                else:
                    submit_selector = await self._find_submit_button(page)

                # Phase 7: Multistep Detection
                if self._profiler:
                    async with self._profiler.profile_phase("multistep_detection"):
                        is_multistep = await self._is_multistep(page)
                else:
                    is_multistep = await self._is_multistep(page)

                schema = FormSchema(
                    url=url,
                    fields=fields,
                    captcha_type=captcha,
                    submit_selector=submit_selector or "button[type='submit']",
                    is_multistep=is_multistep,
                )

                logger.info(f"Detected {len(fields)} fields on {url}")
                profiling = self._profiler.finish() if self._profiler else None
                return schema, profiling

            except Exception as e:
                logger.error(f"Error detecting form on {url}: {e}")
                raise
            finally:
                # Phase 8: Browser Cleanup
                if self._profiler:
                    async with self._profiler.profile_phase("browser_cleanup"):
                        await browser.close()
                else:
                    await browser.close()

    async def _detect_fields(self, page: Page) -> List[FormField]:
        """Find all form inputs, textareas, selects"""
        fields = []

        # Query all form elements
        selectors = ["input", "textarea", "select"]

        for selector in selectors:
            elements = await page.locator(selector).all()

            for i, elem in enumerate(elements):
                try:
                    # Skip hidden/disabled fields
                    if await elem.is_hidden() or await elem.is_disabled():
                        continue

                    html_type = await elem.get_attribute("type") or "text"
                    name = await elem.get_attribute("name")

                    if not name:  # Skip fields without names
                        continue

                    placeholder = await elem.get_attribute("placeholder")
                    required = await elem.get_attribute("required") is not None

                    # Find associated label
                    label_text = await self._get_field_label(page, name)

                    # Classify field type
                    field_type = self._classify_field(name, html_type, placeholder, label_text)

                    # Infer candidate field
                    inferred = self._infer_candidate_field(field_type, name)

                    field = FormField(
                        selector=f"{selector}[name='{name}']",
                        name=name,
                        html_type=html_type,
                        field_type=field_type,
                        required=required,
                        placeholder=placeholder,
                        label_text=label_text,
                        inferred_candidate_field=inferred,
                    )

                    fields.append(field)

                except Exception as e:
                    logger.warning(f"Error processing field {i}: {e}")
                    continue

        return fields

    async def _get_field_label(self, page: Page, field_name: str) -> Optional[str]:
        """Find label associated with field"""
        try:
            # Try label with for attribute
            label = await page.locator(f"label[for='{field_name}']").first.text_content()
            if label:
                return label.strip()

            # Try label wrapping the input
            label = await page.locator(f"label:has(input[name='{field_name}'])").first.text_content()
            if label:
                return label.strip()
        except:
            pass

        return None

    def _classify_field(self, name: str, html_type: str, placeholder: str = None, label: str = None) -> FieldType:
        """Classify field based on name, type, placeholder, label"""
        name_lower = name.lower()
        html_type_lower = html_type.lower()
        placeholder_lower = placeholder.lower() if placeholder else ""
        label_lower = label.lower() if label else ""

        # Check HTML type first
        if html_type_lower == "email":
            return FieldType.EMAIL
        if html_type_lower == "tel":
            return FieldType.PHONE
        if html_type_lower == "file":
            return FieldType.FILE_UPLOAD
        if html_type_lower == "checkbox":
            return FieldType.CHECKBOX
        if html_type_lower == "date":
            return FieldType.DATE

        # Check against heuristics
        for field_type, (classified_type, keywords) in self.FIELD_CLASSIFICATIONS.items():
            for keyword in keywords:
                if keyword in name_lower or keyword in placeholder_lower or keyword in label_lower:
                    return classified_type

        # Default classification
        if html_type_lower == "textarea":
            return FieldType.LONG_TEXT
        if html_type_lower == "select":
            return FieldType.DROPDOWN

        return FieldType.TEXT

    def _infer_candidate_field(self, field_type: FieldType, name: str) -> str:
        """Map form field to candidate attribute"""
        mapping = {
            FieldType.EMAIL: "candidate.email",
            FieldType.PHONE: "candidate.phone",
            FieldType.FIRST_NAME: "candidate.first_name",
            FieldType.LAST_NAME: "candidate.last_name",
            FieldType.FILE_UPLOAD: "candidate.cv_file",
            FieldType.LONG_TEXT: "candidate.motivation",
        }

        return mapping.get(field_type, "candidate.unknown")

    async def _detect_captcha(self, page: Page) -> CaptchaType:
        """Detect CAPTCHA type on page"""
        # reCAPTCHA v2
        if await page.locator('[data-sitekey]').count() > 0:
            return CaptchaType.RECAPTCHA_V2

        # hCaptcha
        if await page.locator('.h-captcha').count() > 0:
            return CaptchaType.HCAPTCHA

        # Cloudflare Turnstile
        if await page.locator('.cf-turnstile').count() > 0:
            return CaptchaType.CLOUDFLARE

        # reCAPTCHA v3 (harder to detect)
        if await page.locator('script[src*="recaptcha"]').count() > 0:
            scripts = await page.locator('script[src*="recaptcha"]').get_attribute('src')
            if 'v3' in scripts:
                return CaptchaType.RECAPTCHA_V3

        return CaptchaType.NONE

    async def _find_submit_button(self, page: Page) -> Optional[str]:
        """Find form submit button selector"""
        selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button.submit",
            "button.btn-primary",
            "a.btn-submit",
            "button:has-text('Submit')",
            "button:has-text('Absenden')",  # German
            "button:has-text('Senden')",    # German
        ]

        for selector in selectors:
            try:
                if await page.locator(selector).count() > 0:
                    return selector
            except:
                continue

        return None

    async def _is_multistep(self, page: Page) -> bool:
        """Check if form is multi-step"""
        indicators = [
            page.locator("[class*='progress']"),
            page.locator("[class*='step']"),
            page.locator("button:has-text('Next')"),
            page.locator("button:has-text('Weiter')"),  # German
        ]

        for indicator in indicators:
            if await indicator.count() > 0:
                return True

        return False


async def detect_form(url: str, enable_profiling: bool = False) -> Tuple[FormSchema, Optional[ProfilingData]]:
    """Convenience function to detect form"""
    detector = FormDetector(enable_profiling=enable_profiling)
    return await detector.detect_form(url)
