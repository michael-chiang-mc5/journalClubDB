from django.conf.urls import url
from . import views

urlpatterns = [
    # ex: /papers/
    url(r'^$', views.index, name='index'),

    # ex: /papers/search/0/
    url(r'^search/(?P<page>[0-9]+)/$', views.search, name='search'),

    # ex: /papers/addCitation/
    url(r'^addCitation/$', views.addCitation, name='addCitation'),

    # ex:
    url(r'^addPost/$', views.addPost, name='addPost'),

    url(r'^postForm/$', views.postForm, name='postForm'),


    # ex:
    url(r'^updownvote/$', views.updownvote, name='updownvote'),

    # ex:
    url(r'^upvote/$', views.upvote, name='upvote'),

    # ex:
    url(r'^downvote/$', views.downvote, name='downvote'),


    # ex: /papers/detail/0/0/
    url(r'^detail/(?P<pk>[0-9]+)/(?P<current_thread>[0-9]+)/$', views.detail, name='detail'),

    # ex: /papers/search/0/
    url(r'^search_development/(?P<page>[0-9]+)/$', views.search_development, name='search_development'),


]
