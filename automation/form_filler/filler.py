import asyncio
import base64
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime

from playwright.async_api import async_playwright, Page
from automation.models import FormSchema, Candidate, ApplicationRecord, CaptchaType, ErrorType

logger = logging.getLogger(__name__)


class FormFiller:
    """Fill and submit forms with candidate data"""

    def __init__(self, headless: bool = True, timeout: int = 60000):
        self.headless = headless
        self.timeout = timeout

    async def fill_and_submit(
        self,
        form_schema: FormSchema,
        candidate: Candidate,
        screenshot_dir: str = "./screenshots",
    ) -> ApplicationRecord:
        """
        Fill form with candidate data and submit.
        Returns ApplicationRecord with submission result.
        """
        logger.info(f"Filling form at {form_schema.url} for {candidate.name}")

        record = ApplicationRecord(
            candidate_id=candidate.id or "unknown",
            form_schema_id=form_schema.id or "unknown",
            url=form_schema.url,
        )

        Path(screenshot_dir).mkdir(exist_ok=True)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()

            try:
                # Navigate to form
                await page.goto(form_schema.url, wait_until="networkidle", timeout=self.timeout)
                await asyncio.sleep(1)

                # Check for CAPTCHA
                if form_schema.captcha_type != "none":
                    logger.warning(f"CAPTCHA detected: {form_schema.captcha_type}")
                    record.status = "captcha_quarantine"
                    record.requires_manual_action = True
                    record.manual_action_type = "captcha"
                    screenshot = await self._take_screenshot(page, screenshot_dir)
                    record.screenshot_path = screenshot
                    await browser.close()
                    return record

                # Map candidate data to form fields
                field_data = self._map_candidate_to_form(candidate, form_schema)

                if not field_data:
                    record.status = "failed"
                    record.error_type = ErrorType.VALIDATION
                    record.last_error = "Could not map candidate data to form fields"
                    await browser.close()
                    return record

                # Fill form fields
                fill_result = await self._fill_fields(page, form_schema, field_data, candidate)
                if not fill_result["success"]:
                    record.status = "failed"
                    record.error_type = ErrorType.FIELD_NOT_FOUND
                    record.last_error = fill_result.get("error")
                    screenshot = await self._take_screenshot(page, screenshot_dir)
                    record.screenshot_path = screenshot
                    await browser.close()
                    return record

                # Take screenshot before submit
                pre_submit_screenshot = await self._take_screenshot(page, screenshot_dir, suffix="_pre_submit")

                # Submit form
                submit_result = await self._submit_form(page, form_schema)
                if not submit_result["success"]:
                    record.status = "failed"
                    record.error_type = ErrorType.SUBMIT_FAILED
                    record.last_error = submit_result.get("error")
                    record.screenshot_path = pre_submit_screenshot
                    await browser.close()
                    return record

                # Wait for post-submit page
                await asyncio.sleep(2)

                # Take final screenshot
                post_submit_screenshot = await self._take_screenshot(page, screenshot_dir, suffix="_post_submit")

                # Check for success indicator
                success = await self._check_success(page, form_schema)

                record.status = "success" if success else "submitted"
                record.form_data_submitted = field_data
                record.submitted_at = datetime.utcnow()
                record.screenshot_path = post_submit_screenshot
                record.attempt_count = 1

                logger.info(f"Successfully submitted form at {form_schema.url}")

            except Exception as e:
                logger.error(f"Error filling/submitting form: {e}")
                record.status = "failed"
                record.error_type = ErrorType.UNKNOWN
                record.last_error = str(e)

            finally:
                await browser.close()

        return record

    def _map_candidate_to_form(self, candidate: Candidate, form_schema: FormSchema) -> Optional[Dict[str, str]]:
        """Map candidate attributes to form field values"""
        field_data = {}

        for field in form_schema.fields:
            inferred = field.inferred_candidate_field
            if not inferred or inferred == "candidate.unknown":
                if field.required:
                    logger.warning(f"Required field not mapped: {field.name}")
                    return None
                continue

            # Extract attribute from candidate
            attr_parts = inferred.split(".")
            if len(attr_parts) != 2 or attr_parts[0] != "candidate":
                continue

            attr_name = attr_parts[1]
            value = getattr(candidate, attr_name, None)

            if value is None and field.required:
                logger.warning(f"Required field {attr_name} has no value")
                return None

            if value:
                field_data[field.selector] = str(value)

        return field_data if field_data else None

    async def _fill_fields(
        self,
        page: Page,
        form_schema: FormSchema,
        field_data: Dict[str, str],
        candidate: Candidate,
    ) -> Dict[str, Any]:
        """
        Fill form fields with data.
        Returns {success: bool, error: str}
        """
        try:
            for field in form_schema.fields:
                selector = field.selector

                if field.html_type == "file":
                    # Handle file upload
                    if candidate.cv_file:
                        cv_path = Path(candidate.cv_file)
                        if cv_path.exists():
                            await page.locator(selector).set_input_files(str(cv_path))
                            logger.info(f"Uploaded file: {cv_path}")
                    continue

                # Get value to fill
                value = field_data.get(selector)
                if not value:
                    if field.required:
                        return {"success": False, "error": f"No value for required field: {field.name}"}
                    continue

                # Fill based on field type
                if field.html_type == "checkbox":
                    await page.locator(selector).check()
                elif field.html_type == "select":
                    # Try to select by value or label
                    try:
                        await page.locator(selector).select_option(value)
                    except:
                        await page.locator(f"{selector} >> text={value}").click()
                else:
                    # Text input
                    await page.locator(selector).fill(value)
                    logger.debug(f"Filled field {field.name}")

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _submit_form(self, page: Page, form_schema: FormSchema) -> Dict[str, Any]:
        """Click submit button and wait for navigation"""
        try:
            submit_selector = form_schema.submit_selector

            # Try to click submit button
            await page.locator(submit_selector).click()
            logger.info(f"Clicked submit button: {submit_selector}")

            # Wait for navigation or timeout
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except:
                # Some forms don't reload after submit
                await asyncio.sleep(2)

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _check_success(self, page: Page, form_schema: FormSchema) -> bool:
        """Check if form submission was successful"""
        if not form_schema.success_indicator:
            # No success indicator defined, assume success
            return True

        try:
            result = await page.locator(form_schema.success_indicator).count()
            return result > 0
        except:
            return False

    async def _take_screenshot(self, page: Page, screenshot_dir: str, suffix: str = "") -> str:
        """Take screenshot of current page"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"form_{timestamp}{suffix}.png"
        filepath = Path(screenshot_dir) / filename

        try:
            await page.screenshot(path=str(filepath))
            logger.info(f"Screenshot saved: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return ""


async def fill_and_submit(
    form_schema: FormSchema,
    candidate: Candidate,
    screenshot_dir: str = "./screenshots",
) -> ApplicationRecord:
    """Convenience function to fill and submit form"""
    filler = FormFiller()
    return await filler.fill_and_submit(form_schema, candidate, screenshot_dir)
