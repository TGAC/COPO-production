from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from common.dal.profile_da import Profile
from common.dal.submission_da import Submission
from .utils.da import Image
from common.utils.helpers import notify_image_status
from django.http import HttpResponse, JsonResponse
from .forms import ImageForm
from common.s3.s3Connection import S3Connection
from src.apps.copo_core.views import web_page_access_checker


@web_page_access_checker
@login_required
def copo_images(request, profile_id):
    request.session["profile_id"] = profile_id
    profile = Profile().get_record(profile_id)
    return render(request, 'copo/copo_image.html', {'profile_id': profile_id, 'profile': profile})
