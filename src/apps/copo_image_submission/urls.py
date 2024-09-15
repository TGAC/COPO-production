from django.urls import path, re_path
from . import views

app_name = 'copo_image_submission'

urlpatterns = [
    re_path(r'^(?P<profile_id>[a-z0-9]+)/view', views.copo_images,
         name='copo_images')
]
