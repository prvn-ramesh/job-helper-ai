from __future__ import annotations

"""Greenhouse ATS Form Applier.

Automates candidate job applications on Greenhouse job boards
(boards.greenhouse.io / job-boards.greenhouse.io).
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from playwright.async_api import Page

from core.entities.job import JobRecord
from core.entities.profile import CandidateProfile
from domain.appliers.base_applier import ApplyResult, BaseApplier

log = logging.getLogger(__name__)


class GreenhouseApplier(BaseApplier):
    @property
    def platform_name(self) -> str:
        return "greenhouse"

    def can_handle(self, url: str) -> bool:
        u = url.lower()
        return "greenhouse.io" in u or "gh_jid" in u or "greenhouse" in u

    async def apply(
        self,
        job: JobRecord,
        profile: CandidateProfile,
        resume_path: str | None = None,
    ) -> ApplyResult:
        """Execute Greenhouse application filling and conditional submission."""
        resume = resume_path or profile.resume_pdf_path
        page: Page | None = None
        filled_fields: dict[str, Any] = {}

        try:
            page = await self.browser_manager.new_page()
            log.info("Navigating to Greenhouse application: %s", job.url)
            await page.goto(job.url, wait_until="domcontentloaded")
            await asyncio.sleep(1.5)

            # Wait for form to appear
            # Wait for form to appear (supports legacy boards.greenhouse.io and React job-boards.greenhouse.io)
            form_selector = "#application-form, #application_form, form.application--form, form#application, form"
            await page.wait_for_selector(form_selector, timeout=15000)

            # 1. Fill Standard Personal Fields
            await self._fill_standard_fields(page, profile, filled_fields)

            # 2. Upload Resume
            if resume and Path(resume).exists():
                await self._upload_resume(page, resume, filled_fields)

            # 3. Fill Custom Screening Questions
            await self._answer_custom_questions(page, profile, filled_fields)

            # 4. Capture Pre-Submit Full Page Screenshot
            screenshot_dir = Path("data/screenshots")
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = str(screenshot_dir / f"{job.uid}_greenhouse_filled.png")
            await self.browser_manager.capture_screenshot(page, screenshot_path)

            # 5. Review Gate Check
            if not self.review_gate.is_auto_submit_enabled():
                self.review_gate.record_pending_review(
                    job=job,
                    platform=self.platform_name,
                    screenshot_path=screenshot_path,
                    filled_fields=filled_fields,
                    notes="Awaiting candidate review in semi-auto mode",
                )
                return ApplyResult(
                    success=True,
                    status="pending_review",
                    screenshot_path=screenshot_path,
                    filled_fields=filled_fields,
                    confirmation_text="Application form filled and screenshot captured. Awaiting submission approval.",
                )

            # 6. Full-Auto Submission
            log.info("Auto-submit enabled: submitting Greenhouse application for %s", job.uid)
            submit_btn = page.locator(
                "#submit_app, button#submit-button, button:has-text('Submit application'), "
                "button:has-text('Submit Application'), input[type='submit'], button[type='submit']"
            )
            await submit_btn.first.click()

            # Wait for confirmation redirect or success message
            await page.wait_for_timeout(4000)
            conf_text = await page.inner_text("body")
            post_screenshot = str(screenshot_dir / f"{job.uid}_greenhouse_submitted.png")
            await self.browser_manager.capture_screenshot(page, post_screenshot)

            is_submitted = (
                "thank you" in conf_text.lower()
                or "submitted" in conf_text.lower()
                or "received" in conf_text.lower()
                or "confirmation" in page.url.lower()
            )

            return ApplyResult(
                success=is_submitted,
                status="applied" if is_submitted else "failed",
                screenshot_path=post_screenshot,
                filled_fields=filled_fields,
                confirmation_text="Application submitted successfully" if is_submitted else "Submission not confirmed",
            )

        except Exception as e:
            log.error("Error applying to Greenhouse job %s: %s", job.uid, e)
            error_shot = ""
            if page:
                try:
                    error_shot = f"data/screenshots/{job.uid}_error.png"
                    await self.browser_manager.capture_screenshot(page, error_shot)
                except Exception as err:
                    log.debug("Could not capture error screenshot: %s", err)
            return ApplyResult(
                success=False,
                status="failed",
                screenshot_path=error_shot,
                filled_fields=filled_fields,
                error_message=str(e),
            )
        finally:
            if page:
                try:
                    await page.context.close()
                except Exception as err:
                    log.debug("Could not close page context: %s", err)

    async def _fill_standard_fields(
        self,
        page: Page,
        profile: CandidateProfile,
        filled: dict[str, Any],
    ) -> None:
        """Fill standard Greenhouse name, email, phone, and location fields."""
        names = profile.name.split()
        first_name = names[0] if names else "Praveen"
        last_name = " ".join(names[1:]) if len(names) > 1 else "Ramesh"

        # First Name
        fn_locator = page.locator("#first_name, input[name*='first_name']")
        if await fn_locator.count() > 0:
            await fn_locator.first.fill(first_name)
            filled["first_name"] = first_name

        # Last Name
        ln_locator = page.locator("#last_name, input[name*='last_name']")
        if await ln_locator.count() > 0:
            await ln_locator.first.fill(last_name)
            filled["last_name"] = last_name

        # Email
        email_locator = page.locator("#email, input[name*='email']")
        if await email_locator.count() > 0:
            await email_locator.first.fill(profile.email)
            filled["email"] = profile.email

        # Phone
        phone_locator = page.locator("#phone, input[name*='phone']")
        if await phone_locator.count() > 0:
            await phone_locator.first.fill(profile.phone)
            filled["phone"] = profile.phone

        # Location / City / Country
        loc_locator = page.locator("#job_application_location, #country, input[name*='location'], input[name*='country']")
        if await loc_locator.count() > 0:
            await loc_locator.first.fill(profile.location)
            filled["location"] = profile.location

        # LinkedIn
        li_locator = page.locator("input[name*='linkedin'], input[id*='linkedin'], input[autocomplete*='linkedin']")
        if await li_locator.count() > 0:
            await li_locator.first.fill(profile.linkedin_url)
            filled["linkedin"] = profile.linkedin_url

        # GitHub / Website
        gh_locator = page.locator("input[name*='github'], input[id*='github'], input[name*='website']")
        if await gh_locator.count() > 0:
            await gh_locator.first.fill(profile.github_url)
            filled["github"] = profile.github_url

    async def _upload_resume(
        self,
        page: Page,
        resume_path: str,
        filled: dict[str, Any],
    ) -> None:
        """Upload candidate PDF resume to file input."""
        file_input = page.locator("input#resume[type='file'], input[type='file'][name*='resume'], input[type='file']")
        if await file_input.count() > 0:
            await file_input.first.set_input_files(resume_path)
            filled["resume_file"] = resume_path
            log.info("Uploaded resume: %s", resume_path)

    async def _answer_custom_questions(
        self,
        page: Page,
        profile: CandidateProfile,
        filled: dict[str, Any],
    ) -> None:
        """Iterate over custom question containers and resolve answers using QAEngine."""
        # 1. Container-based questions (Legacy Greenhouse)
        containers = page.locator("div.field, div.custom-question, div[class*='field']")
        count = await containers.count()

        for i in range(count):
            try:
                container = containers.nth(i)
                label_elem = container.locator("label").first
                if await label_elem.count() == 0:
                    continue

                q_text = (await label_elem.inner_text()).strip()
                if not q_text or any(k in q_text.lower() for k in ["first name", "last name", "email", "phone", "resume"]):
                    continue

                # Check if it has a select / dropdown
                select_elem = container.locator("select").first
                if await select_elem.count() > 0:
                    options = await select_elem.locator("option").all_inner_texts()
                    cleaned_opts = [o.strip() for o in options if o.strip() and not o.strip().lower().startswith("select")]
                    ans_res = await self.qa_engine.answer_question(q_text, profile, options=cleaned_opts)
                    if ans_res.answer:
                        await select_elem.select_option(label=str(ans_res.answer))
                        filled[q_text] = ans_res.answer
                    continue

                # Check radio buttons
                radios = container.locator("input[type='radio']")
                if await radios.count() > 0:
                    radio_labels = await container.locator("label, span").all_inner_texts()
                    ans_res = await self.qa_engine.answer_question(q_text, profile, options=radio_labels)
                    if ans_res.answer:
                        ans_target = str(ans_res.answer).lower()
                        for r_idx in range(await radios.count()):
                            r_input = radios.nth(r_idx)
                            r_label = await r_input.evaluate("el => el.parentElement ? el.parentElement.innerText : ''")
                            if ans_target in r_label.lower():
                                await r_input.check()
                                filled[q_text] = ans_res.answer
                                break
                    continue

                # Text input or textarea
                text_input = container.locator("input[type='text'], input[type='number'], textarea").first
                if await text_input.count() > 0:
                    val = await text_input.input_value()
                    if not val:
                        ans_res = await self.qa_engine.answer_question(q_text, profile)
                        if ans_res.answer:
                            await text_input.fill(str(ans_res.answer))
                            filled[q_text] = ans_res.answer
            except Exception as e:
                log.debug("Skipped custom field %d: %s", i, e)

        # 2. Direct question inputs with id^='question_' (React Greenhouse)
        q_elements = page.locator("input[id^='question_'], textarea[id^='question_'], select[id^='question_']")
        q_count = await q_elements.count()
        for idx in range(q_count):
            try:
                el = q_elements.nth(idx)
                el_id = await el.get_attribute("id")
                if not el_id:
                    continue
                label_loc = page.locator(f"label[for='{el_id}']")
                if await label_loc.count() == 0:
                    continue
                q_text = (await label_loc.inner_text()).strip()
                if not q_text or q_text in filled:
                    continue
                tag = await el.evaluate("el => el.tagName.toLowerCase()")
                if tag == "select":
                    options = await el.locator("option").all_inner_texts()
                    cleaned_opts = [o.strip() for o in options if o.strip() and not o.strip().lower().startswith("select")]
                    ans_res = await self.qa_engine.answer_question(q_text, profile, options=cleaned_opts)
                    if ans_res.answer:
                        await el.select_option(label=str(ans_res.answer))
                        filled[q_text] = ans_res.answer
                else:
                    val = await el.input_value()
                    if not val:
                        ans_res = await self.qa_engine.answer_question(q_text, profile)
                        if ans_res.answer:
                            await el.fill(str(ans_res.answer))
                            filled[q_text] = ans_res.answer
            except Exception as e:
                log.debug("Skipped direct question %d: %s", idx, e)
