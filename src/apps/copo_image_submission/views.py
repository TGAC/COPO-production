from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from common.dal.profile_da import Profile

from src.apps.copo_core.models import ProfileType
from src.apps.copo_core.views import web_page_access_checker


@web_page_access_checker
@login_required
def copo_images(request, profile_id):
    request.session['profile_id'] = profile_id
    profile = Profile().get_record(profile_id)
    schema_name = profile.get('schema_name', 'COPO_IMAGE')
    # image_checklists = ImageSchema().get_checklists(schema_name=schema_name, checklist_id='')
    profile_checklist_ids = []
    # Image().get_collection_handle().distinct('checklist_id', {'profile_id': profile_id, 'schema_name' : schema_name})

    checklists = []
    # if image_checklists:
    #     for key, item in image_checklists.items():
    #         checklist = {'primary_id': key, 'name': item.get('name', ''), 'description': item.get('description', '')}
    #         checklists.append(checklist)

    return render(
        request,
        'copo/copo_images.html',
        {
            'profile_id': profile_id,
            'profile': profile,
            'schema_name': schema_name,
            'checklists': checklists,
            'profile_checklist_ids': profile_checklist_ids,
        },
    )
