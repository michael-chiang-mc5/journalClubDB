from django.shortcuts import render
from django.views import generic
from .models import Citation
from django.http import HttpResponse
from .scholar2 import testFunction

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
def search(request):
    search_str = request.POST.get("search_str")



    return HttpResponse(testFunction())
