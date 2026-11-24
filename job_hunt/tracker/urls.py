from django.urls import path
import views

urlpatterns = [
    path("", views.vacancy_list, name="vacancy_list"),
    path("scrape/", views.trigger_scrape, name="trigger_scrape"),
]