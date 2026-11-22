from django.db import models


class Vacancy(models.Model):
    title = models.TextField()
    company = models.TextField()
    link = models.TextField(unique=True)
    raw_text = models.TextField(blank=True, null=True)
    found_skills = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "vacancies"
        ordering = ["-id"]

    @property
    def skills_list(self) -> list[str]:
        if not self.found_skills:
            return []
        return [s.strip() for s in self.found_skills.split(",") if s.strip()]

    @property
    def source(self) -> str:
        if "dou.ua" in self.link:
            return "DOU"
        if "robota.ua" in self.link:
            return "Robota.ua"
        return "else"