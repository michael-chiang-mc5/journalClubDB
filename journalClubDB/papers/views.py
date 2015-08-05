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

def addCitation(request):

    # check for duplicate citations.  If citation already exists, return primary key
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

    # Create threads
    thread = Thread()
    setattr(thread,'description','General comments')
    setattr(thread,'owner',citation)
    thread.save()

    # Return url to new citation detail page
    new_citation_url = reverse('papers:detail',args=[citation.pk])
    return JsonResponse({'new_citation_url':new_citation_url})

# internal citation information
def detail(request,pk):
    citation = Citation.objects.get(pk=pk)
    thread1 = Thread.objects.filter(owner=pk)[0]
    posts1 = Post.objects.filter(owner=thread1.pk) # TODO: sort by time_created

    context = {'citation': citation,'thread1': thread1,'posts1':posts1}
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
