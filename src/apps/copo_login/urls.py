from django.urls import path
from . import views

app_name = 'copo_login'

urlpatterns = [
    path('login/', views.login, name='login'),
    path('logout/', views.copo_logout, name='logout'),
]
