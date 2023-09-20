from django.urls import path, re_path
from . import views

app_name = 'copo_profile'

urlpatterns = [
    path('', views.copo_profile_index, name='index'),
    path('update_counts/', views.get_profile_counts, name='update_counts'),
    re_path(r'^(?P<profile_id>[a-z0-9]+)/view', views.view_copo_profile,
            name='view_copo_profile'),
    #path('forms/', views.copo_profile_forms, name="copo_profile_forms"),
    # path('delete_profile/', views.delete_profile, name="delete_profile"),
    path('delete', views.delete_profile, name="delete_profile"),
    #path('visualise/', views.copo_profile_visualise, name="copo_profile_visualise")
    re_path(r'^(?P<profile_id>[a-z0-9]+)/release_study', views.release_study,
        name='release_study'),
    path('get_sequencing_centers/', views.get_sequencing_centers, name='get_sequencing_centers'),
]