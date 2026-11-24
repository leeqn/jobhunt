from unittest.mock import AsyncMock, patch

from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from .models import Vacancy
from .tasks import scrape_vacancies_task


class BaseVacancyTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        Vacancy._meta.managed = True
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        Vacancy._meta.managed = False

    def setUp(self):
        cache.clear()
        self.client = Client()

        self.v_dou = Vacancy.objects.create(
            title="Senior Python Developer",
            company="TechCorp",
            link="https://jobs.dou.ua/companies/techcorp/vacancies/101/",
            raw_text="We need experience with Django, PostgreSQL and Docker.",
            found_skills="Python, Django, PostgreSQL, Docker",
        )
        self.v_robota = Vacancy.objects.create(
            title="Middle Backend Engineer",
            company="StartupUA",
            link="https://robota.ua/company123/vacancy456",
            raw_text="Building high-load APIs with FastAPI and Asyncio.",
            found_skills="Python, FastAPI, Asyncio",
        )


class VacancyModelTests(BaseVacancyTestCase):
    def test_skills_list_property(self):
        self.assertEqual(
            self.v_dou.skills_list,
            ["Python", "Django", "PostgreSQL", "Docker"],
        )
        empty_vacancy = Vacancy(title="Test", company="Test", link="https://example.com", found_skills="")
        self.assertEqual(empty_vacancy.skills_list, [])

    def test_source_detection(self):
        self.assertEqual(self.v_dou.source, "DOU")
        self.assertEqual(self.v_robota.source, "Robota.ua")


class VacancyViewsTests(BaseVacancyTestCase):
    def test_vacancy_list_renders_all(self):
        response = self.client.get(reverse("vacancy_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Senior Python Developer")
        self.assertContains(response, "Middle Backend Engineer")
        self.assertEqual(response.context["filtered_count"], 2)

    def test_filter_by_source(self):
        response = self.client.get(reverse("vacancy_list"), {"source": "dou"})
        self.assertContains(response, "Senior Python Developer")
        self.assertNotContains(response, "Middle Backend Engineer")
        self.assertEqual(response.context["filtered_count"], 1)

    def test_filter_by_skill(self):
        response = self.client.get(reverse("vacancy_list"), {"skill": "FastAPI"})
        self.assertNotContains(response, "Senior Python Developer")
        self.assertContains(response, "Middle Backend Engineer")

    def test_search_query(self):
        response = self.client.get(reverse("vacancy_list"), {"q": "TechCorp"})
        self.assertContains(response, "Senior Python Developer")
        self.assertNotContains(response, "Middle Backend Engineer")

    def test_stats_are_cached_in_redis(self):
        self.assertIsNone(cache.get("vacancy_stats"))
        self.client.get(reverse("vacancy_list"))
        cached_stats = cache.get("vacancy_stats")
        self.assertIsNotNone(cached_stats)
        self.assertEqual(cached_stats["total"], 2)
        self.assertEqual(cached_stats["dou"], 1)
        self.assertEqual(cached_stats["robota"], 1)


class ScrapeTriggerAndTaskTests(BaseVacancyTestCase):
    @patch("tracker.views.scrape_vacancies_task.delay")
    def test_trigger_scrape_post_queues_celery_task(self, mock_delay):
        response = self.client.post(
            reverse("trigger_scrape"),
            {"query": "Django"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        mock_delay.assert_called_once_with("Django")
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertIn("Django", str(messages[0]))

    def test_trigger_scrape_get_not_allowed(self):
        response = self.client.get(reverse("trigger_scrape"))
        self.assertEqual(response.status_code, 405)

    @patch("tracker.tasks.run_scrapers", new_callable=AsyncMock)
    def test_scrape_vacancies_task_runs_parser_and_clears_cache(self, mock_run_scrapers):
        cache.set("vacancy_stats", {"total": 99}, timeout=3600)

        result = scrape_vacancies_task("Python")

        mock_run_scrapers.assert_awaited_once_with(query="Python")
        self.assertIsNone(cache.get("vacancy_stats"))
        self.assertIn("Python", result)