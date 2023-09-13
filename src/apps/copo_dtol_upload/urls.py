from django.urls import path 
from . import views

app_name = 'copo_dtol_upload'

urlpatterns = [

    path('sample_spreadsheet/', views.sample_spreadsheet,
         name="sample_spreadsheet"),
    path('sample_images/', views.sample_images,
         name="sample_images"),
    path('sample_permits/', views.sample_permits,
         name="sample_permits"),
    path('create_spreadsheet_samples/', views.create_spreadsheet_samples,
         name="create_spreadsheet_samples"),
    path('update_spreadsheet_samples/', views.update_spreadsheet_samples,
         name="update_spreadsheet_samples"),
     
]
