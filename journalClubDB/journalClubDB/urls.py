"""journalClubDB URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^papers/', include('papers.urls', namespace="papers")),

    # for description of django.contrib.auth.urls, see: https://docs.djangoproject.com/en/1.8/topics/auth/default/#using-the-views for description of django.contrib.auth.urls
    url('^', include('django.contrib.auth.urls')),

    # See https://realpython.com/blog/python/adding-social-authentication-to-django/
    url('', include('social.apps.django_app.urls', namespace='social')),



]
