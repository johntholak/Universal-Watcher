from datetime import datetime, timezone
import unittest

from job_hunter.models import Compensation, JobPosting, SearchProfile
from job_hunter.pipeline import deduplicate, hard_filter_reasons, passes_hard_filters


NOW = datetime.now(timezone.utc)


def job(**overrides):
    data = dict(
        source="greenhouse",
        source_job_id="123",
        company="Example Co",
        title="Director of Events",
        apply_url="https://example.com/jobs/123",
        retrieved_at=NOW,
        location="Los Angeles, CA",
        employment_type="fulltime",
        compensation=Compensation(minimum=150000, maximum=180000, currency="USD", period="year"),
        description="Lead event strategy and production.",
    )
    data.update(overrides)
    return JobPosting(**data)


class PipelineTests(unittest.TestCase):
    def test_deduplicates_same_source_id(self):
        self.assertEqual(len(deduplicate([job(), job()])), 1)

    def test_known_pay_below_floor_is_hard_filter(self):
        posting = job(compensation=Compensation(minimum=90000, maximum=100000, currency="USD", period="year"))
        profile = SearchProfile(minimum_compensation=120000)
        self.assertFalse(passes_hard_filters(posting, profile))
        self.assertIn("known compensation below minimum", hard_filter_reasons(posting, profile))

    def test_unknown_pay_does_not_fail_floor(self):
        posting = job(compensation=None)
        profile = SearchProfile(minimum_compensation=120000)
        self.assertTrue(passes_hard_filters(posting, profile))

    def test_blocked_company_is_rejected(self):
        profile = SearchProfile(blocked_companies=("Example Co",))
        self.assertFalse(passes_hard_filters(job(), profile))


if __name__ == "__main__":
    unittest.main()
