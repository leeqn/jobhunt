import asyncio
from .fetch_sources.dou import DouParser
from .fetch_sources.robota import RobotaParser
from urllib.parse import quote

PARSER_REGISTRY = {
    'dou': (DouParser, lambda req: f'https://jobs.dou.ua/vacancies/?search={quote(req)}'),
    'robota': (RobotaParser, lambda req: f'https://robota.ua/zapros/{quote(req.lower())}/ukraine'),
}


async def run_scrapers(query:str="python"):
    selected_sites = list(PARSER_REGISTRY.keys())
    tasks = []
    for site_key in selected_sites:
        parser_cls, url_builder = PARSER_REGISTRY[site_key]
        target_url = url_builder(query)
        parser_instance = parser_cls()
        tasks.append(parser_instance.run(target_url))

    print(f"Run: {', '.join(selected_sites)}...")
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(run_scrapers())