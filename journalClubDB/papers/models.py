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
    # optional fields
    link = models.TextField(blank=True,null=True) # link to pdf or something else

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
    order = models.PositiveIntegerField()

class Post(models.Model):
    def __str__(self):
        return self.text
    time_created = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(User, blank=True, null=True)
    thread = models.ForeignKey(Thread)
    isReplyToPost = models.BooleanField()
    mother = models.ForeignKey('self', blank=True, null=True)
    text = models.TextField() # json serialized
    node_depth = models.PositiveIntegerField() # base node posts have a node depth of 0

    # to access upvoted posts from User instance, user.upvoted.all()
    upvoters   = models.ManyToManyField(User, blank=True, related_name="upvoted")
    downvoters = models.ManyToManyField(User, blank=True, related_name="downvoted")

    # score is a measure of post quality
    # TODO: Make score based on user quality, i.e., professors have more weight
    def score(self):
        return len(self.upvoters.all()) - len(self.downvoters.all())

    def add_post(self,text,editor_pk,date_added,editor_name):
        text_tuple_vector = self.get_undecoded_textTupleVector()
        t = (text,editor_pk,date_added,editor_name)
        text_tuple_vector.append(t)
        self.text = json.dumps(text_tuple_vector, default=json_util.default)

    def notify_mother_author(self):
        # get mother post
        mother = Post.objects.get(pk=self.mother.pk)

        # if mother is base node, do nothing
        if mother.node_depth == 0:
            return

        # get author of mother post
        mother_author = User.objects.get(pk=mother.creator.pk)

        # if author of the current post is the same as the author of the
        # mother post (i.e., if somebody replied to himself) then do nothing
        if mother_author.pk == self.creator.pk:
            return

        # notify author of mother post that somebody responded
        mother_user_profile = UserProfile().get_user_profile(mother_author)
        mother_user_profile.post_reply_notifications.add(self)
        mother_user_profile.save()
        return

    # v[i] = (text , editor/creator.pk , date)
    def get_undecoded_textTupleVector(self):
        if self.text == '':
            tuple_vector = []
        else:
            tuple_vector_undecoded = self.text
            tuple_vector = json.loads(tuple_vector_undecoded, object_hook=json_util.object_hook)
        return tuple_vector

    def get_most_recent_edit(self):
        all_edits = self.get_undecoded_textTupleVector()
        if all_edits == []:
            rn = []
        else:
            for edit in all_edits:
                pass
            rn = []
        return rn

class Tag(models.Model): # use http://jquery-plugins.net/bootstrap-tags-input
    def __str__(self):
        return self.name
    name = models.TextField()
    citations  = models.ManyToManyField(Citation, blank=True, related_name="tags")  # to access tags from Citation instance, citation.tags.all()

class UserProfile(models.Model):
    user = models.OneToOneField(User)
    education = models.TextField(blank=True)
    library   = models.ManyToManyField(Citation, blank=True, related_name="userProfiles") # to access user profiles from Citation instance, citation.userProfiles.all()
    post_reply_notifications = models.ManyToManyField(Post, blank=True)

    def __str__(self):
        return self.user.username

    # check if user profile exists for user, if not then create one and save to database. Input argument user should be User object
    # Example usage: userProfile = UserProfile().get_user_profile(user)
    def get_user_profile(self,user):
        try:
            userProfile = UserProfile.objects.get(user=user)
        except:
            userProfile = UserProfile()
            userProfile.user = user
            userProfile.save()
            return userProfile
        else:
            return userProfile

# An object of this class stores an ordered list of citations. SUsed to determine the "Paper of the Week"
class PaperOfTheWeek(models.Model):
    citation_list = models.ManyToManyField(Citation, through='PaperOfTheWeekInfo')
    offset = models.PositiveIntegerField(blank=True) # used to set current paper of the week

class PaperOfTheWeekInfo(models.Model):
    def __str__(self):
        return str(self.citation) + ", order=" + str(self.order)
    citation = models.ForeignKey(Citation)
    paperOfTheWeek = models.ForeignKey(PaperOfTheWeek)
    order = models.FloatField()
