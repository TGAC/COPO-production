from django.contrib.auth.decorators import login_required
from common.dal.copo_da import Profile, DataFile, Source
from common.s3.s3Connection import S3Connection
from django.shortcuts import render
import jsonpickle
from django.http import HttpResponse
from .utils.CopoFiles import generate_files_record
from common.utils import helpers
import json
from django.conf import settings
from os.path import join, isfile
from pathlib import Path
from django.core.files.storage import default_storage
import os
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
from common.utils.logger import Logger
from django_tools.middlewares import ThreadLocal

l = Logger()




@login_required()
def validate_bioimage_filenames(request, profile_id):
    filenames = request.POST.get("filenames", list())
    profile = Profile().get_record(profile_id)
    dtol_only = True

    if profile["type"] == "Stand-alone":
        return HttpResponse(status=200, content="No checking for stand-alone profile images", content_type='application/json')

    profile_oids = Profile().get_all_profiles(user=None, id_only=True, dtol_only=True)
    profile_ids = [str(profile_oid["_id"]) for profile_oid in profile_oids]
    sourceMap = Source().get_sourcemap_by_specimens(profile_ids=profile_ids)
    is_error = False
    for filename in filenames:
        if "-" not in filename:
            is_error = True
            break
        specimen_id = filename[: ( filename.rfind("-") )]
        if specimen_id not in sourceMap:
            is_error = True
            break

    if is_error:
        return HttpResponse(status=400, content="Noe or more specimen dose not exist in user samples", content_type='application/json')
    else:
        return HttpResponse(status=200, content="All specimen exist in user samples", content_type='application/json')
    

@login_required()
def upload_bioimages(request, profile_id):
    files = request.FILES

    image_path = Path(settings.MEDIA_ROOT) / "sample_images" / helpers.get_user_id()
    display_path = Path(settings.MEDIA_URL) / "sample_images" / helpers.get_user_id()
    thumbnail_folder = image_path / "thumbnail"
    # compare list of sample names with specimen ids already uploaded
    # get list of specimen_ids in sample
    # specimen_id_column_index = 0
    output = list()
    thumbnail_folder.mkdir(parents=True, exist_ok=True)

    #image_path = sample_images
    #display_path = display_images
    # image_path = Path(settings.MEDIA_ROOT) / "sample_images" / self.profile_id
    #existing_images = DataFile().get_datafile_names_by_name_regx(specimentIds)

    for f in files:
        file = files[f]
        # file_path = image_path / file.name
        # write full sized image to large storage
        file_path = image_path / file.name
        thumbnail_path = thumbnail_folder / file.name
        thumbnail_display_path = display_path / "thumbnail" / file.name
        file_display_path = display_path / file.name

        filename = os.path.splitext(file.name)[0].upper()
        # now iterate through samples data to see if there is a match between specimen_id and image name
        found = False
        size = 128, 128
 
        output.append({"file_display_location": str(file_display_path), "thumbnail": str(thumbnail_display_path), "name": file.name})

        # logging.info("writing " + str(file_path))
        with default_storage.open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        im = Image.open(file_path)
        im.thumbnail(size)
        im.save(thumbnail_path)
        # create matching DataFile object for image is provided
        df = DataFile().get_records_by_fields({"name": file.name, "type": "bioimage", "created_by": helpers.get_user_id()})
        if (len(df) == 0):
            fields = {
                "file_display_location": str(file_display_path), "file_location": str(file_path), "name": file.name, "thumbnail" :  str(thumbnail_display_path), "type": "bioimage" }
            DataFile().save_record({}, **fields)

    helpers.notify_frontend(data={"profile_id": profile_id}, msg=output, action="make_images_table",
                    html_id="images")
    out = jsonpickle.encode(output, unpicklable=False)
    return HttpResponse(status=200, content=out, content_type='application/json')

@login_required
def copo_bioimage(request, profile_id):
    bioimages = DataFile().get_records_by_fields({"type": "bioimage", "created_by": helpers.get_user_id()})
    specimen_ids = [  bioimage["name"] [: ( bioimage["name"].rfind("-") )  ]  for bioimage in bioimages if  "-" in bioimage["name"]]
    profile_oids = Profile().get_all_profiles(user=None, id_only=True, dtol_only=True)
    profile_ids = [str(profile_oid["_id"]) for profile_oid in profile_oids]
    sourceMap = Source().get_sourcemap_by_specimens(specimen_ids=specimen_ids, profile_ids=profile_ids)

    for bioimage in bioimages :
        if "-" in bioimage["name"]:
            specimen_id = bioimage["name"][: ( bioimage["name"].rfind("-") )]
            bioimage["bioSampleAccession"] = sourceMap.get(specimen_id, dict()).get("bioSampleAccession","")

    out = jsonpickle.encode(bioimages, unpicklable=False)
    return HttpResponse(status=200, content=out, content_type='application/json')


@login_required
def submit_bioimage(request, target_ids):
    return HttpResponse(status=503, content="Not implemented", content_type='application/json')