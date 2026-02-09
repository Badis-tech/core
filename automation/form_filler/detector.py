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

                # Phase 4-7: Parallel Detection (batch queries)
                if self._profiler:
                    async with self._profiler.profile_phase("parallel_detection"):
                        # Run all detection phases in parallel using asyncio.gather
                        fields_data, captcha_data, submit_data, multistep_data = await asyncio.gather(
                            self._detect_fields_batch(page),
                            self._detect_captcha_batch(page),
                            self._find_submit_button_batch(page),
                            self._is_multistep(page)
                        )
                        fields = fields_data
                        captcha = captcha_data
                        submit_selector = submit_data
                        is_multistep = multistep_data
                    self._profiler.metadata['field_count'] = len(fields)
                else:
                    fields, captcha, submit_selector, is_multistep = await asyncio.gather(
                        self._detect_fields_batch(page),
                        self._detect_captcha_batch(page),
                        self._find_submit_button_batch(page),
                        self._is_multistep(page)
                    )

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

    async def _detect_fields_batch(self, page: Page) -> List[FormField]:
        """Detect all form fields using a single batched JavaScript query"""
        try:
            # Execute all field detection in browser context with single call
            fields_data = await page.evaluate("""
            () => {
                function getLabel(elem) {
                    // Try label[for=name]
                    if (elem.name) {
                        const labelFor = document.querySelector(`label[for="${elem.name}"]`);
                        if (labelFor) return labelFor.textContent.trim();
                    }

                    // Try wrapping label
                    let parent = elem.parentElement;
                    while (parent && parent.tagName !== 'FORM') {
                        if (parent.tagName === 'LABEL') {
                            return parent.textContent.trim();
                        }
                        parent = parent.parentElement;
                    }
                    return null;
                }

                const selectors = ['input', 'textarea', 'select'];
                const elements = document.querySelectorAll(selectors.join(','));

                const result = [];
                for (const elem of elements) {
                    // Skip hidden/disabled
                    if (elem.offsetParent === null || elem.disabled) {
                        continue;
                    }

                    const name = elem.getAttribute('name');
                    if (!name) continue;

                    result.push({
                        tagName: elem.tagName.toLowerCase(),
                        type: elem.getAttribute('type') || 'text',
                        name: name,
                        placeholder: elem.getAttribute('placeholder'),
                        required: elem.hasAttribute('required'),
                        label: getLabel(elem)
                    });
                }
                return result;
            }
            """)

            fields = []
            for field_data in fields_data:
                try:
                    field_type = self._classify_field(
                        field_data['name'],
                        field_data['type'],
                        field_data['placeholder'],
                        field_data['label']
                    )

                    inferred = self._infer_candidate_field(field_type, field_data['name'])

                    field = FormField(
                        selector=f"{field_data['tagName']}[name='{field_data['name']}']",
                        name=field_data['name'],
                        html_type=field_data['type'],
                        field_type=field_type,
                        required=field_data['required'],
                        placeholder=field_data['placeholder'],
                        label_text=field_data['label'],
                        inferred_candidate_field=inferred,
                    )
                    fields.append(field)
                except Exception as e:
                    logger.warning(f"Error processing field {field_data['name']}: {e}")
                    continue

            return fields

        except Exception as e:
            logger.error(f"Error in batch field detection: {e}")
            return []

    async def _detect_fields(self, page: Page) -> List[FormField]:
        """Deprecated: Use _detect_fields_batch instead. Kept for backwards compatibility."""
        return await self._detect_fields_batch(page)


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

    async def _detect_captcha_batch(self, page: Page) -> CaptchaType:
        """Detect CAPTCHA type using single batched query"""
        try:
            captcha_data = await page.evaluate("""
            () => ({
                hasRecaptchaV2: document.querySelector('[data-sitekey]') !== null,
                hasHcaptcha: document.querySelector('.h-captcha') !== null,
                hasCloudflare: document.querySelector('.cf-turnstile') !== null,
                hasRecaptchaV3: Array.from(document.scripts).some(s =>
                    s.src.includes('recaptcha') && s.src.includes('v3')
                )
            })
            """)

            if captcha_data['hasRecaptchaV2']:
                return CaptchaType.RECAPTCHA_V2
            if captcha_data['hasHcaptcha']:
                return CaptchaType.HCAPTCHA
            if captcha_data['hasCloudflare']:
                return CaptchaType.CLOUDFLARE
            if captcha_data['hasRecaptchaV3']:
                return CaptchaType.RECAPTCHA_V3

            return CaptchaType.NONE

        except Exception as e:
            logger.warning(f"Error in CAPTCHA detection: {e}")
            return CaptchaType.NONE

    async def _detect_captcha(self, page: Page) -> CaptchaType:
        """Deprecated: Use _detect_captcha_batch instead."""
        return await self._detect_captcha_batch(page)

    async def _find_submit_button_batch(self, page: Page) -> Optional[str]:
        """Find submit button using single batched query"""
        try:
            selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button.submit",
                "button.btn-primary",
                "a.btn-submit",
            ]

            submit_selector = await page.evaluate(f"""
            () => {{
                const selectors = {selectors};
                for (const selector of selectors) {{
                    if (document.querySelector(selector)) {{
                        return selector;
                    }}
                }}

                // Try text-based buttons (case insensitive)
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {{
                    const text = btn.textContent.toLowerCase().trim();
                    if (text === 'submit' || text === 'absenden' || text === 'senden') {{
                        return 'button[type="submit"]:not([disabled])';
                    }}
                }}

                return null;
            }}
            """)

            return submit_selector

        except Exception as e:
            logger.warning(f"Error in submit button detection: {e}")
            return None

    async def _find_submit_button(self, page: Page) -> Optional[str]:
        """Deprecated: Use _find_submit_button_batch instead."""
        return await self._find_submit_button_batch(page)

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
