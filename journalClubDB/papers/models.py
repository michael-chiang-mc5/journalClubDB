from django.db import models
from django.contrib.auth.models import User

# This is internal journalclubDB citation data (as opposed to external pubmed citation data)
class Citation(models.Model):
    def __str__(self):
        return self.title

    def num_posts(self):
        return sum([t.num_posts() for t in self.thread_set.all()])

    def time_last_post(self):
        tMax = None
        for t in self.thread_set.all():
            if tMax is None:
                tMax = t.time_last_post()
            else:
                if t.time_last_post() > tMax:
                    tMax = t.time_last_post()
        return tMax

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
# Possible categories: ELI5, Methodology, Results, Discussion, Historical context
class Thread(models.Model):
    def __str__(self):
        return str(self.owner) + ' - ' + self.description

    def num_posts(self):
        return self.post_set.count()

    def time_last_post(self):
        tMax = None
        for p in self.post_set.all():
            if tMax is None:
                tMax = p.time_created
            else:
                if p.time_created > tMax:
                    tMax = p.time_created
        return tMax

    owner = models.ForeignKey(Citation)
    description = models.TextField(blank=True)

class Post(models.Model):
    def __str__(self):
        return self.text
    time_created = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(User, blank=True, null=True)
    thread = models.ForeignKey(Thread)
    isReplyToPost = models.BooleanField()
    mother = models.ForeignKey('self', blank=True, null=True)
    text = models.TextField()
    node_depth = models.PositiveIntegerField()

    # to access upvoted posts from User instance, user.upvoted.all()
    upvoters   = models.ManyToManyField(User, blank=True, related_name="upvoted")
    downvoters = models.ManyToManyField(User, blank=True, related_name="downvoted")

    # This must be recalculated every time a new reply is added to subtree
    aggregate_score_tmp = models.IntegerField(blank=True, null=True)
    ordered_index = models.IntegerField(blank=True,null=True)

    # score is a measure of post quality
    # TODO: Make score based on user quality, i.e., professors have more weight
    def score(self):
        return len(self.upvoters.all()) - len(self.downvoters.all())
