from django.contrib.auth.decorators import login_required


@login_required()
def copo_images(request, profile_id):
    request.session["profile_id"] = profile_id
    return ''
