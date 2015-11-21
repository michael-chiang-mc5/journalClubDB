from django.shortcuts import render, redirect, render_to_response
from django.views import generic
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
import logging
import math
from .models import *
#from .forms import UserForm #, UserProfileForm
from .Pubmed import PubmedInterface
logger = logging.getLogger(__name__)
import time
import pickle # used to debug, remove later
import os
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
#from datetime import datetime, timedelta, timezone
import datetime
import json


def add_indent_dedent_to_post_list(post_list):
    rn =  add_indent_dedent_to_post_list_recursive(post_list,0,0,[])
    return rn

def add_indent_dedent_to_post_list_recursive(post_list,i,position_post,rn):
    if i>=len(post_list):
        return rn
    elif i==0:
        post = post_list[i]
        rn = ['in-'+str(post.node_depth),post,'out-'+str(post.node_depth)] # note that position of post = 1
        position_post = 1
        return add_indent_dedent_to_post_list_recursive(post_list,i+1,position_post,rn)
    else:
        post = post_list[i]
        previous_post = post_list[i-1]
        insert = ['in-'+str(post.node_depth),post,'out-'+str(post.node_depth)]
        if post.node_depth == previous_post.node_depth:
            rn[position_post+2:position_post+2] = insert
            position_post = (position_post+2) + 1
        elif post.node_depth > previous_post.node_depth:
            rn[position_post+1:position_post+1] = insert
            position_post = (position_post+1) + 1
        elif post.node_depth < previous_post.node_depth:
            for j in range(position_post+2,len(post_list)):
                if post_list[j] == 'out-'+str(post.node_depth):
                    rn[j+1:j+1] = insert
                    position_post = (j+1) + 1
                    break
        return add_indent_dedent_to_post_list_recursive(post_list,i+1,position_post,rn)

# rn should start an empty list
def get_post_chain(post):
    rn = get_post_chain_recursive(post,[])
    return rn[::-1] # reverse list so that most recent post is at end of the list

# rn should start an empty list
def get_post_chain_recursive(post,rn):
    rn.append(post)
    mother = post.mother
    if mother.node_depth == 0:
        return rn
    else:
        return get_post_chain_recursive(mother,rn)

def post_context(request,post_pk):

    # get post
    post = Post.objects.get(pk=post_pk)

    # get mother post chain
    posts = get_post_chain(post)

    # insert indents and dedents to post list
    posts =  add_indent_dedent_to_post_list(posts)

    # return html
    context = {'posts':posts}
    return render(request, 'papers/post_context.html', context)

def user_notifications(request):
    # get notifications
    user_profile = UserProfile().get_user_profile(request.user)
    posts = list(user_profile.post_reply_notifications.all()) # list is necessary to prevent post_reply_notifications clear from also clearing copy

    # clear notifications
    user_profile.post_reply_notifications.clear()

    # return html
    context = {'navbar':'user_profile','posts':posts, 'number_of_post_reply_notifications':len(posts)}
    return render(request, 'papers/user_notifications.html', context)

def user_library(request):
    user_profile = UserProfile().get_user_profile(request.user)
    citations = user_profile.library.all()
    context = {'navbar':'user_profile','citations':citations}
    return render(request, 'papers/user_library.html', context)

def user_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse('papers:frontpage'))

def about_contact(request):
    context = {'navbar':'about'}
    return render(request,'papers/about_contact.html', context)
def about_developers(request):
    context = {'navbar':'about'}
    return render(request,'papers/about_developers.html', context)
def about_etiquette(request):
    context = {'navbar':'about'}
    return render(request,'papers/about_etiquette.html', context)
def about_jcdb(request):
    context = {'navbar':'about'}
    return render(request,'papers/about_jcdb.html', context)
def about_privacy(request):
    context = {'navbar':'about'}
    return render(request,'papers/about_privacy.html', context)

# user login.  Code from: http://www.tangowithdjango.com/book17/chapters/login.html
def user_login(request): # login is taken up by native django function
    username = request.POST.get('username')
    password = request.POST.get('password')

    # Use Django's machinery to attempt to see if the username/password combination is valid - a User object is returned if it is.
    user = authenticate(username=username, password=password)

    # If we have a User object, the details are correct.
    # If None (Python's way of representing the absence of a value), no user
    # with matching credentials was found.
    if user:
        # Is the account active? It could have been disabled.
        if user.is_active:
            # If the account is valid and active, we can log the user in.
            # We'll send the user back to the homepage.
            login(request, user)
            return HttpResponse(True)
        else:
            # An inactive account was used - no logging in!
            return HttpResponse("Banned")
    else:
        # Bad login details were provided. So we can't log the user in.
        print("Invalid login details: {0}, {1}".format(username, password))
        return HttpResponse(False)

# add a citation to user library
def add_citation_to_user_library(request):
    citation_pk = request.POST.get("citation_pk")
    userProfile = UserProfile().get_user_profile(request.user)
    userProfile.library.add(citation_pk)
    userProfile.save()
    return detail(request,citation_pk,0)

# code from: http://stackoverflow.com/questions/1531272/django-ajax-response-for-valid-available-username-email-during-registration
def is_field_available(request):
    if request.method == "GET":
        get = request.GET.copy()
        if 'username' in get:
            name = get['username']
            if User.objects.filter(username__iexact=name):
                return HttpResponse("False")
            else:
                return HttpResponse("True")
    return HttpResponseServerError("Requires username to test")

# user registration.  Code from: http://www.tangowithdjango.com/book17/chapters/login.html
def register(request):
    username = request.POST.get("username")
    password1 = request.POST.get("password1")
    email = request.POST.get("email")
    user = User.objects.create_user(username, email, password1)
    #user.set_password(user.password) # I don't think this is necessary, should hash automatically
    user.save()
    user = authenticate(username=username, password=password1)
    login(request, user)
    message = 'Registration successful'
    return JsonResponse({'message':message})

# landing page
def frontpage(request):
    paperOfTheWeek_citation,dummy = getCitationOfTheWeek()
    context = {'paperOfTheWeek_citation': paperOfTheWeek_citation,'navbar':'home'}
    return render(request, 'papers/frontpage.html', context)

# see all citations in database
def index_deprecated(request):
    citations = Citation.objects.all()

    # Paginate
    paginator = Paginator(citations, 10) # TODO: change this to something more reasonable
    page = request.GET.get('page')
    try:
        citations = paginator.page(page)
        active_page = int(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        citations = paginator.page(1)
        active_page = 1
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        citations = paginator.page(paginator.num_pages)
        active_page = int(paginator.num_pages)

    context = {'citations': citations,'navbar':'index','num_pages':int(paginator.num_pages),'active_page':active_page}
    return render(request, 'papers/index.html', context)

# see all citations in database
def index(request):
    citations = Citation.objects.all()
    context = {'citations': citations,'navbar':'search','show_detail_link':True}
    return render(request, 'papers/index.html', context)

# returns a string, otherwise returns None
def citationSanitizer(request,field_name):
    if request.method == 'POST' and field_name in request.POST:
        f = request.POST[field_name]
        if f is not None and f != '' and f != 'None':
            return f
    return ''

# TODO: check that number of Papers of the Week does not exceed weeks elapsed
def getCitationOfTheWeek():
    t0 = datetime.date(2000, 1, 1)
    today = datetime.date.today()
    days_elapsed = (today-t0).days
    weeks_elapsed = math.floor(days_elapsed / 7)
    num_papersOfTheWeek = len(PaperOfTheWeekInfo.objects.all())
    if num_papersOfTheWeek == 0:
        return 0,0
    else:
        current_index = (weeks_elapsed + PaperOfTheWeek.objects.all()[0].offset) % num_papersOfTheWeek
        citation_pk = PaperOfTheWeekInfo.objects.order_by('order')[current_index].citation.pk
        citation = Citation.objects.get(pk=citation_pk)
        return citation,current_index

# display user profile
def self_user_profile(request):
    context = {'user': request.user, 'navbar':'user_profile'}
    return render(request, 'papers/self_user_profile.html', context)

# display user posts
def user_posts(request, user_pk):
    user = User.objects.get(pk=user_pk)
    posts = Post.objects.filter(creator=user)
    context = {'posts': posts, 'navbar':'user_profile'}
    return render(request, 'papers/user_posts.html', context)

# list all papers of the week
def paperOfTheWeek_list(request):
    paperOfTheWeekInfo_list = PaperOfTheWeekInfo.objects.order_by('order')
    context = {'paperOfTheWeekInfo_list': paperOfTheWeekInfo_list}
    return render(request, 'papers/paperOfTheWeek_list.html', context)

# admin interface to set paper of the week
def paperOfTheWeek_admin(request):

    # adding/removing citations from weekly rotation if user submits form
    if request.method == 'POST':
        addOrRemove = request.POST.get('addOrRemove')
        citation_pk = request.POST.get('citation_pk')
        order = request.POST.get('order')
        offset = request.POST.get('offset')
        if order=="":
            sorted_citations = PaperOfTheWeekInfo.objects.order_by('-order')  # TODO: sort is inefficient, better to find min
            if len(sorted_citations) == 0:
                order = 0
            else:
                order = sorted_citations[0].order + 1
        if addOrRemove == "add":
            p = PaperOfTheWeek.objects.all()[0]
            c = Citation.objects.get(pk=citation_pk)
            new_pow_entry = PaperOfTheWeekInfo(citation = c, paperOfTheWeek=p, order=order)
            new_pow_entry.save()
        elif addOrRemove == "remove":
            c = Citation.objects.get(pk=citation_pk)
            p = PaperOfTheWeekInfo.objects.filter(citation=c)
            p.delete()
        if offset!="": # set offset so that current paper of the week is correctly set
            paperOfTheWeek_list = PaperOfTheWeekInfo.objects.order_by('order')
            # find index (idx) of citation with order (o) closest to offset
            idx = 0
            diff_storage = float('inf')
            for i,p in enumerate(paperOfTheWeek_list):
                o = p.order
                diff = abs(o - float(offset))
                if diff<diff_storage:
                    diff_storage = diff
                    idx = i
            # determine modulus offset
            dummy,currentIdx = getCitationOfTheWeek()
            if idx > currentIdx:
                p = PaperOfTheWeek.objects.all()[0]
                p.offset = p.offset + (idx-currentIdx)
                p.save()
            elif idx < currentIdx:
                p = PaperOfTheWeek.objects.all()[0]
                p.offset = p.offset - (currentIdx-idx)
                p.save()

    # display citations in weekly rotation
    if len(PaperOfTheWeek.objects.all()) == 0:     # check if paperOfTheWeekObject exists. If not, create one
        paperOfTheWeek = PaperOfTheWeek()
        paperOfTheWeek.offset = 0;
        paperOfTheWeek.save()
    # this is a list of all citations used in Papers of the Week. Re-number order to be consecutive integers
    paperOfTheWeek_list = PaperOfTheWeekInfo.objects.order_by('order')
    for i,p in enumerate(paperOfTheWeek_list):
        p.order = i
        p.save()
    # get order of current paper of the week
    dummy,idx = getCitationOfTheWeek()
    if idx==0: # there is no current paper of the week
        currentOrder=0
    else:
        currentOrder = paperOfTheWeek_list[idx].order

    # this is a list of all citations not used in Papers of the Week
    nonPaperOfTheWeek_list = Citation.objects.exclude(paperoftheweekinfo__in=paperOfTheWeek_list)
    context = {'paperOfTheWeek_list': paperOfTheWeek_list, 'nonPaperOfTheWeek_list':nonPaperOfTheWeek_list, 'currentOrder':currentOrder}
    return render(request, 'papers/paperOfTheWeek_admin.html', context)


def add_tag(request):
    if request.method == 'POST':
        citation_pk = request.POST.get('citation_pk',False)
        current_thread = request.POST.get('current_thread',False)
        tag_name = request.POST.get('tag_name',False)
        # check if tag already exists
        if Tag.objects.filter(name=tag_name).exists():
            tag = Tag.objects.filter(name=tag_name)[0]
            if not tag.citations.filter(pk=citation_pk).exists():
                tag.citations.add(citation_pk)
                tag.save()
        else:
            tag = Tag()
            setattr(tag,'name',tag_name)
            tag.save()
            tag.citations.add(citation_pk)
            tag.save()
        return HttpResponseRedirect(reverse('papers:detail', args=[citation_pk,current_thread]))

# To open: import pickle; favorite_color = pickle.load( open( "save.p", "rb" ) )
def save_object(obj, filename):
    with open(filename, 'wb') as output:
        pickle.dump(obj, output, pickle.HIGHEST_PROTOCOL)

def load_object(filename):
    return pickle.load( open( filename, "rb" ) )

def safe_text(initial_text):
    initial_text = initial_text.replace("\r","")
    initial_text = initial_text.replace("\n","")
    initial_text = initial_text.replace('"',"'")
    initial_text = initial_text.replace("\\","\\\\")
    return initial_text

def postForm(request):
    thread_pk = request.POST.get("thread_pk")
    citation_pk = request.POST.get("citation_pk")
    citation = request.POST.get("citation")
    thread_title = request.POST.get("thread_title")
    thread_description = request.POST.get("thread_description")
    isReplyToPost = request.POST.get("isReplyToPost")
    mother_pk = request.POST.get("mother_pk")
    current_thread = request.POST.get("current_thread") # pane id
    initial_text = request.POST.get("initial_text")
    post_pk = request.POST.get("post_pk")
    edit_or_reply = request.POST.get("edit_or_reply")


    blockquote = request.POST.get("blockquote")
    if blockquote == "True":
        initial_text = safe_text(initial_text)
        initial_text = "<blockquote>" + initial_text + "</blockquote>" + "<br >"
    else:
        initial_text = safe_text(initial_text)

    context={'citation':citation,'citation_pk':citation_pk,'thread_title':thread_title,'thread_description':thread_description,'thread_pk':thread_pk,'isReplyToPost':isReplyToPost,'mother_pk':mother_pk,'current_thread':current_thread,'initial_text':initial_text,'post_pk':post_pk,'edit_or_reply':edit_or_reply}
    return render(request, 'papers/postForm.html', context)

def personalNoteForm(request):
    citation_pk = request.POST.get("citation_pk")
    citation = Citation.objects.get(pk=citation_pk)
    user = request.user
    personal_note = PersonalNote().get_personal_note(user,citation)
    initial_text = personal_note.text
    initial_text = safe_text(initial_text)
    context={'citation':citation,'initial_text':initial_text}
    return render(request, 'papers/personalNoteForm.html', context)

def editPersonalNote(request):
    user = request.user
    citation_pk = request.POST.get("citation_pk")
    citation = Citation.objects.get(pk=citation_pk)
    personal_note = PersonalNote().get_personal_note(user,citation)
    new_text = request.POST.get("text")
    personal_note.text = new_text
    personal_note.save()
    return HttpResponseRedirect(reverse('papers:detail', args=[citation_pk,5]))

# add post
# TODO: add sanity checks that user is authenticated and is correct user
def addPost(request):
    edit_or_reply = request.POST.get("edit_or_reply", False)
    if edit_or_reply == "edit":
        new_text = request.POST.get("text", False)
        post_pk = request.POST.get("post_pk", False)
        post = Post.objects.get(pk=post_pk)
        citation_pk = request.POST.get("citation_pk", False)
        thread_number = post.thread.order #request.POST.get("current_thread", False)
        post.add_post(new_text,request.user.pk,datetime.datetime.now(datetime.timezone.utc),request.user.username)
        setattr(post,'time_created',datetime.datetime.now())
        post.save()
        return HttpResponseRedirect(reverse('papers:detail', args=[citation_pk,thread_number])+'#post-'+str(post.pk))
    elif edit_or_reply == "reply":
        # get POST data
        thread_pk = int(request.POST.get("thread_pk", False))
        citation_pk = request.POST.get("citation_pk", False)
        is_reply_to_post = bool(int(request.POST.get("isReplyToPost", False)))
        mother_pk = int(request.POST.get("mother_pk", False))
        text = request.POST.get("text", False)
        thread_number = Thread.objects.get(pk=thread_pk).order #request.POST.get("current_thread", False)
        post = Post()
        setattr(post,'time_created',datetime.datetime.now())
        setattr(post,'creator',request.user)
        setattr(post,'thread',Thread.objects.get(pk=thread_pk))
        setattr(post,'isReplyToPost', True) # TODO: pick a better variable name, base_node?
        if is_reply_to_post: # TODO: pick a better name, is_submission?
            setattr(post,'mother',Post.objects.get(pk=mother_pk))
            setattr(post,'node_depth', Post.objects.get(pk=mother_pk).node_depth + 1)
        else:
            setattr(post,'mother', Post.objects.get(thread=thread_pk,isReplyToPost=False))
            setattr(post,'node_depth',1)
        post.add_post(text,request.user.pk,datetime.datetime.now(datetime.timezone.utc),request.user.username)
        post.save() # TODO: This may not be necessary
        post.upvoters.add(request.user)
        post.save()
        post.notify_mother_author()         # notify author of mother post that you replied to him
        return HttpResponseRedirect(reverse('papers:detail', args=[citation_pk,thread_number])+'#post-'+str(post.pk))

def addCitation_deprecated(request):
    # check for duplicate citations.  If citation already exists, return primary key of the citation
    pubmedID = request.POST['pubmedID']
    citations = Citation.objects.filter(pubmedID=pubmedID)
    if len(citations) is not 0:
        citation_url = reverse('papers:detail',args=[citations[0].pk])
        return JsonResponse({'new_citation_url':citation_url})

    # Create citation
    citation = Citation()
    field_list = ["title", "author", "journal", "volume","number","pages","date","fullSource","keywords","abstract","doi","fullAuthorNames","pubmedID"]
    for f in field_list:
        field_entry = citationSanitizer(request,f)
        setattr(citation,f,field_entry)
    citation.save()

    # Create threads and master post
    thread_titles = ["Explain Like I'm Five","Methodology","Results","Historical Context"]
    thread_descriptions = ["Easy to understand summary of the paper",
                           "Description of innovative methodologies",
                           "Description of main results of the paper",
                           "How does the paper fit into the pre-existing literature"]
    ordering = [1,2,3,4]
    for title,description,order in zip(thread_titles,thread_descriptions,ordering):
        thread = Thread()
        setattr(thread,'owner',citation)
        setattr(thread,'title',title)
        setattr(thread,'description',description)
        setattr(thread,'order',order)
        thread.save()
        post = Post()
        post = Post(time_created=datetime.datetime.now(),thread=thread,
                    isReplyToPost=False,text="",node_depth=0)
        post.save()

    # Return url to new citation detail page
    new_citation_url = reverse('papers:detail',args=[citation.pk,0])
    return JsonResponse({'new_citation_url':new_citation_url})

def addCitation(request):
    citation_data_serialized = request.POST['citation_serialized']
    citation = Citation()
    citation.deserialize(citation_data_serialized)
    citation_pk = citation.save_if_unique()
    # Return url to new citation detail page
    new_citation_url = reverse('papers:detail',args=[citation_pk,0])
    return HttpResponse(new_citation_url)

# returns ordered list of posts.  Ordering is greedy
# Input post_list should constitute a full tree with a single base node (no error checking)
def order_greedy_post_list_with_indents(post_list):
    # childrenIdx_list[i] gives the indices of children of post_list[i]
    childrenIdx_list = [None] * len(post_list)
    for j,post in enumerate(post_list):
        children = post.post_set.all()
        children_idx = []
        for child in children:
            child_idx = None
            for i,p in enumerate(post_list):
                if child.pk is p.pk:
                    child_idx = i
                    break
            children_idx.append(child_idx)
        childrenIdx_list[j] = children_idx

    # get base node of post tree
    idx_baseNode = None
    for i,post in enumerate(post_list):
        if post.node_depth is 0:
            idx_baseNode = i
            break

    # order post_list
    ordered_indices = orderGreedyPostlist_with_indents(idx_baseNode, post_list, childrenIdx_list,True)
    ordered_post_list = []
    for i,post in enumerate(ordered_indices):
        if type(ordered_indices[i]) is str: #.startswith('in') or ordered_indices[i].startswith('out'):
            ordered_post_list.append(ordered_indices[i])
        else:
            ordered_post_list.append(post_list[ ordered_indices[i] ])
    return ordered_post_list # note this is no longer a queryset


# Returns a list of indices corresponding to an ordered post_list
# ordered[i] = j means that the jth element of post_list belongs in slot i of ordered list
def orderGreedyPostlist_with_indents(node_idx, post_list, childrenIdx_list,withIndents):
    children_indices = childrenIdx_list[node_idx]
    num_children = len(children_indices)

    if num_children is 0:
        if withIndents:
            return ['in-'+str(post_list[node_idx].node_depth),node_idx,'out-'+str(post_list[node_idx].node_depth)]
        else:
            return [node_idx]
    else:
        # create tuple list [ (aggregateScore, index), ...] which is sorted by aggregateScore
        tup = [None] * len(children_indices)
        for i,child_idx in enumerate(children_indices):
            score = post_list[child_idx].score()
            tup[i] = (score,child_idx)
        tup = sorted(tup, reverse=True)
        if withIndents:
            ordered = ['in-'+str(post_list[node_idx].node_depth),node_idx]
        else:
            ordered = [node_idx]
        for t in tup:
            score = t[0]
            child_idx = t[1]
            o = orderGreedyPostlist_with_indents(child_idx,post_list,childrenIdx_list,withIndents)
            if withIndents:
                ordered = ordered + o
            else:
                ordered = ordered + o
        if withIndents:
            ordered = ordered + ['out-'+str(post_list[node_idx].node_depth)]
        return ordered


# internal citation information
def detail(request,pk,current_thread):
    citation = Citation.objects.get(pk=pk)
    threads = Thread.objects.filter(owner=pk).order_by('order')
    associated_tags = citation.tags.all()
    unused_tags = Tag.objects.exclude(id__in=associated_tags)
    posts_vector = []
    num_depth1_posts = [] # number of depth 1 comments used for display
    for thread in threads:
        posts = Post.objects.filter(thread=thread.pk)
        ordered_posts = order_greedy_post_list_with_indents(posts) # ordered_posts is not a queryset
        ordered_posts = ordered_posts[2:-1] # exclude first entry (dummy post) along with indents/dedents
        posts_vector.append(ordered_posts)
        num_depth1_posts.append(len(posts.filter(node_depth=1)))
    threadsPostsIndents = zip(threads,posts_vector,num_depth1_posts)

    # check if citation already is in user library
    # citationIsInLibrary True if user is authenticated and citation is in library, false otherwise
    try:
        userProfile = UserProfile().get_user_profile(request.user)
        userProfile.library.get(pk=pk)
    except:
        citationIsInLibrary = False
    else:
        citationIsInLibrary = True

    # get user's personal note for the citation
    personalNote = PersonalNote().get_personal_note(request.user,citation)

    context = {'personalNote':personalNote,'citation': citation,'threads': threads,'posts_vector':posts_vector,'threadsPostsIndents':threadsPostsIndents,'current_thread':int(current_thread),'associated_tags':associated_tags,'unused_tags':unused_tags, 'citationIsInLibrary':citationIsInLibrary}
    return render(request, 'papers/detail.html', context)

# upvote comment
# assumes that user is authenticated
def upvote(request):
    post_pk = request.POST.get("post_pk")
    post = Post.objects.get(pk=post_pk)

    # clear upvote if user already upvoted
    if post.upvoters.filter(id=request.user.pk).exists():
        post.upvoters.remove(request.user)
    # upvote if user has not already upvoted
    else:
        post.upvoters.add(request.user)
        post.downvoters.remove(request.user)

    return JsonResponse({'score':post.score()})

def downvote(request):
    post_pk = request.POST.get("post_pk")
    post = Post.objects.get(pk=post_pk)

    # clear downvote if user already downvoted
    if post.downvoters.filter(id=request.user.pk).exists():
        post.downvoters.remove(request.user)
    # downvote if user has not already downvoted
    else:
        post.downvoters.add(request.user)
        post.upvoters.remove(request.user)

    return JsonResponse({'score':post.score()})


# check pubmed search results against internal database
def checkPubmedEntriesForPreexistingCitations(pubmed):
    for i,entry in enumerate(pubmed.entries):
        pubmedID = entry.pubmedID
        matches = Citation.objects.filter(pubmedID=pubmedID)
        num_matches = len(matches)
        if num_matches is 0:
            pubmed.entries[i].preexistingEntry = False
            pubmed.entries[i].preexistingEntry_pk = None
        else:
            pubmed.entries[i].preexistingEntry = True
            pubmed.entries[i].preexistingEntry_pk = matches[0].pk
    return pubmed

# search interface
def search0(request,page):
    pubmed = PubmedInterface()
    search_str = ''
    totalPages=0
    pageNumber=0
    if request.method == 'POST': # either search initiated or page change
        searchInitiated = request.POST.get("searchInitiated")
        if searchInitiated == "True": # search initiated
            search_str = request.POST.get("search_str")
            pubmed.countNumberSearchResults(search_str)
            numberSearchResults = pubmed.numberSearchResults
            totalPages = math.ceil(numberSearchResults/10)
            pageNumber=1
            retMin = 0
            retMax = 10
            citations = Citation.objects.all()
            pubmed.getRecords(search_str,retMin,retMax)
        else: # page change
            search_str = request.POST.get("search_str")
            pageNumber = int(request.POST.get("pageNumber"))
            retMin = (pageNumber - 1)*10
            retMax = 10
            citations = Citation.objects.all()
            pubmed.getRecords(search_str,retMin,retMax)
            totalPages = int(request.POST.get("totalPages"))
        freshSearch=False
    else:
        freshSearch=True

    totalPages = min([totalPages,15+1]) # maximum of 15 pages
    pubmed = checkPubmedEntriesForPreexistingCitations(pubmed)
    context = {'entries': pubmed.entries, 'search_str': search_str, 'totalPages':totalPages, 'totalPagesRange': range(1,totalPages), 'pageNumber': pageNumber, 'freshSearch': freshSearch, 'navbar':'addCitation'}
    return render(request, 'papers/search0.html', context)


# search interface
def search(request,page):

    ## This is to debug without repeatedly querying pubmed
    json_str = load_object('deleteMe.pkl')
    json_object = json.loads(json_str)
    articles_json = json_object['PubmedArticle']
    try:    # multiple articles
        citations = []
        for article_json in articles_json:
            citation = Citation()
            citation.parse_pubmedJson(article_json)
            citations.append(citation)
    except: # single article
        citations = []
        citation = Citation()
        citation.parse_pubmedJson(articles_json)
        citations.append(citation)

    search_bar_placeholder = "Search pubmed ... "

    # client has passed us POST data containing Pubmed xml
    # we will create list of citation objects from post data and pass it back
    if request.method == 'POST':
        search_bar_placeholder = request.POST.get("search_bar_placeholder")
        json_str = request.POST.get("json_str")
        save_object(json_str, 'deleteMe.pkl')
        json_object = json.loads(json_str)
        articles_json = json_object['PubmedArticle']
        try:    # multiple articles
            citations = []
            for article_json in articles_json:
                citation = Citation()
                citation.parse_pubmedJson(article_json)
                citations.append(citation)
        except: # single article
            citations = []
            citation = Citation()
            citation.parse_pubmedJson(articles_json)
            citations.append(citation)

    context = {'navbar':'search','is_search_results':True,'citations':citations,'search_bar_placeholder':search_bar_placeholder}
    return render(request, 'papers/search.html', context)
