from django.conf.urls import url
from . import views

urlpatterns = [
    # ex: /papers/
    url(r'^$', views.IndexView.as_view(), name='index'),

    # ex: /papers/search/
    url(r'^search/(?P<page>[0-9]+)/$', views.search, name='search'),
]
