from __future__ import annotations

"""Dependency Injection Container.

Wires together configurations, repositories, scrapers, trackers,
and workflows without tight coupling.
"""

from pathlib import Path

import yaml

from application.workflows.apply_workflow import ApplyWorkflow
from application.workflows.discover_workflow import DiscoverWorkflow
from application.workflows.triage_workflow import TriageWorkflow
from core.config import settings
from domain.appliers.ashby_applier import AshbyApplier
from domain.appliers.greenhouse_applier import GreenhouseApplier
from domain.appliers.lever_applier import LeverApplier
from domain.appliers.review_gate import ReviewGate
from domain.qa.dict_answerer import DictAnswerer
from domain.qa.llm_answerer import LLMAnswerer
from domain.qa.qa_engine import QAEngine
from domain.scrapers.ats_direct_scraper import ATSDirectScraper
from domain.scrapers.instahyre_scraper import InstahyreScraper
from domain.scrapers.jobspy_scraper import JobSpyScraper
from domain.scrapers.wellfound_scraper import WellfoundScraper
from domain.triage.profile_loader import load_profile
from infrastructure.browser.browser_manager import BrowserManager
from infrastructure.database.job_repository import SQLiteJobRepository
from infrastructure.sheets.sheets_tracker import SheetsTracker


class Container:
    def __init__(self) -> None:
        self.settings = settings
        self.profile = load_profile("config/profile.yaml")

        # Load job preferences
        prefs_path = Path("config/job_prefs.yaml")
        self.job_prefs = yaml.safe_load(prefs_path.read_text()) if prefs_path.exists() else {}

        # Repositories & Trackers
        self.job_repo = SQLiteJobRepository()
        self.tracker = SheetsTracker()

        # Scrapers
        ats_companies = self.job_prefs.get("ats_companies", {})
        self.ats_scraper = ATSDirectScraper(ats_companies=ats_companies)

        keywords = self.job_prefs.get(
            "search_keywords", ["Machine Learning Engineer", "AI Engineer"]
        )
        locations = self.job_prefs.get("locations", ["Bengaluru", "Remote"])
        platforms_cfg = self.job_prefs.get("platforms", {})

        jobspy_sites = []
        if platforms_cfg.get("linkedin", True):
            jobspy_sites.append("linkedin")
        if platforms_cfg.get("indeed", False):
            jobspy_sites.append("indeed")
        if platforms_cfg.get("glassdoor", False):
            jobspy_sites.append("glassdoor")

        self.jobspy_scraper = JobSpyScraper(
            sites=jobspy_sites,
            search_terms=keywords[:3],
            locations=locations[:2],
        )
        self.wellfound_scraper = WellfoundScraper(headless=self.settings.headless)
        self.instahyre_scraper = InstahyreScraper(headless=self.settings.headless)

        # Active scrapers list
        active_scrapers = [self.ats_scraper]
        if jobspy_sites:
            active_scrapers.append(self.jobspy_scraper)
        if platforms_cfg.get("wellfound", False):
            active_scrapers.append(self.wellfound_scraper)
        if platforms_cfg.get("instahyre", False):
            active_scrapers.append(self.instahyre_scraper)

        self.active_scrapers = active_scrapers

        # Workflows
        self.discover_workflow = DiscoverWorkflow(
            scrapers=self.active_scrapers,
            job_repo=self.job_repo,
            tracker=self.tracker,
        )

        filter_rules = self.job_prefs.get("filters", {})
        self.triage_workflow = TriageWorkflow(
            job_repo=self.job_repo,
            tracker=self.tracker,
            filter_rules=filter_rules,
            min_score_threshold=float(self.settings.min_score_threshold),
        )

        # QA Engine
        self.dict_answerer = DictAnswerer("config/answers.yaml")
        self.llm_answerer = LLMAnswerer()
        self.qa_engine = QAEngine(
            dict_answerer=self.dict_answerer,
            llm_answerer=self.llm_answerer,
        )

        # Worker 3: Appliers & Review Gate
        self.browser_manager = BrowserManager(headless=self.settings.headless)
        self.review_gate = ReviewGate("data/pending_reviews.json")
        self.greenhouse_applier = GreenhouseApplier(
            browser_manager=self.browser_manager,
            qa_engine=self.qa_engine,
            review_gate=self.review_gate,
        )
        self.lever_applier = LeverApplier(
            browser_manager=self.browser_manager,
            qa_engine=self.qa_engine,
            review_gate=self.review_gate,
        )
        self.ashby_applier = AshbyApplier(
            browser_manager=self.browser_manager,
            qa_engine=self.qa_engine,
            review_gate=self.review_gate,
        )
        self.appliers = [
            self.greenhouse_applier,
            self.lever_applier,
            self.ashby_applier,
        ]

        self.apply_workflow = ApplyWorkflow(
            job_repo=self.job_repo,
            tracker=self.tracker,
            appliers=self.appliers,
            profile=self.profile,
            review_gate=self.review_gate,
        )


container = Container()
