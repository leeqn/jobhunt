from django.contrib import messages
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from models import Vacancy
from tasks import scrape_vacancies_task


def vacancy_list(request):
    queryset = Vacancy.objects.all()

    q = request.GET.get("q", "").strip()
    skill = request.GET.get("skill", "").strip()
    source = request.GET.get("source", "").strip()

    if q:
        queryset = queryset.filter(
            Q(title__icontains=q) | Q(company__icontains=q) | Q(raw_text__icontains=q)
        )

    if skill:
        queryset = queryset.filter(found_skills__icontains=skill)

    if source == "dou":
        queryset = queryset.filter(link__icontains="dou.ua")
    elif source == "robota":
        queryset = queryset.filter(link__icontains="robota.ua")

    stats = cache.get("vacancy_stats")
    if stats is None:
        stats = {
            "total": Vacancy.objects.count(),
            "dou": Vacancy.objects.filter(link__icontains="dou.ua").count(),
            "robota": Vacancy.objects.filter(link__icontains="robota.ua").count(),
        }
        cache.set("vacancy_stats", stats, timeout=3600)

    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    popular_skills = ["Python", "Django", "FastAPI", "PostgreSQL", "Docker", "Asyncio", "Git"]

    return render(request, "tracker/vacancy_list.html", {
        "page_obj": page_obj,
        "q": q,
        "selected_skill": skill,
        "selected_source": source,
        "popular_skills": popular_skills,
        "stats": stats,
        "filtered_count": paginator.count,
    })


@require_POST
def trigger_scrape(request):
    query = request.POST.get("query", "Python").strip() or "Python"
    scrape_vacancies_task.delay(query)
    messages.success(
        request,
        f"already parsing for «{query}»"
    )
    return redirect("vacancy_list")