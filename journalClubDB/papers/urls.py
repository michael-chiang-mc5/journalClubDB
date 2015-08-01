from django.conf.urls import url
from . import views

urlpatterns = [
    # ex: /polls/
    url(r'^$', views.IndexView.as_view(), name='index'),
    # ex: /polls/5
    #url(r'^(?P<pk>[0-9]+)/$', views.DetailView.as_view(), name='detail'),
]
