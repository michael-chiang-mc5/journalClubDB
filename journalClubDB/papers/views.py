from django.shortcuts import render
from django.views import generic
from .models import Citation

class IndexView(generic.ListView):
    template_name = 'papers/index.html'
    context_object_name = 'citation_list'
    def get_queryset(self):
        """Return list of all citations"""
        return Citation.objects.all()
