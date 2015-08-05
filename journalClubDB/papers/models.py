from django.db import models

# This is internal journalclubDB citation data (as opposed to external pubmed citation data)
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
    pubmedID = models.PositiveIntegerField(blank=True)

# Discussion thread for a particular citation
class Thread(models.Model):
    def __str__(self):
        return self.description
    owner = models.ForeignKey(Citation)
    description = models.TextField(blank=True)

class Post(models.Model):
    def __str__(self):
        return self.text
    owner = models.ForeignKey(Thread)
    text = models.TextField(blank=True)
    pub_date = models.DateTimeField('date published')
