from django.conf.urls import url
from . import views

urlpatterns = [
    # ex: /papers/
    url(r'^$', views.IndexView.as_view(), name='index'),

    # ex: /papers/searchInterface/
    url(r'^searchInterface/$', views.searchInterface, name='searchInterface'),

    # ex: /papers/searchInterface/
    url(r'^searchInterface/$', views.searchInterface, name='searchInterface'),

    # ex: /papers/search/
    url(r'^search/(?P<page>[0-9]+)/$', views.search, name='search'),


    # ex: /polls/5
    #url(r'^(?P<pk>[0-9]+)/$', views.DetailView.as_view(), name='detail'),
]
