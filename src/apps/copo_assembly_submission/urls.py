from django.urls import path
from . import views

app_name = 'copo_assembly_submission'

urlpatterns = [

    path('<profile_id>', views.ena_assembly,
         name="ena_assembly")
     
]
