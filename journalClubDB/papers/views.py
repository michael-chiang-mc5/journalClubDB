from django.shortcuts import render, redirect
from django.views import generic
from django.core.paginator import Paginator, InvalidPage, EmptyPage
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
    context = {'citations': citations,}
    return render(request, 'papers/index.html', context)

# returns a string, otherwise returns None
def citationSanitizer(request,field_name):
    if request.method == 'POST' and field_name in request.POST:
        f = request.POST[field_name]
        if f is not None and f != '' and f != 'None':
            return f
    return ''

# add posts
def addPost(request):

    # get POST data
    text = request.POST['text']
    thread_pk = int(request.POST.get("thread_pk", False))
    is_reply_to_post = bool(int(request.POST.get("isReplyToPost", False)))
    mother_pk = int(request.POST.get("mother_pk", False))
    text = request.POST.get("text", False)

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

    currentCitationPk = request.POST.get("citationPk", False)
    return HttpResponseRedirect(reverse('papers:detail', args=[currentCitationPk]))

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
    new_citation_url = reverse('papers:detail',args=[citation.pk])
    return JsonResponse({'new_citation_url':new_citation_url})


# returns post_list with field aggregate_score_tmp set for all posts in post_list.
# Input post_list should constitute a full tree with a single base node (no error checking)
def order_post_list(post_list):
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

    # post_list[idx_baseNode] is the base node of the post tree
    idx_baseNode = None
    for i,post in enumerate(post_list):
        if post.node_depth is 0:
            idx_baseNode = i
            break

    # recursively calculate aggregate scores and store in post_list[i].aggregate_score_tmp
    calculateAggregateScore(idx_baseNode, post_list, childrenIdx_list)

    # order post_list
    ordered_indices = orderPostlist(idx_baseNode, post_list, childrenIdx_list)
    ordered_post_list = [None] * len(post_list)
    for i,post in enumerate(ordered_indices):
        ordered_post_list[i] = post_list[ ordered_indices[i] ]

    return ordered_post_list,post_list


# Returns a list of indices corresponding to an ordered post_list
# ordered[i] = j means that the jth element of post_list belongs in slot i of ordered list
def orderPostlist(node_idx, post_list, childrenIdx_list):
    children_indices = childrenIdx_list[node_idx]
    num_children = len(children_indices)

    if num_children is 0:
        return [node_idx]
    else:
        # create tuple list [ (aggregateScore, index), ...] which is sorted by aggregateScore
        tup = [None] * len(children_indices)
        for i,child_idx in enumerate(children_indices):
            aggregate_score = post_list[child_idx].aggregate_score_tmp
            tup[i] = (aggregate_score,child_idx)
        tup = sorted(tup, reverse=True)

        ordered = [node_idx]
        for t in tup:
            aggregate_score = t[0]
            child_idx = t[1]
            o = orderPostlist(child_idx,post_list,childrenIdx_list)
            ordered = ordered + o
        return ordered

def calculateAggregateScore(node_idx, post_list, childrenIdx_list):
    children_indices = childrenIdx_list[node_idx]
    num_children = len(children_indices)
    raw_score = post_list[node_idx].score()

    if num_children is 0:
        score = raw_score
        post_list[node_idx].aggregate_score_tmp = score
        return score
    else:
        score = raw_score
        for child_idx in children_indices:
            aggregate_score_child = calculateAggregateScore(child_idx,post_list,childrenIdx_list)
            score = max(score,aggregate_score_child)
        post_list[node_idx].aggregate_score_tmp = score
        return score

# internal citation information
def detail(request,pk):
    citation = Citation.objects.get(pk=pk)
    threads = Thread.objects.filter(owner=pk)
    posts_vector = []
    for thread in threads:
        posts = Post.objects.filter(thread=thread.pk)
        ordered_posts,dummy = order_post_list(posts) # ordered_posts is not a queryset
        posts_vector.append(ordered_posts[1:]) # exclude first entry which is master post
    threadsPostsvector = zip(threads,posts_vector)

    context = {'citation': citation,'threads': threads,'posts_vector':posts_vector,'threadsPostsvector':threadsPostsvector}
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
    context = {'entries': pubmed.entries, 'search_str': search_str, 'totalPages':totalPages, 'totalPagesRange': range(1,totalPages), 'pageNumber': pageNumber, 'freshSearch': freshSearch}
    return render(request, 'papers/search.html', context)

# upvoting and downvoting comments
def updownvote(request):
    updown = request.POST.get("updown")
    post_pk = int(request.POST.get("post_pk"))

    post = Post.objects.get(pk=post_pk)
    if updown == "up":
        post.upvoters.add(request.user)
        post.downvoters.remove(request.user)
        post.save()
    else:
        post.downvoters.add(request.user)
        post.upvoters.remove(request.user)
        post.save()


    return HttpResponse("asdfads")
    #return JsonResponse({'post_pk':post_pk})



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
            pubmed.getRecords(search_str,retMin,retMax)
        else: # page change
            search_str = request.POST.get("search_str")
            pageNumber = int(request.POST.get("pageNumber"))
            retMin = (pageNumber-1)*10
            retMax = 10
            pubmed.getRecords(search_str,retMin,retMax)
            totalPages = int(request.POST.get("totalPages"))
        freshSearch=False
    else:
        freshSearch=True

    totalPages = min([totalPages,15+1]) # maximum of 15 pages
    context = {'entries': pubmed.entries, 'search_str': search_str, 'totalPages':totalPages, 'totalPagesRange': range(1,totalPages), 'pageNumber': pageNumber, 'freshSearch': freshSearch}
    return render(request, 'papers/search.html', context)
