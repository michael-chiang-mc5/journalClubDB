Templates from:
https://github.com/macdhuibh/django-registration-templates/tree/master/registration

urls (from http://riceball.com/d/content/django-18-tutorial-5-django-registration-redux):
^accounts/ ^activate/complete/$ [name='registration_activation_complete']
^accounts/ ^activate/(?P<activation_key>\w+)/$ [name='registration_activate']
^accounts/ ^register/complete/$ [name='registration_complete']
^accounts/ ^register/closed/$ [name='registration_disallowed']
^accounts/ ^register/$ [name='registration_register']
^accounts/ ^login/$ [name='auth_login']
^accounts/ ^logout/$ [name='auth_logout']
^accounts/ ^password/change/$ [name='auth_password_change']
^accounts/ ^password/change/done/$ [name='auth_password_change_done']
^accounts/ ^password/reset/$ [name='auth_password_reset']
^accounts/ ^password/reset/complete/$ [name='auth_password_reset_complete']
^accounts/ ^password/reset/done/$ [name='auth_password_reset_done']
^accounts/ ^password/reset/confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/$ [name='auth_password_reset_confirm']

To make registration not require email, see:
http://stackoverflow.com/questions/6364623/django-registration-email-as-username
