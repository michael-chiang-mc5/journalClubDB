from django.shortcuts import render, redirect
from django.views import generic
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
import logging
import math
from .models import Citation, Thread, Post
from .Pubmed import PubmedInterface
logger = logging.getLogger(__name__)
import time
import pickle # used to debug, remove later
import os
from django.http import JsonResponse
import datetime

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

def postForm(request):
    thread_pk = request.POST.get("thread_pk")
    citation_pk = request.POST.get("citation_pk")
    citation = request.POST.get("citation")
    thread = request.POST.get("thread")
    isReplyToPost = request.POST.get("isReplyToPost")
    mother_pk = request.POST.get("mother_pk")
    current_thread = request.POST.get("current_thread") # pane id
    context={'citation':citation,'citation_pk':citation_pk,'thread':thread,'thread_pk':thread_pk,'isReplyToPost':isReplyToPost,'mother_pk':mother_pk,'current_thread':current_thread}
    return render(request, 'papers/postForm.html', context)


# add posts
def addPost(request):

    # get POST data
    text = request.POST['text']
    thread_pk = int(request.POST.get("thread_pk", False))
    citation_pk = request.POST.get("citation_pk", False)
    is_reply_to_post = bool(int(request.POST.get("isReplyToPost", False)))
    mother_pk = int(request.POST.get("mother_pk", False))
    text = request.POST.get("text", False)
    current_thread = request.POST.get("current_thread", False)

    post = Post()
    setattr(post,'time_created',datetime.datetime.now())
    setattr(post,'creator',request.user)
    setattr(post,'thread',Thread.objects.get(pk=thread_pk))
    setattr(post,'isReplyToPost', True) # TODO: change this to base_node?
    if is_reply_to_post: # TODO: change name to is_submission?
        setattr(post,'mother',Post.objects.get(pk=mother_pk))
        setattr(post,'node_depth', Post.objects.get(pk=mother_pk).node_depth + 1)
    else:
        setattr(post,'mother', Post.objects.get(thread=thread_pk,isReplyToPost=False))
        setattr(post,'node_depth',1)
    setattr(post,'text',text)
    #setattr(post,'upvotes',0)
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
    thread_names = ["Explain Like I'm Five","Methodology","Results","Historical Context","Discussion"]
    for name in thread_names:
        thread = Thread()
        setattr(thread,'description',name)
        setattr(thread,'owner',citation)
        thread.save()
        post = Post()
        post = Post(time_created=datetime.datetime.now(),creator=request.user,thread=thread,
                    isReplyToPost=False,text="master_post",node_depth=0)
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
    #return render(request, 'papers/debug_ckeditor.html', context)

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
