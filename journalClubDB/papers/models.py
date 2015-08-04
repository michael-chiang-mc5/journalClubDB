from django.db import models

# This internal journalclubDB citation data (as opposed to external pubmed citation data)
class Citation(models.Model):
    def __str__(self):
        return self.title

    title = models.TextField(blank=True)
    author = models.TextField(blank=True)
    journal = models.TextField(blank=True)
    volume = models.PositiveSmallIntegerField(blank=True,null=True)
    number = models.PositiveSmallIntegerField(blank=True,null=True)
    pages = models.TextField(blank=True)
    year = models.PositiveSmallIntegerField(blank=True,null=True)
    publisher = models.TextField(blank=True)
