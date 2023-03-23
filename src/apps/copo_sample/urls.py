from django.urls import path, re_path
from . import views

app_name = 'copo_sample'

urlpatterns = [
    re_path(r'^(?P<profile_id>[a-z0-9]+)/view', views.copo_samples,
            name='copo_samples')
]            