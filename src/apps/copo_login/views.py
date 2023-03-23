from django.shortcuts import render
from django.contrib.auth import logout
from allauth.account.forms import LoginForm

# Create your views here.
def copo_logout(request):
    logout(request)
    return render(request, 'copo/auth/logout.html', {})

def login(request):
    context = {
        'login_form': LoginForm(),
    }
    return render(request, 'copo/auth/login.html', context)