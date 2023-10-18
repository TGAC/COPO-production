from django.urls import path, re_path
from . import views

app_name = 'copo_bioimage'

urlpatterns = [
    re_path(r'(?P<profile_id>[a-z0-9]+)/view', views.copo_bioimage, name='copo_bioimage'),
    re_path(r'(?P<profile_id>[a-z0-9]+)/upload', views.upload_bioimages, name='upload_bioimages'),      
    re_path(r'(?P<profile_id>[a-z0-9]+)/validate', views.validate_bioimage_filenames, name='validate_bioimage_filenames'),
]
