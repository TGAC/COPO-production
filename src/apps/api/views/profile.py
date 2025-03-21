from common.dal.mongo_util import cursor_to_list
from common.dal.profile_da import Profile
from common.dal.sample_da import Sample
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from .sample import format_date
import bson.json_util as jsonb
import dateutil.parser as parser

class APICreateProfile(APIView):
    def post(self, request):
        uid = request.user.id
        # first check if there is a profile with this title already
        existing_profiles = Profile().get_collection_handle().find({'user_id': uid, 'title': request.POST['title']})
        if len(list(existing_profiles)) > 0:
            return Response(status=409, data={'status': 'A Profile with that name already exists:' + request.POST['title']})
        p_dict = {'title': request.POST['title'], 'description': request.POST['description'], 'type': request.POST['profile_type'],
                  'user_id': uid}
        p = Profile().save_record({}, **p_dict)
        out = {'_id': str(p['_id']), 'title': p['title'], 'description': p['description'], 'type': p['type']}
        return Response(out)

class APIGetProfilesForUser(APIView):
    def post(self, request):
        uid = request.user.id
        existing_profiles = Profile().get_collection_handle().find({'user_id': uid})
        out = list()
        for el in existing_profiles:
            out.append({'title': el['title'], 'type': el['type'], '_id': str(el['_id'])})
        return Response(out)

def associate_profiles_with_tubes_or_well_ids(request):
    from src.apps.api.utils import generate_csv_response, generate_wrapper_response

    filter_dict = {}
    projection = {'_id': 1, 'title': 1, 'type':1, 'associated_type':1,'first_manifest_date_created': 1, 'last_manifest_date_modified': 1}

    return_type = request.GET.get('return_type', 'json').lower()
    profile_type = request.GET.get('profile_type','').lower()
    associated_profile_type = request.GET.get('associated_profile_type','')

    # Dates must be ISO 8601 formatted
    try:                
        d_from = parser.parse(request.GET.get('d_from', None))
    except TypeError: 
        d_from = None

    try:                
        d_to = parser.parse(request.GET.get('d_to', None))
    except TypeError: 
        d_to = None

    # Get all profiles of the given type
    if profile_type:
        filter_dict['type'] = profile_type

    # Get all profiles of the given associated type
    if associated_profile_type:
        filter_dict['associated_type'] = {'$in': [associated_profile_type]}

    # Validate the dates
    if d_from and d_to is None:
        return HttpResponse(status=400, content=f'\'to date\' is required when \'from date\' is entered')

    if d_from is None and d_to:
        return HttpResponse(status=400, content=f'\'from date\' is required when \'to date\' is entered')

    if d_from and d_to and d_from > d_to:
        return HttpResponse(status=400, content=f'\'from date\' must be earlier than \'to date\'')
    
    # Get all profiles created between the given dates
    if d_from and d_to:
        filter_dict['first_manifest_date_created'] = {'$gte': d_from}
        filter_dict['last_manifest_date_modified'] = {'$lt': d_to}

    profiles = cursor_to_list(Profile().get_collection_handle().find(filter_dict, projection))
    profile_count = len(profiles)

    # Create a dictionary to store the final structure
    profile_well_associations = []

    for profile in profiles:
        # Fetch samples associated with the profile
        samples = Sample().get_by_field('profile_id', [str(profile['_id'])])

        # Gather the TUBE_OR_WELL_IDs from the associated samples
        tube_or_well_ids = [sample['TUBE_OR_WELL_ID'] for sample in samples if 'TUBE_OR_WELL_ID' in sample]

        # Add the profile and its associated well IDs to the result structure
        profile_well_associations.append({
            'TUBE_OR_WELL_IDs': tube_or_well_ids,
            'associated_profile_type': profile['associated_type'],
            'first_manifest_date_created': format_date(profile['first_manifest_date_created']),
            'last_manifest_date_modified': format_date(profile['last_manifest_date_modified']),
            'profile_title': profile['title'],
            'profile_type': profile['type']
        })

    if return_type not in ['json', 'csv']:
        # Show error if return type is not 'json' or 'csv'
        error = "Invalid return type provided. Please provide either 'json' or 'csv'."
        return HttpResponse(status=400, content=error)

    if  return_type == 'csv':
        template = []
        for profile in profile_well_associations:
            well_ids = ' '.join(profile['TUBE_OR_WELL_IDs'])
            template.append({'copo_profile_title': profile['copo_profile_title'], 'TUBE_OR_WELL_IDs': well_ids})
        return generate_csv_response(standard='tol', template=template)
    else:
        output = generate_wrapper_response(num_found = profile_count, template=profile_well_associations)
        output = jsonb.dumps([output])

        return  HttpResponse(output, content_type='application/json')
