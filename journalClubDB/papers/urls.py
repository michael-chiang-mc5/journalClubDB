from django.conf.urls import url
from . import views
from django.views.generic import TemplateView

urlpatterns = [
    # ex: /papers/
    url(r'^$', views.frontpage, name='frontpage'),

    # ex: /paperOfTheWeek_list/
    url(r'^paperOfTheWeek_list/$', views.paperOfTheWeek_list, name='paperOfTheWeek_list'),

    # ex: /papers/index/
    url(r'^index/$', views.index, name='index'),

    # ex: /papers/self_user_profile/
    url(r'^self_user_profile/$', views.self_user_profile, name='self_user_profile'),

    # ex: /papers/self_user_profile/
    url(r'^add_citation_to_user_library/$', views.add_citation_to_user_library, name='add_citation_to_user_library'),


    url(r'^user_notifications/$', views.user_notifications, name='user_notifications'),

    url(r'^user_library/$', views.user_library, name='user_library'),

    # ex:
    url(r'^post_context/(?P<post_pk>[0-9]+)/$', views.post_context, name='post_context'),

    # ex:
    url(r'^user_posts/(?P<user_pk>[0-9]+)/$', views.user_posts, name='user_posts'),

    # ex: /papers/search/0/
    url(r'^search/(?P<page>[0-9]+)/$', views.search, name='search'),

    # ex: /papers/addCitation/
    url(r'^addCitation/$', views.addCitation, name='addCitation'),

    # ex:
    url(r'^addPost/$', views.addPost, name='addPost'),
    url(r'^editPersonalNote/$', views.editPersonalNote, name='editPersonalNote'),
    url(r'^postForm/$', views.postForm, name='postForm'),
    url(r'^personalNoteForm/$', views.personalNoteForm, name='personalNoteForm'),


    # ex:
    url(r'^upvote/$', views.upvote, name='upvote'),

    # ex:
    url(r'^downvote/$', views.downvote, name='downvote'),


    # ex: /papers/detail/0/0/
    url(r'^detail/(?P<pk>[0-9]+)/(?P<current_thread>[0-9]+)/$', views.detail, name='detail'),

    # ex: /papers/search/0/
    url(r'^search_development/(?P<page>[0-9]+)/$', views.search_development, name='search_development'),

    url(r'^register/$', views.register, name='register'), # ADD NEW PATTERN!
    url(r'^user_login/$', views.user_login, name='user_login'),
    url(r'^is_field_available/$', views.is_field_available, name='is_field_available'),
    url(r'^user_logout/$', views.user_logout, name='user_logout'),
    url(r'^add_tag/$', views.add_tag, name='add_tag'),

    url(r'^paperOfTheWeek_admin/$', views.paperOfTheWeek_admin, name='paperOfTheWeek_admin'),


]
