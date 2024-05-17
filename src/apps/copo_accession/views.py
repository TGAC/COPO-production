from bson import json_util
from common.dal.profile_da import Profile
from common.dal.sample_da import Sample
from common.dal.submission_da import Submission
from common.schema_versions.lookup.dtol_lookups import NON_SAMPLE_ACCESSION_TYPES, TOL_PROFILE_TYPES
from common.utils.helpers import get_group_membership_asString
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from src.apps.copo_core.models import ViewLock
from src.apps.copo_core.views import web_page_access_checker
import common.schemas.utils.data_utils as d_utils
import json


@web_page_access_checker
@login_required
def copo_accessions(request, profile_id):
    request.session['profile_id'] = profile_id
    profile = Profile().get_record(profile_id)
    groups = get_group_membership_asString()

    return render(request, 'copo/accessions/copo_accessions.html',
                  {'profile_id': profile_id, 'profile': profile, 'groups': groups, 'showAllCOPOAccessions': False})

def copo_accessions_dashboard(request):
    # Determine if users are in the appropriate membership group to view the web page
    groups = get_group_membership_asString()

    return render(request, 'copo/accessions/copo_accessions.html',
                  {'profile_id': '999', 'groups': groups, 'showAllCOPOAccessions': True})

def get_accession_records_column_names(request):
    isOtherAccessionsTabActive = d_utils.convertStringToBoolean(request.GET.get('isOtherAccessionsTabActive', str()))
    
    columns = list()
    columns.append(dict(data='record_id', visible=False))
    columns.append(dict(data='DT_RowId', visible=False))
    columns.append(dict(data='accession_type', title='Accession Type', visible=True))

    if isOtherAccessionsTabActive:
        # Add profile_id column
        columns.append(dict(data='profile_id', visible=False))

        # Set column names
        labels = ['accession', 'alias', 'profile_title']
        
        for x in labels:
            class_name = 'ena-accession' if x.lower().endswith("accession") else ''
            columns.append(dict(data=x, title=d_utils.convertStringToTitleCase(x), visible=True,  className=class_name))
    else:
        # Set column names
        labels = ['biosampleAccession', 'sraAccession', 'submissionAccession', 'manifest_id', 'SCIENTIFIC_NAME', 'SPECIMEN_ID', 'TAXON_ID']
        
        for x in labels:
            class_name = 'ena-accession' if x.lower().endswith("accession") else 'copo-api' if x.lower() == 'manifest_id' else ''
            columns.append(dict(data=x, title=d_utils.convertStringToTitleCase(x),className=class_name))

    return HttpResponse(json_util.dumps(columns))

def generate_accession_records(request):
    isUserProfileActive = d_utils.convertStringToBoolean(request.POST.get('isUserProfileActive',str()))
    isOtherAccessionsTabActive = d_utils.convertStringToBoolean(request.POST.get('isOtherAccessionsTabActive', str()))
    showAllCOPOAccessions = d_utils.convertStringToBoolean(request.POST.get('showAllCOPOAccessions', str()))
    filter_accessions = json.loads(request.POST.get('filter_accessions', list()))

    # Convert items in list to lowercase
    filter_accessions = [x.lower() for x in filter_accessions] if filter_accessions else list()

    profile_id = request.session.get('profile_id', str()) if isUserProfileActive else str()
    start = request.POST.get('start', '0')
    length = request.POST.get('length', '10')
    draw = request.POST.get('draw', '1')
    sort_by = request.POST.get('order[0][column]', '')
    direction = request.POST.get('order[0][dir]', '')
    search = request.POST.get('search', '')
    dir = -1

    if direction == 'asc':
        dir = 1

    # Create a dictionary to store the elements
    element_dict = dict()
    element_dict['draw'] = draw
    element_dict['start'] = start
    element_dict['length'] = length
    element_dict['sort_by'] = sort_by
    element_dict['dir'] = dir
    element_dict['search'] = search
    element_dict['showAllCOPOAccessions'] = showAllCOPOAccessions
    element_dict['isUserProfileActive'] = isUserProfileActive
    element_dict['profile_id'] = profile_id
    element_dict['filter_accessions'] = filter_accessions

    records = None

    if isOtherAccessionsTabActive:
        records = Submission().get_non_sample_accessions(element_dict)          
    else:
        records = Sample().get_sample_accessions(element_dict)

    return HttpResponse(json_util.dumps(records))

def get_accession_types(isOtherAccessionsTabActive):
    tol_project_types = [x.upper() for x in TOL_PROFILE_TYPES]

    accession_types = NON_SAMPLE_ACCESSION_TYPES if isOtherAccessionsTabActive else tol_project_types

    return accession_types


def get_filter_accession_titles(request):
    # Get the text and value for the filter accession checkboxes
    accession_titles = list()
    isOtherAccessionsTabActive = d_utils.convertStringToBoolean(
        request.POST.get('isOtherAccessionsTabActive', str()))

    accession_types = get_accession_types(isOtherAccessionsTabActive)

    if isOtherAccessionsTabActive:
        # Reorder the list of accessions types accorsing to the order of 
        # the accession types in NON_SAMPLE_ACCESSION_TYPES list
        accession_titles = [{'title': d_utils.convertStringToTitleCase(
            item), 'value': item} for item in NON_SAMPLE_ACCESSION_TYPES if item in accession_types]
    else:
        # Other project types
        profile_types = list()

        for i in accession_types:
            profile_type = Profile().get_collection_handle().find_one({'type': {'$regex': i.upper(), '$options': 'i'}},
                                                                      {'_id': 0, 'type': 1})
            if profile_type:
                profile_types.append(
                    {'title':  profile_type.get('type', ''), 'value': i.upper()})

        accession_titles = profile_types

    return HttpResponse(json_util.dumps(accession_titles))
