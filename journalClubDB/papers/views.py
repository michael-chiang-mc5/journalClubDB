from django.shortcuts import render, redirect
from django.views import generic
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
import math
from .models import Citation
from .Pubmed import PubmedInterface

# see all citations in database
class IndexView(generic.ListView):
    template_name = 'papers/index.html'
    context_object_name = 'citation_list'
    def get_queryset(self):
        """Return list of all citations"""
        return Citation.objects.all()

# probably better to use ajax
def addCitation(request):
    citation = Citation()
    citation.title = request.POST.get("title")
    citation.author = request.POST.get("author")
    citation.journal = request.POST.get("journal")
    citation.volume = request.POST.get("volume")
    citation.number = request.POST.get("number")
    citation.pages = request.POST.get("pages")
    citation.year = request.POST.get("year")
    citation.publisher = request.POST.get("publisher")
    citation.save()
    return redirect('papers:index')

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
    context = {'entries': pubmed.entries, 'search_str': search_str, 'totalPages':totalPages, 'totalPagesRange': range(1,totalPages), 'pageNumber': pageNumber, 'freshSearch': False}
    return render(request, 'papers/search.html', context)
