from django.urls import path
from . import views

app_name = 'copo_read_submission'

urlpatterns = [
    path('ena_read_manifest_validate/<profile_id>', views.ena_read_manifest_validate,
         name="ena_read_manifest_validate"),
    path('process_urls', views.process_urls,
         name="process_urls"),
    path('parse_ena_spreadsheet/', views.parse_ena_spreadsheet,
         name="parse_ena_spreadsheet"),
    path('save_ena_records/', views.save_ena_records,
         name="save_ena_records"),
    path('get_manifest_submission_list/', views.get_manifest_submission_list,
         name="get_manifest_submission_list"),
    path('init_manifest_submission/', views.init_manifest_submission,
         name="init_manifest_submission"),
    path('get_submission_status/', views.get_submission_status, 
         name="get_submission_status")
]
