from __future__ import annotations

"""Lever ATS Form Applier.

Automates candidate job applications on Lever job boards (jobs.lever.co).
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


class LeverApplier(BaseApplier):
    @property
    def platform_name(self) -> str:
        return "lever"

    def can_handle(self, url: str) -> bool:
        u = url.lower()
        return "jobs.lever.co" in u or "lever" in u

    async def apply(
        self,
        job: JobRecord,
        profile: CandidateProfile,
        resume_path: str | None = None,
    ) -> ApplyResult:
        """Execute Lever application filling and conditional submission."""
        resume = resume_path or profile.resume_pdf_path
        page: Page | None = None
        filled_fields: dict[str, Any] = {}

        # Ensure url ends with /apply for Lever postings
        apply_url = job.url
        if not apply_url.rstrip("/").endswith("/apply"):
            apply_url = apply_url.rstrip("/") + "/apply"

        try:
            page = await self.browser_manager.new_page()
            log.info("Navigating to Lever application: %s", apply_url)
            await page.goto(apply_url, wait_until="domcontentloaded")
            await asyncio.sleep(1.5)

            # Wait for application form
            form_selector = "form#application-form, .application-form, form"
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
            screenshot_path = str(screenshot_dir / f"{job.uid}_lever_filled.png")
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
            log.info("Auto-submit enabled: submitting Lever application for %s", job.uid)
            submit_btn = page.locator("button#btn-submit, button[type='submit'], input[type='submit']")
            await submit_btn.first.click()

            await page.wait_for_timeout(4000)
            conf_text = await page.inner_text("body")
            post_screenshot = str(screenshot_dir / f"{job.uid}_lever_submitted.png")
            await self.browser_manager.capture_screenshot(page, post_screenshot)

            is_submitted = (
                "thank you" in conf_text.lower()
                or "submitted" in conf_text.lower()
                or "thanks" in page.url.lower()
            )

            return ApplyResult(
                success=is_submitted,
                status="applied" if is_submitted else "failed",
                screenshot_path=post_screenshot,
                filled_fields=filled_fields,
                confirmation_text="Application submitted successfully" if is_submitted else "Submission not confirmed",
            )

        except Exception as e:
            log.error("Error applying to Lever job %s: %s", job.uid, e)
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
        """Fill Lever standard input elements."""
        # Full Name
        name_loc = page.locator("input[name='name']")
        if await name_loc.count() > 0:
            await name_loc.first.fill(profile.name)
            filled["name"] = profile.name

        # Email
        email_loc = page.locator("input[name='email']")
        if await email_loc.count() > 0:
            await email_loc.first.fill(profile.email)
            filled["email"] = profile.email

        # Phone
        phone_loc = page.locator("input[name='phone']")
        if await phone_loc.count() > 0:
            await phone_loc.first.fill(profile.phone)
            filled["phone"] = profile.phone

        # Current Company
        org_loc = page.locator("input[name='org']")
        if await org_loc.count() > 0:
            await org_loc.first.fill("Polynomial.AI")
            filled["company"] = "Polynomial.AI"

        # URLs: LinkedIn, GitHub, Portfolio
        li_loc = page.locator("input[name='urls[LinkedIn]'], input[name*='LinkedIn']")
        if await li_loc.count() > 0:
            await li_loc.first.fill(profile.linkedin_url)
            filled["linkedin"] = profile.linkedin_url

        gh_loc = page.locator("input[name='urls[GitHub]'], input[name*='GitHub']")
        if await gh_loc.count() > 0:
            await gh_loc.first.fill(profile.github_url)
            filled["github"] = profile.github_url

        pf_loc = page.locator("input[name='urls[Portfolio]'], input[name='urls[Other]']")
        if await pf_loc.count() > 0:
            await pf_loc.first.fill(profile.portfolio_url or profile.github_url)
            filled["portfolio"] = profile.portfolio_url

    async def _upload_resume(
        self,
        page: Page,
        resume_path: str,
        filled: dict[str, Any],
    ) -> None:
        """Upload resume to Lever file input."""
        file_input = page.locator("input[type='file'][name='resume'], input[type='file']")
        if await file_input.count() > 0:
            await file_input.first.set_input_files(resume_path)
            filled["resume_file"] = resume_path
            log.info("Uploaded resume to Lever: %s", resume_path)

    async def _answer_custom_questions(
        self,
        page: Page,
        profile: CandidateProfile,
        filled: dict[str, Any],
    ) -> None:
        """Iterate over Lever custom question blocks."""
        blocks = page.locator(".application-question, .custom-question")
        count = await blocks.count()

        for i in range(count):
            try:
                block = blocks.nth(i)
                text_elem = block.locator(".text, label").first
                if await text_elem.count() == 0:
                    continue

                q_text = (await text_elem.inner_text()).strip()
                if not q_text or any(k in q_text.lower() for k in ["name", "email", "phone", "resume"]):
                    continue

                # Dropdowns
                select_elem = block.locator("select").first
                if await select_elem.count() > 0:
                    options = await select_elem.locator("option").all_inner_texts()
                    cleaned_opts = [o.strip() for o in options if o.strip() and not o.strip().lower().startswith("select")]
                    ans_res = await self.qa_engine.answer_question(q_text, profile, options=cleaned_opts)
                    if ans_res.answer:
                        await select_elem.select_option(label=str(ans_res.answer))
                        filled[q_text] = ans_res.answer
                    continue

                # Radios
                radios = block.locator("input[type='radio']")
                if await radios.count() > 0:
                    radio_labels = await block.locator("label, span").all_inner_texts()
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

                # Text/Textarea
                text_input = block.locator("input[type='text'], textarea").first
                if await text_input.count() > 0:
                    val = await text_input.input_value()
                    if not val:
                        ans_res = await self.qa_engine.answer_question(q_text, profile)
                        if ans_res.answer:
                            await text_input.fill(str(ans_res.answer))
                            filled[q_text] = ans_res.answer
            except Exception as e:
                log.debug("Skipped Lever custom field %d: %s", i, e)
