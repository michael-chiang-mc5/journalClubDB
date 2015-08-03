from django.shortcuts import render
from django.views import generic
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.http import HttpResponse
from .models import Citation
from .Pubmed import PubmedInterface

# see all citations in database
class IndexView(generic.ListView):
    template_name = 'papers/index.html'
    context_object_name = 'citation_list'
    def get_queryset(self):
        """Return list of all citations"""
        return Citation.objects.all()

# search interface
def searchInterface(request):
    return render(request, 'papers/search.html')

# get search string from /searchInterface/.  Search using google scholar
def search(request,page):

    search_str = request.POST.get("search_str")


    pubmed = PubmedInterface()
    pubmed.getRecords(search_str,20)
    paginator = Paginator(pubmed.entries, 5) # get pages with 5 items each

    try:
        posts = paginator.page(page)
    except (InvalidPage, EmptyPage):
        posts = paginator.page(paginator.num_pages)

    context = {'posts': posts}
    return render(request, 'papers/searchResults.html', context)
