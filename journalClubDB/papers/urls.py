from django.conf.urls import url
from . import views

urlpatterns = [
    # ex: /papers/
    url(r'^$', views.index, name='index'),

    # ex: /papers/search/0/
    url(r'^search/(?P<page>[0-9]+)/$', views.search, name='search'),

    # ex: /papers/addCitation/
    url(r'^addCitation/$', views.addCitation, name='addCitation'),

    # ex: /papers/detail/0/
    url(r'^detail/(?P<pk>[0-9]+)/$', views.detail, name='detail'),

    # ex: /papers/search/0/
    url(r'^search_development/(?P<page>[0-9]+)/$', views.search_development, name='search_development'),

]
