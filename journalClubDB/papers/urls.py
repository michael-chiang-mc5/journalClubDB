from django.conf.urls import url
from . import views

urlpatterns = [
    # ex: /papers/
    url(r'^$', views.IndexView.as_view(), name='index'),

    # ex: /papers/search/0/
    url(r'^search/(?P<page>[0-9]+)/$', views.search, name='search'),

    # ex: /papers/addCitation/
    url(r'^addCitation/$', views.addCitation, name='addCitation'),

]
