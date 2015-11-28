from django.db import models
from django.contrib.auth.models import User
import json
from bson import json_util
import ast
import datetime

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

    def get_author_list_truncated(self):
        authors = self.eval('authors')
        if len(authors) is 1: # case where there is only one author
            author = authors[0]
            return author['initials'] + ' ' + author['last_name']
        else:   # case where there are multiple authors
            return authors[0]['last_name'] + ' et al'
    def get_author_list(self):
        authors = self.eval('authors')
        if len(authors) is 1: # case where there is only one author
            author = authors[0]
            if author['first_name'][-2] == ' ':
                full_name = author['first_name'] + '. ' + author['last_name']
            else:
                full_name = author['first_name'] + ' ' + author['last_name']
            return full_name
        else:   # case where there are multiple authors TODO: implement this
            rn = ''
            for author in authors[:-1]:
                if author['first_name'][-2] == ' ':
                    rn += author['first_name'] + '. ' + author['last_name']
                else:
                    rn += author['first_name'] + ' ' + author['last_name']
                rn += ", "
            # last name is special case
            rn += "and "
            author = authors[-1]
            if author['first_name'][-2] == ' ':
                rn += author['first_name'] + '. ' + author['last_name']
            else:
                rn += author['first_name'] + ' ' + author['last_name']
            rn += '.'
            return rn

    def filled_field(self,fieldname):
        if not getattr(self,fieldname): # check if NoneType
            return False
        if len(getattr(self,fieldname))==0: # entry is ''
            return False
        return True

    # Returns -1 if no preexisting Citation object with matching pubmed ID
    # Returns pk of preexisting object otherwise
    def preExistingEntryExists(self):
        my_pk = self.eval('pubmedID')
        try:
            citation = Citation.objects.get(pubmedID=my_pk)
        except:
            return -1
        else:
            return citation.pk

    def get_source(self):
        source = "<i>" + self.journal +"</i>"
        if self.filled_field('volume'):
            source += ' ' + self.volume
        if self.filled_field('number'):
            source += ", no. " + self.number
        source += " (" + self.get_year_published() + ')'
        if self.filled_field('pages'):
            source += ": " + self.pages
        source += "."
        return source
    def get_journal(self):
        return self.journal
    def get_year_published(self):
        date_dict = self.eval('pubDate')
        try:
            year = date_dict['Year']
        except:
             year = date_dict['MedlineDate']
        return year
    def serialize(self):
        d = self.__dict__
        d.pop("_state", None)
        return str(d)
    def deserialize(self,str):
        d = ast.literal_eval(str)
        for key in d.keys():
            if key == 'id' or key == 'pk' or key == '_state':
                continue
            setattr(self,key,d[key])
    def eval(self,fieldname):
        try:
            rn = ast.literal_eval(getattr(self,fieldname))
        except:
            rn = getattr(self,fieldname)
        return rn

    def create_associated_threads_posts(self):
        # TODO: add error checking to make sure not already created
        thread_titles = ["Explain Like I'm Five","Methodology","Results","Historical Context"]
        thread_descriptions = ["Easy to understand summary of the paper",
                               "Description of innovative methodologies",
                               "Description of main results of the paper",
                               "How does the paper fit into the pre-existing literature"]
        ordering = [1,2,3,4]
        for title,description,order in zip(thread_titles,thread_descriptions,ordering):
            thread = Thread()
            setattr(thread,'owner',self)
            setattr(thread,'title',title)
            setattr(thread,'description',description)
            setattr(thread,'order',order)
            thread.save()
            post = Post()
            post = Post(time_created=datetime.datetime.now(),thread=thread,
                        isReplyToPost=False,text="",node_depth=0)
            post.save()

    # saves object if it does not already exist in database (based on pubmed ID)
    # also creates associated threads and posts
    # returns pk of self, or of matching db entry
    def save_if_unique(self):
        try:
            citation = Citation.objects.get(pubmedID=self.pubmedID)
        except: # does not exist in database
            self.save()
            self.create_associated_threads_posts()
            return self.pk
        else:
            return citation.pk


    # parses a json string from pubmed into self
    def parse_pubmedJson(self,json_object):
        parsed_data = self.pubmedJson_to_dict(json_object)

        fieldnames = list(self.__dict__.keys())
        for fieldname in fieldnames:
            try:
                setattr(self,fieldname,parsed_data[fieldname])
            except:
                pass

    def pubmedJson_to_dict(self,json_object):
        parsed_data = dict()

        # There is no try/except because we want to be sure we are working with a proper pubmed json object
        medline_data = json_object['MedlineCitation']
        parsed_data['pubmedID'] = medline_data['PMID']
        citation_data = medline_data['Article']

        try:
            parsed_data['keywords'] = medline_data['KeywordList']
        except:
            pass
        try:
            parsed_data['mesh_keywords'] = medline_data['MeshHeadingList']['MeshHeading']
        except:
            pass
        try:
            parsed_data['PublicationType'] = citation_data['PublicationTypeList']['PublicationType']
        except:
            pass
        try:
            parsed_data['doi'] = citation_data['ELocationID']
        except:
            pass
        try:
            parsed_data['abstract'] = citation_data['Abstract']['AbstractText']
        except:
            pass
        try:
            parsed_data['pages'] = citation_data['Pagination']['MedlinePgn']
        except:
            pass
        try:
            parsed_data['number'] = citation_data['Journal']['JournalIssue']['Issue']
        except:
            pass
        try:
            parsed_data['volume'] = citation_data['Journal']['JournalIssue']['Volume']
        except:
            pass
        try:
            parsed_data['pubDate'] = citation_data['Journal']['JournalIssue']['PubDate']
        except:
            pass
        try:
            parsed_data['journal'] = citation_data['Journal']['Title']
        except:
            pass
        try:
            parsed_data['journalAbbreviated'] = citation_data['Journal']['ISOAbbreviation']
        except:
            pass
        try:
            parsed_data['title'] = citation_data['ArticleTitle']
        except:
            pass

        authors = citation_data['AuthorList']['Author']
        parsed_author_data = []
        try: # case with more than one author
            for author in authors:
                single_author = dict()
                single_author['first_name'] = author['ForeName'] # this includes middle initial
                single_author['initials'] = author['Initials'] # this includes middle initial
                single_author['last_name'] = author['LastName']
                parsed_author_data.append(single_author)
            parsed_data['authors'] = parsed_author_data
        except: # case with only one author
            single_author = dict()
            single_author['first_name'] = authors['ForeName'] # this includes middle initial
            single_author['initials'] = authors['Initials'] # this includes middle initial
            single_author['last_name'] = authors['LastName']
            parsed_author_data.append(single_author)
            parsed_data['authors'] = parsed_author_data
        return parsed_data

    title = models.TextField(blank=True,null=True)
    authors = models.TextField(blank=True,null=True)
    journal = models.TextField(blank=True,null=True)
    journalAbbreviated = models.TextField(blank=True,null=True)
    volume = models.TextField(blank=True,null=True)
    number = models.TextField(blank=True,null=True)
    pages = models.TextField(blank=True,null=True)
    pubDate = models.TextField(blank=True,null=True)
    keywords = models.TextField(blank=True,null=True)
    mesh_keywords = models.TextField(blank=True,null=True)
    abstract = models.TextField(blank=True,null=True)
    doi = models.TextField(blank=True,null=True)
    pubmedID = models.PositiveIntegerField(blank=True,null=True)
    link = models.TextField(blank=True,null=True) # link to pdf

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

class PersonalNote(models.Model):
    def __str__(self):
        return self.text
    user = models.ForeignKey(User)
    citation = models.ForeignKey(Citation)
    text = models.TextField(default='<p>These are your personal notes. Only you can read them</p>')

    # check if user profile exists for user/citation, if not then create one and save to database. Input argument user should be User object, citation object
    # Example usage: personalNote = PersonalNote().get_user_profile(user,citation)
    def get_personal_note(self,user,citation):
        if user.is_authenticated() == False:         # if user not logged in
            return "not authenticated"
        else:
            try:
                personalNote = PersonalNote.objects.filter(user=user).get(citation=citation)
            except:
                personalNote = PersonalNote()
                personalNote.user = user
                personalNote.citation = citation
                personalNote.save()
                return personalNote
            else:
                return personalNote


class Post(models.Model):
    def __str__(self):
        return self.text
    time_created = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(User, blank=True, null=True)
    thread = models.ForeignKey(Thread)
    isReplyToPost = models.BooleanField()   # TODO: This may be unnecessary
    mother = models.ForeignKey('self', blank=True, null=True)
    text = models.TextField() # json serialized
    node_depth = models.PositiveIntegerField() # base node posts have a node depth of 0
    deleted = models.BooleanField(default=False)
    # to access upvoted posts from User instance, user.upvoted.all()
    upvoters   = models.ManyToManyField(User, blank=True, related_name="upvoted")
    downvoters = models.ManyToManyField(User, blank=True, related_name="downvoted")

    # score is a measure of post quality
    # TODO: Make score based on user quality, i.e., professors have more weight
    def score(self):
        if self.deleted:
            return -999999
        else:
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
