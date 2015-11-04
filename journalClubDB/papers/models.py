from django.db import models
from django.contrib.auth.models import User
import json
from bson import json_util

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
        return str(self.owner) + ' - ' + self.title

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
    title = models.TextField(blank=True)
    description = models.TextField(blank=True)

class Post(models.Model):
    def __str__(self):
        return self.text
    time_created = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(User, blank=True, null=True)
    thread = models.ForeignKey(Thread)
    isReplyToPost = models.BooleanField()
    mother = models.ForeignKey('self', blank=True, null=True)
    text = models.TextField() # json serialized
    node_depth = models.PositiveIntegerField()

    # to access upvoted posts from User instance, user.upvoted.all()
    upvoters   = models.ManyToManyField(User, blank=True, related_name="upvoted")
    downvoters = models.ManyToManyField(User, blank=True, related_name="downvoted")

    # This must be recalculated every time a new reply is added to subtree
    #aggregate_score_tmp = models.IntegerField(blank=True, null=True)
    #ordered_index = models.IntegerField(blank=True,null=True)

    # score is a measure of post quality
    # TODO: Make score based on user quality, i.e., professors have more weight
    def score(self):
        return len(self.upvoters.all()) - len(self.downvoters.all())

    def add_post(self,text,editor_pk,date_added,editor_name):
        text_tuple_vector = self.get_undecoded_textTupleVector()
        t = (text,editor_pk,date_added,editor_name)
        text_tuple_vector.append(t)
        self.text = json.dumps(text_tuple_vector, default=json_util.default)

    # v[i] = (text , editor/creator.pk , date)
    def get_undecoded_textTupleVector(self):
        if self.text == '':
            tuple_vector = []
        else:
            tuple_vector_undecoded = self.text
            tuple_vector = json.loads(tuple_vector_undecoded, object_hook=json_util.object_hook)
        return tuple_vector

class Tag(models.Model): # use http://jquery-plugins.net/bootstrap-tags-input
    def __str__(self):
        return self.name
    name = models.TextField()
    citations  = models.ManyToManyField(Citation, blank=True, related_name="tags")  # to access tags from Citation instance, citation.tags.all()

class UserProfile(models.Model):
    user = models.OneToOneField(User)
    education = models.TextField(blank=True)
    library   = models.ManyToManyField(Citation, blank=True, related_name="citation_library")
    def __str__(self):
        return self.user.username

# An object of this class stores an ordered list of citations. SUsed to determine the "Paper of the Week"
class PaperOfTheWeek(models.Model):
    citation_list = models.ManyToManyField(Citation, through='PaperOfTheWeekInfo')

class PaperOfTheWeekInfo(models.Model):
    def __str__(self):
        return str(self.citation) + ", order=" + str(self.order)
    citation = models.ForeignKey(Citation)
    paperOfTheWeek = models.ForeignKey(PaperOfTheWeek)
    order = models.FloatField()
