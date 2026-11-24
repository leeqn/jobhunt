import asyncio
import random
from abc import ABC, abstractmethod
from typing import Optional
from asgiref.sync import sync_to_async
from curl_cffi.requests import AsyncSession
from ..sort import skill_filter


class BaseParser(ABC):
    CONCURRENCY_LIMIT: int = 10
    DELAY_RANGE: tuple[float, float] = (0.3, 0.7)

    def __init__(self):
        self.semaphore = asyncio.Semaphore(self.CONCURRENCY_LIMIT)

    @property
    @abstractmethod
    def source_name(self) -> str:
        pass

    @abstractmethod
    def get_vacancy_urls(self, list_html: str) -> list[str]:
        pass

    @abstractmethod
    def parse_vacancy_page(self, html: str, url: str) -> Optional[dict]:
        pass

    async def _fetch(self, session: AsyncSession, url: str) -> Optional[str]:
        async with self.semaphore:
            await asyncio.sleep(random.uniform(*self.DELAY_RANGE))
            try:
                response = await session.get(url, timeout=15)
                if response.status_code == 200:
                    return response.text
                print(f"[{self.source_name}] HTTP error {response.status_code} for {url}")
            except Exception as e:
                print(f"[{self.source_name}] Error {url}: {e}")
        return None

    async def _process_single_vacancy(self, session: AsyncSession, url: str) -> Optional[dict]:
        html = await self._fetch(session, url)
        if html:
            return self.parse_vacancy_page(html, url)
        return None

    async def run(self, start_url: str):
        print(f"[{self.source_name}] start crawling {start_url}")
        async with AsyncSession(impersonate="safari") as session:
            main_html = await self._fetch(session, start_url)
            if not main_html:
                return

            urls = self.get_vacancy_urls(main_html)
            print(f"[{self.source_name}] found {len(urls)}")

            tasks = [self._process_single_vacancy(session, url) for url in urls]
            results = await asyncio.gather(*tasks)
            jobs = [j for j in results if j is not None]
            await self.save_to_db(jobs)

    @sync_to_async
    def _bulk_save_sync(self, jobs: list[dict]) -> int:
        from tracker.models import Vacancy

        vacancy_objects = []
        for job in jobs:
            skills = skill_filter(job.get("raw_text", ""))
            skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills or "")

            vacancy_objects.append(
                Vacancy(
                    title=job["title"],
                    company=job["company"],
                    link=job["link"],
                    raw_text=job.get("raw_text", ""),
                    found_skills=skills_str,
                )
            )

        created = Vacancy.objects.bulk_create(vacancy_objects, ignore_conflicts=True)
        return len(created)

    async def save_to_db(self, jobs: list[dict]) -> None:
        if not jobs:
            print(f"[{self.source_name}] no found vacancies.")
            return

        saved_count = await self._bulk_save_sync(jobs)
        print(f"[{self.source_name}] saved: {saved_count} (из {len(jobs)})")