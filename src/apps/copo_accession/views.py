from bson import json_util
# from dal.broker_da import BrokerVisuals
from common.dal.profile_da import Profile
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from src.apps.copo_core.views import web_page_access_checker
from common.schema_versions.lookup.dtol_lookups import STANDALONE_ACCESSION_TYPES
from common.utils.helpers import get_group_membership_asString
import common.schemas.utils.data_utils as d_utils
import json


@web_page_access_checker
@login_required
def copo_accessions(request, profile_id):
    request.session["profile_id"] = profile_id
    profile = Profile().get_record(profile_id)
    groups = get_group_membership_asString()

    return render(request, 'copo/accessions/copo_accessions.html',
                  {'profile_id': profile_id, 'profile': profile, 'groups': groups, 'showAllCOPOAccessions': False})


def copo_accessions_dashboard(request):
    # Determine if users are in the appropriate membership group to view the web page
    groups = get_group_membership_asString()

    return render(request, 'copo/accessions/copo_accessions.html',
                  {'profile_id': '999', 'groups': groups, 'showAllCOPOAccessions': True})


"""
def copo_visualize_accessions_dashboard(request):
    context = dict()

    task = request.POST.get("task", str())

    # profile_id = request.session.get("profile_id", str())

    context["quick_tour_flag"] = request.session.get("quick_tour_flag", False)
    request.session["quick_tour_flag"] = context["quick_tour_flag"]  

    broker_visuals = BrokerVisuals(context=context,
                                #    profile_id=profile_id,
                                   request_dict=request.POST.dict(),
                                   component=request.POST.get("component", str()),
                                   quick_tour_flag=request.POST.get("quick_tour_flag", False))

    task_dict = dict(table_data=broker_visuals.do_table_data)

    if task in task_dict:
        context = task_dict[task]()

    out = encode(context, unpicklable=False)
    return HttpResponse(out, content_type='application/json')
"""


def get_filter_accession_titles(request):
    # Get the text and value for the filter accession checkboxes
    accession_titles = list()
    isSampleProfileTypeStandalone = d_utils.convertStringToBoolean(
        request.POST.get("isSampleProfileTypeStandalone", str()))
    # Parses string array to actual list
    accession_types = json.loads(request.POST.get("accession_types", []))

    if isSampleProfileTypeStandalone:
        # Stand-alone projects
        # Reorder the list of accessions types accorsing to the order of the accession types in STANDALONE_ACCESSION_TYPES list
        accession_titles = [{'title': d_utils.convertStringToTitleCase(
            item), 'value': item} for item in STANDALONE_ACCESSION_TYPES if item in accession_types]
    else:
        # Other project types
        profile_types = list()

        for i in accession_types:
            profile_type = Profile().get_collection_handle().find_one({"type": {"$regex": i.upper(), "$options": "i"}},
                                                                      {"_id": 0, "type": 1})
            if profile_type:
                profile_types.append(
                    {'title':  profile_type.get("type", ""), 'value': i.upper()})

        accession_titles = profile_types

    return HttpResponse(json_util.dumps(accession_titles))
