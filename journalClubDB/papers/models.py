from django.db import models

# This internal journalclubDB citation data (as opposed to external pubmed citation data)
class Citation(models.Model):
    def __str__(self):
        return self.title
    title = models.TextField()
    author = models.TextField()
    journal = models.TextField()
    volume = models.PositiveSmallIntegerField()
    number = models.PositiveSmallIntegerField()
    pages = models.TextField()
    year = models.PositiveSmallIntegerField()
    publisher = models.TextField()
