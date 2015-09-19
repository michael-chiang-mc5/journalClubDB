from django.shortcuts import render, redirect
from django.views import generic
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
import logging
import math
from .models import Citation, Thread, Post
#from .forms import UserForm #, UserProfileForm
from .Pubmed import PubmedInterface
logger = logging.getLogger(__name__)
import time
import pickle # used to debug, remove later
import os
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from datetime import datetime, timedelta, timezone


def user_logout(request):
    logout(request)
    return HttpResponseRedirect('/')

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

# see all citations in database
def index(request):
    template_name = 'papers/index.html'
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

    context = {'citations': citations,'navbar':'home','num_pages':int(paginator.num_pages),'active_page':active_page}
    return render(request, 'papers/index.html', context)

# returns a string, otherwise returns None
def citationSanitizer(request,field_name):
    if request.method == 'POST' and field_name in request.POST:
        f = request.POST[field_name]
        if f is not None and f != '' and f != 'None':
            return f
    return ''

def save_object(obj, filename):
    with open(filename, 'wb') as output:
        pickle.dump(obj, output, pickle.HIGHEST_PROTOCOL)

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
        initial_text = initial_text.replace("\r","")
        initial_text = initial_text.replace("\n","")
        initial_text = "<blockquote>" + initial_text + "</blockquote>" + "<br >"
    else:
        initial_text = initial_text.replace("\r","")
        initial_text = initial_text.replace("\n","")

    #initial_text = initial_text.replace("\\","a")
    initial_text = initial_text.replace('"',"'")
    initial_text = initial_text.replace("\\","\\\\")


    save_object(initial_text,'asdf.pkl')
    #return HttpResponse(initial_text)
    #initial_text = '<p>test comment edited&nbsp;<span class=dfdmath-texsd>a(x = {-b apm asqrt{b^2-4ac} aover 2a}a)</span></p>'
    context={'citation':citation,'citation_pk':citation_pk,'thread_title':thread_title,'thread_description':thread_description,'thread_pk':thread_pk,'isReplyToPost':isReplyToPost,'mother_pk':mother_pk,'current_thread':current_thread,'initial_text':initial_text,'post_pk':post_pk,'edit_or_reply':edit_or_reply}
    return render(request, 'papers/postForm.html', context)

# add post
# TODO: add sanity checks that user is authenticated and is correct user
def addPost(request):
    edit_or_reply = request.POST.get("edit_or_reply", False)
    if edit_or_reply == "edit":
        new_text = request.POST.get("text", False)
        post_pk = request.POST.get("post_pk", False)
        post = Post.objects.filter(pk=post_pk).all()[0]
        citation_pk = request.POST.get("citation_pk", False)
        current_thread = request.POST.get("current_thread", False)
        post.add_post(new_text,request.user.pk,datetime.now(timezone.utc),request.user.username)
        setattr(post,'time_created',datetime.now())
        post.save()
        return HttpResponseRedirect(reverse('papers:detail', args=[citation_pk,current_thread]))
    elif edit_or_reply == "reply":
        # get POST data
        thread_pk = int(request.POST.get("thread_pk", False))
        citation_pk = request.POST.get("citation_pk", False)
        is_reply_to_post = bool(int(request.POST.get("isReplyToPost", False)))
        mother_pk = int(request.POST.get("mother_pk", False))
        text = request.POST.get("text", False)
        current_thread = request.POST.get("current_thread", False)

        post = Post()
        setattr(post,'time_created',datetime.now())
        setattr(post,'creator',request.user)
        setattr(post,'thread',Thread.objects.get(pk=thread_pk))
        setattr(post,'isReplyToPost', True) # TODO: pick a better variable name, base_node?
        if is_reply_to_post: # TODO: change name to is_submission?
            setattr(post,'mother',Post.objects.get(pk=mother_pk))
            setattr(post,'node_depth', Post.objects.get(pk=mother_pk).node_depth + 1)
        else:
            setattr(post,'mother', Post.objects.get(thread=thread_pk,isReplyToPost=False))
            setattr(post,'node_depth',1)
        post.add_post(text,request.user.pk,datetime.now(timezone.utc),request.user.username)
        post.save()
        post.upvoters.add(request.user)
        post.save()
        return HttpResponseRedirect(reverse('papers:detail', args=[citation_pk,current_thread]))

def addCitation(request):
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
    thread_titles = ["Explain Like I'm Five","Methodology","Results","Historical Context","Discussion"]
    thread_descriptions = ["Easy to understand summary of the paper",
                           "Description of innovative methodologies",
                           "Description of main results of the paper",
                           "How does the paper fit into the pre-existing literature",
                           "Discuss!!"]
    for title,description in zip(thread_titles,thread_descriptions):
        thread = Thread()
        setattr(thread,'owner',citation)
        setattr(thread,'title',title)
        setattr(thread,'description',description)
        thread.save()
        post = Post()
        post = Post(time_created=datetime.now(),creator=request.user,thread=thread,
                    isReplyToPost=False,text="",node_depth=0)
        post.save()

    # Return url to new citation detail page
    new_citation_url = reverse('papers:detail',args=[citation.pk,0])
    return JsonResponse({'new_citation_url':new_citation_url})



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
    threads = Thread.objects.filter(owner=pk)
    posts_vector = []
    num_depth1_posts = [] # number of depth 1 comments used for display
    for thread in threads:
        posts = Post.objects.filter(thread=thread.pk)
        ordered_posts = order_greedy_post_list_with_indents(posts) # ordered_posts is not a queryset
        ordered_posts = ordered_posts[2:-1] # exclude first entry (dummy post) along with indents/dedents
        posts_vector.append(ordered_posts)
        num_depth1_posts.append(len(posts.filter(node_depth=1)))

    threadsPostsIndents = zip(threads,posts_vector,num_depth1_posts)
    context = {'citation': citation,'threads': threads,'posts_vector':posts_vector,'threadsPostsIndents':threadsPostsIndents,'current_thread':int(current_thread)}
    return render(request, 'papers/detail.html', context)

# search is terribly slow.  Use this for development
def search_development(request,page):
    with open('/Users/mcah5a/Desktop/projects/journalClubDB/journalClubDB/pubmedObject.pkl','rb') as input:
        pubmed = pickle.load(input)
    search_str = 'asdf'
    totalPages=0
    pageNumber=0
    searchInitiated = "True"
    search_str = 'asdf'
    numberSearchResults = 4
    totalPages = math.ceil(numberSearchResults/10)
    pageNumber=1
    retMin = 0
    retMax = 10
    freshSearch=False
    totalPages = min([totalPages,15+1]) # maximum of 15 pages
    pubmed = checkPubmedEntriesForPreexistingCitations(pubmed)
    context = {'navbar':'addCitation','entries': pubmed.entries, 'search_str': search_str, 'totalPages':totalPages, 'totalPagesRange': range(1,totalPages), 'pageNumber': pageNumber, 'freshSearch': freshSearch}
    return render(request, 'papers/search.html', context)

# upvote comment
# assumes that user is authenticated
def upvote(request):
    post_pk = request.POST.get("post_pk")
    post = Post.objects.get(pk=post_pk)
    post.upvoters.add(request.user)
    post.downvoters.remove(request.user)
    post.save()
    return JsonResponse({'score':post.score()})

def downvote(request):
    post_pk = request.POST.get("post_pk")
    post = Post.objects.get(pk=post_pk)
    post.upvoters.remove(request.user)
    post.downvoters.add(request.user)
    post.save()
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
def search(request,page):
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
    context = {'entries': pubmed.entries, 'search_str': search_str, 'totalPages':totalPages, 'totalPagesRange': range(1,totalPages), 'pageNumber': pageNumber, 'freshSearch': freshSearch}
    return render(request, 'papers/search.html', context)
