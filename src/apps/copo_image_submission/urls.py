from django.urls import include, path, re_path

from . import views

app_name = 'copo_image_submission'

urlpatterns = [
    # path(
    #     'parse_image_spreadsheet/',
    #     views.parse_image_spreadsheet,
    #     name="parse_image_spreadsheet",
    # # ),
    # path(
    #     'save_image_records/',
    #     views.save_image_records,
    #     name="save_image_records",
    # ),
    re_path(r'^(?P<profile_id>[a-z0-9]+)/view', views.copo_images, name='copo_images'),
    # re_path(
    #     "download_manifest/(?P<profile_id>[a-z0-9]+)/(?P<study_id>[A-Za-z0-9]+)",
    #     views.download_manifest,
    # ),
]
