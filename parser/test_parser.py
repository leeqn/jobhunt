import asyncio
from asgiref.sync import sync_to_async

from django.test import TestCase
from django.db import close_old_connections

from tracker.models import Vacancy

from parser.sort import skill_filter

async def _run_and_cleanup(coro):
    try:
        return await coro
    finally:
        await sync_to_async(close_old_connections)()

class ParserSaveAndSkillsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        Vacancy._meta.managed = True
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        Vacancy._meta.managed = False

    def test_skill_filter_extracts_known_skills(self):
        sample_text = "Looking for a Python developer with Django, PostgreSQL and Docker experience."
        skills = skill_filter(sample_text)
        skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills)
        self.assertIn("Python", skills_str)
        self.assertIn("Django", skills_str)

    def test_bulk_save_ignores_duplicate_links(self):
        from parser.fetch_sources.base import BaseParser

        class DummyParser(BaseParser):
            source_name = "dummy"
            def get_vacancy_urls(self, list_html): return []
            def parse_vacancy_page(self, html, url): return None

        parser = DummyParser()
        jobs_batch_1 = [
            {"title": "Dev 1", "company": "Comp A", "link": "https://dou.ua/1", "raw_text": "Python"},
            {"title": "Dev 2", "company": "Comp B", "link": "https://dou.ua/2", "raw_text": "Django"},
        ]
        jobs_batch_2 = [
            {"title": "Dev 1 Duplicate", "company": "Comp A", "link": "https://dou.ua/1", "raw_text": "Python"},
            {"title": "Dev 3 New", "company": "Comp C", "link": "https://dou.ua/3", "raw_text": "FastAPI"},
        ]

        asyncio.run(_run_and_cleanup(parser.save_to_db(jobs_batch_1)))
        self.assertEqual(Vacancy.objects.count(), 2)

        asyncio.run(_run_and_cleanup(parser.save_to_db(jobs_batch_2)))
        self.assertEqual(Vacancy.objects.count(), 3)

