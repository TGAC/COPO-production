from django.shortcuts import render

from src.apps.copo_core.models import banner_view


def index(request):
    banner = banner_view.objects.all()
    if len(banner) > 0:
        context = {'user': request.user, "banner": banner[0]}
    else:
        context = {'user': request.user}
    return render(request, 'index_new.html', context)
