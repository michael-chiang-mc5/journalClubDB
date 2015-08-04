from django.shortcuts import render, redirect
from django.views import generic
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
import logging
import math
from .models import Citation
from .Pubmed import PubmedInterface
logger = logging.getLogger(__name__)
import time
from django.views.decorators.csrf import csrf_exempt

# see all citations in database
class IndexView(generic.ListView):
    template_name = 'papers/index.html'
    context_object_name = 'citation_list'
    def get_queryset(self):
        """Return list of all citations"""
        return Citation.objects.all()


# returns a string, otherwise returns None
def citationSanitizer(request,field_name):
    if request.method == 'POST' and field_name in request.POST:
        f = request.POST[field_name]
        if f is not None and f != '' and f != 'None':
            return f
    return ''


# probably better to use ajax
def addCitation(request):
    citation = Citation()
    field_list = ["title", "author", "journal", "volume","number","pages","date","fullSource","keywords","abstract","doi","fullAuthorNames","pubmedID"]
    for f in field_list:
        field_entry = citationSanitizer(request,f)
        setattr(citation,f,field_entry)
    citation.save()
    return HttpResponse("donezo")

# search interface
def search(request,page):
    logger.debug("in search")
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
