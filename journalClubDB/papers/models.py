from django.db import models

# This internal journalclubDB citation data (as opposed to external pubmed citation data)
class Citation(models.Model):
    def __str__(self):
        return self.title

    title = models.TextField(blank=True)
    author = models.TextField(blank=True)
    journal = models.TextField(blank=True)
    volume = models.TextField(blank=True)
    number = models.TextField(blank=True)
    pages = models.TextField(blank=True)
    date = models.TextField(blank=True)
    fullSource = models.TextField(blank=True)
    keywords = models.TextField(blank=True)
    abstract = models.TextField(blank=True)
    doi = models.TextField(blank=True)
    fullAuthorNames = models.TextField(blank=True)
    pubmedID = models.TextField(blank=True)
