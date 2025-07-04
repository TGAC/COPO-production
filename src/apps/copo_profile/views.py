import json
import pymongo
import re
import requests

from bson import ObjectId
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from jsonpickle import encode
from lxml import etree
from django.http import HttpResponse
from rest_framework import status

from common.dal.mongo_util import cursor_to_list_str2
from common.dal.profile_da import Profile, ProfileInfo
from common.dal.submission_da import Submission
from common.ena_utils.generic_helper import get_study_status
from common.lookup.lookup import SRA_SUBMISSION_MODIFY_TEMPLATE, SRA_SUBMISSION_TEMPLATE
from common.utils.helpers import get_group_membership_asString, get_datetime, get_env
from common.utils.logger import Logger

# from dal.broker_da import BrokerDA, BrokerVisuals
from src.apps.copo_core.models import Banner
from src.apps.copo_core.models import SequencingCentre, ProfileType
from src.apps.copo_core.utils import get_all_profile_types_for_options_for_user


l = Logger()


@login_required
def copo_profile_index(request):
    # Banner and groups
    member_groups = get_group_membership_asString()
    banner = Banner.objects.filter(active=True)

    if len(banner) > 0:
        context = {'user': request.user, 'banner': banner[0]}
    else:
        context = {'user': request.user}
    context['groups'] = member_groups

    # Profiles
    uid = request.user.id
    # number of profile grids to display by default on a single page
    num_of_profiles_per_page = 8
    page = int(request.GET.get('page', 1))  # current page
    db_skip_num = num_of_profiles_per_page * (page - 1)

    # Retrieve shared profiles and user profiles
    profile_lst = Profile().get_all_profiles(user=None, id_only=True)
    profiles_length = len(profile_lst)

    shared_profiles_mapping = {
        p.get('_id', ''): p.get('shared', False) for p in profile_lst
    }
    excluded_shared_profileIDs = list()

    # Get/load 8 profiles on downwards scroll
    existing_profiles_paginated = Profile() \
        .get_collection_handle() \
        .aggregate([
            {"$match": {"_id": {"$in": list(shared_profiles_mapping.keys())}}},
            {"$addFields": {
                "submission_profile_id": {
                    "$convert": {
                        "input": "$_id",
                        "to": "string",
                        "onError": 0
                    }
                }
            }
            },
            {"$lookup":
                {
                    "from": 'SubmissionCollection',
                    "localField": "submission_profile_id",
                    "foreignField": "profile_id",
                    "pipeline": [
                        { "$match" : 
                         {"$expr": { "$eq": [ "ena", "$repository" ] }}
                        } ],
                    "as": "submission"
                }
             },
            {"$unwind": {'path': '$submission', "preserveNullAndEmptyArrays": True}},
            {"$sort":  {"date_created": pymongo.DESCENDING}},
            {"$skip": db_skip_num},
            {"$limit": num_of_profiles_per_page},
            {"$project": {"study_status": "$submission.accessions.project.status", "study_release_date": "$submission.accessions.project.release_date",
                          "sequencing_centre": 1, "title": 1, "description": 1, "associated_type": 1, "type": 1, "date_created": 1, "date_modified": 1}}
        ])
    
    profile_page = cursor_to_list_str2(
        existing_profiles_paginated, use_underscore_in_id=False
    )

    # Validate user shared profiles if any exists
    for index, item in enumerate(profile_page):
        profile_id = item.get('id', '')
        profile_page[index]['owner_name'] = Profile().get_user_full_name_by_id(
            profile_id
        )

        if shared_profiles_mapping.get(ObjectId(profile_id), ''):
            profile_page[index][
                'shared_owner_name'
            ] = Profile().get_user_full_name_by_id(profile_id, is_shared=True)
            profile_type = item.get('type', '')
            if ProfileType.objects.get(type=profile_type).is_permission_required:
                if f'{profile_type}_users' not in member_groups:
                    # Obtain a list of the profile IDs for the shared profiles that users
                    # have been added to but they do not belong to that profile group type
                    excluded_shared_profileIDs.append(item.get('id', ''))
            item['shared_type'] = profile_type
            del item['type']

    # Exclude a shared profile if a user does not belong to the shared profile group type
    if excluded_shared_profileIDs:
        profile_page = [
            profile
            for profile in profile_page
            if profile.get('id', '') not in excluded_shared_profileIDs
        ]
        # Reduce the total number of (owned and shared) profiles for the user
        profiles_length -= len(excluded_shared_profileIDs)

    num_of_pages = profiles_length / num_of_profiles_per_page  # row count
    profile_page_length = len(profile_page)
    profile_page_length += profile_page_length

    schema_map = dict()
    for profile in profile_page:
        profile_type = profile.get('type', '')
        if type not in schema_map:
            schema = Profile().get_component_schema(profile_type=profile_type)
            schema_map[profile_type] = schema
        schema = schema_map.get(profile_type, dict())

        for f in schema:
            f_id = f['id'].split('.')[-1]
            if f_id in profile and not f.get('show_in_table', False):
                profile.pop(f_id)

    if request.headers.get('x-requested-with') != 'XMLHttpRequest':
        # Set up the profile grids that are loaded by default when a user launches the web page
        context['profiles'] = profile_page
        context['profiles_total'] = profiles_length
        context['profiles_visible_length'] = len(profile_page)
        context['profiles_per_page'] = num_of_profiles_per_page
        context['profile_types'] = get_all_profile_types_for_options_for_user(
            request.user
        )
        return render(request, 'copo/profile/copo_profile_index.html', context)
    else:
        # Set up the profile grids that are loaded when a user scrolls down the web page
        output = dict()
        content = ''

        for profile in profile_page:
            content += render_to_string(
                'copo/profile/copo_profile_record.html',
                {
                    'profile': profile,
                    'profile_types': get_all_profile_types_for_options_for_user(
                        request.user
                    ),
                },
                request=request,
            )
        output['content'] = content
        output['profiles_total'] = profiles_length
        output['profiles_per_page'] = num_of_profiles_per_page
        output['end_pagination'] = True if page >= num_of_pages else False

        return JsonResponse(output)


"""
@login_required
def copo_profile_forms(request):
    context = dict()
    task = request.POST.get("task", str())

    profile_id = request.session.get("profile_id", str())

    if request.POST.get("profile_id", str()):
        profile_id = request.POST.get("profile_id")
        request.session["profile_id"] = profile_id

    broker_da = BrokerDA(auto_fields=request.POST.get("auto_fields", dict()),
                         component=request.POST.get("component", str()),
                         context=context,
                         profile_id=profile_id,
                         target_id=request.POST.get("target_id", str()),
                         user_email=request.POST.get("user_email", str()),
                         visualize=request.POST.get("visualize", str()))

    task_dict = dict(edit=broker_da.do_save_edit,
                     delete=broker_da.do_delete,
                     form=broker_da.do_form,
                     resources=broker_da.do_form_control_schemas,
                     save=broker_da.do_save_edit,
                     user_email=broker_da.do_user_email,
                     validate_and_delete=broker_da.validate_and_delete)

    if task in task_dict:
        context = task_dict[task]()

    out = jsonpickle.encode(context, unpicklable=False)
    return HttpResponse(out, content_type='application/json')


@login_required
def copo_profile_visualise(request):
    context = dict()

    task = request.POST.get("task", str())

    profile_id = request.session.get("profile_id", str())

    context["quick_tour_flag"] = request.session.get("quick_tour_flag", True)
    request.session["quick_tour_flag"] = context["quick_tour_flag"]  # for displaying tour message across site

    broker_visuals = BrokerVisuals(context=context,
                                   profile_id=profile_id,
                                   request=request,
                                   user_id=request.user.id,
                                   component=request.POST.get("component", str()),
                                   quick_tour_flag=request.POST.get("quick_tour_flag", False))

    task_dict = dict(help_messages=broker_visuals.get_component_help_messages,
                     profiles_counts=broker_visuals.do_profiles_counts,
                     update_quick_tour_flag=broker_visuals.do_update_quick_tour_flag)

    if task in task_dict:
        context = task_dict[task]()

    out = jsonpickle.encode(context, unpicklable=False)
    return HttpResponse(out, content_type='application/json')
"""


@login_required()
def delete_profile(request):
    profile_id = request.POST.get("target_id", "")

    response = HttpResponse(content_type="application/json")
    response.status_code = 200
    profile_undeleted = []

    if not profile_id:
        response.status_code = 405
    else:
        if not Profile().validate_and_delete(profile_id):
            profile_undeleted.append(profile_id)
            response.status_code = 405
    undeleted_json = json.dumps({"undeleted": [profile_undeleted]})
    response.write(undeleted_json)
    return response


@login_required
def get_profile_counts(request):
    profile_id = request.session["profile_id"]
    counts = ProfileInfo(profile_id).get_counts()
    return HttpResponse(encode(counts))


@login_required
def view_copo_profile(request, profile_id):
    request.session["profile_id"] = profile_id

    profile = Profile().get_record(profile_id)
    if not profile:
        return render(request, 'copo/error_page.html')
    context = {
        "p_id": profile_id,
        'counts': ProfileInfo(profile_id).get_counts(),
        "profile": profile,
    }
    return render(request, 'copo/copo_profile.html', context)


@login_required
def release_study(request, profile_id):
    submissions = Submission().execute_query({"profile_id": profile_id})
    if not submissions:
        return HttpResponse(
            status=status.HTTP_400_BAD_REQUEST, content="Submission not found"
        )

    submission = submissions[0]

    dt = get_datetime()
    ena_service = get_env('ENA_SERVICE')
    pass_word = get_env('WEBIN_USER_PASSWORD')
    user_token = get_env('WEBIN_USER').split("@")[0]

    # get study accession
    prj = submission.get('accessions', dict()).get('project', [{}])
    if not prj:
        message = f'Project accession not found for project: {profile_id}'
        l.log(message)
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST, content=message)

    project_accession = prj[0].get('accession', str())

    # get study status from API
    project_status = get_study_status(
        user_token=user_token, pass_word=pass_word, project_accession=project_accession
    )

    if not project_status:
        message = f'Cannot determine project release status for project: {profile_id}!'
        l.error(message)
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST, content=message)

    release_status = project_status[0].get('report', dict()).get('releaseStatus', str())

    if release_status.upper() == 'PUBLIC':
        # study already released, update the information in the db

        first_public = project_status[0].get('report', dict()).get('firstPublic', str())

        try:
            first_public = datetime.strptime(first_public, "%Y-%m-%dT%H:%M:%S")
        except Exception as e:
            first_public = dt

        prj[0]['status'] = 'PUBLIC'
        prj[0]['release_date'] = first_public

        Submission().get_collection_handle().update_one(
            {"_id": (submission["_id"])}, {'$set': {"accessions.project": prj}}
        )
        # return HttpResponse(status=200, content=f"Project was already released on {first_public}")
        first_public_str = first_public.strftime('%a, %d %b %Y %H:%M')
        return JsonResponse({"study_release_date": first_public_str})

    # release study
    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.parse(SRA_SUBMISSION_MODIFY_TEMPLATE, parser).getroot()
    actions = root.find('ACTIONS')
    action = etree.SubElement(actions, 'ACTION')
    l.log('Releasing project with accession: ' + project_accession)

    action_type = etree.SubElement(action, 'RELEASE')
    action_type.set("target", project_accession)

    xml_str = etree.tostring(root, encoding='utf8', method='xml')

    files = {'SUBMISSION': xml_str}
    receipt = None

    with requests.Session() as session:
        session.auth = (user_token, pass_word)
        try:
            response = session.post(ena_service, data={}, files=files)
            receipt = response.text
            l.log("ENA RECEIPT " + receipt)
        except etree.ParseError as e:
            l.log("Unrecognised response from ENA " + str(e))
            message = (
                " Unrecognised response from ENA - "
                + str(receipt)
                + " Please try again later, if it persists contact admins"
            )
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST, content=message)
        except Exception as e:
            l.exception(e)
            message = (
                'API call error '
                + "Submitting project xml to ENA via CURL. href is: "
                + ena_service
            )
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST, content=message)

    if receipt:
        root = etree.fromstring(bytes(receipt, 'utf-8'))

        if root.get('success') == 'false':
            message = "Couldn't release project due to the following errors: "
            errors = root.findall('.//ERROR')
            if errors:
                error_text = str()
                for e in errors:
                    error_text = error_text + " \n" + e.text
                message = message + error_text

            # log error
            l.error(message)
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST, content=message)

        # update submission record with study status
        l.log(
            "Project successfully released. Updating status in the database :"
            + profile_id
        )

        prj[0]['status'] = 'PUBLIC'
        prj[0]['release_date'] = dt

        Submission().get_collection_handle().update_one(
            {"_id": submission["_id"]}, {'$set': {"accessions.project": prj}}
        )

        # return HttpResponse(status=200, content="Project release successful.")
        dt_str = dt.strftime('%a, %d %b %Y %H:%M')
        return JsonResponse({"study_release_date": dt_str})


@login_required
def get_sequencing_centres(request):
    centres = SequencingCentre.objects.all()
    return HttpResponse(encode(centres), content_type='application/json')
