import pandas
import pymongo
from django.contrib.auth.models import User
from django.http import HttpResponse
from bson import json_util
from common.dal.sample_da import Sample
import common.dal.copo_base_da as da
import dateutil.parser as parser
from common.dal.mongo_util import cursor_to_list
from ..utils import finish_request


def get_number_of_users(request):
    users = User.objects.all()
    number = len(users)
    return HttpResponse(number)


def get_number_of_samples_by_sample_type(request, sample_type):
    # Dates must be ISO 8601 formatted
    try:                
        d_from = parser.parse(request.GET.get('d_from', None))
    except TypeError: 
        d_from = None

    try:                
        d_to = parser.parse(request.GET.get('d_to', None))
    except TypeError: 
        d_to = None


    if d_from and d_to is None:
        return HttpResponse(status=400, content=f'\'to date\' is required when \'from date\' is entered')

    if d_from is None and d_to:
        return HttpResponse(status=400, content=f'\'from date\' is required when \'to date\' is entered')

    if d_from and d_to and d_from > d_to:
        return HttpResponse(status=400, content=f'\'from date\' must be earlier than \'to date\'')
    
    # Strange Swagger API bug where sample_type is being passed 
    # as a comma instead of an empty string if it is not specified/provided
    sample_type = str() if sample_type == ',' else sample_type

    number = Sample().get_number_of_samples_by_sample_type(sample_type.lower(), d_from, d_to)
    return HttpResponse(number)


def get_number_of_samples(request):
    number = Sample().get_number_of_samples()
    return HttpResponse(number)


def get_number_of_profiles(request):
    number = da.handle_dict["profile"].count_documents({})
    return HttpResponse(number)


def get_number_of_datafiles(request):
    number = da.handle_dict["datafile"].count_documents({})
    return HttpResponse(number)


def combined_stats_json(request):
    stats = cursor_to_list(da.handle_dict["stats"].find(
        {}, {"_id": 0}).sort('date', pymongo.DESCENDING))
    df = pandas.DataFrame(stats, index=None)
    return HttpResponse(df.reset_index().to_json(orient='records'))


def samples_stats_csv(request):
    stats = cursor_to_list(
        da.handle_dict["stats"].find({}, {"_id": 0, "date": 1, "samples": 1, }).sort('date', pymongo.ASCENDING))
    df = pandas.DataFrame(stats, index=None)
    df = df.rename(columns={"samples": "num"})
    x = df.to_json(orient="records")
    return HttpResponse(x, content_type="text/json")


def samples_hist_json(request, metric):
    # get counts for each label in the supplied variable (metric) across tol samples
    if metric == "GAL":
        # need to merge PARTNER and GAL columns as this field has different names between tol types
        projection = {"GAL": 1, "PARTNER": 1, "_id": 0}
        s_list = list(Sample().get_collection_handle().find(
            {"$or": [{"TOL_PROJECT": "DTOL"}, {"TOL_PROJECT": "ASG"},
                     {"sample_type": "dtol"}, {"sample_type": "asg"}]},
            projection))
        df = pandas.DataFrame(s_list)
        df["GAL"][df["GAL"].isnull()] = df["PARTNER"][df["GAL"].isnull()]
    else:
        projection = {metric: 1, "_id": 0}
        s_list = list(Sample().get_collection_handle().find(
            {"$or": [{"TOL_PROJECT": "DTOL"}, {"TOL_PROJECT": "ASG"},
                     {"sample_type": "dtol"}, {"sample_type": "asg"}]},
            projection))
        df = pandas.DataFrame(s_list)

    # now get counts of each value label in dataframe
    u = df[metric].value_counts()
    out = list()
    for x in u.keys():
        out.append({"k": x, "v": int(u[x])})
    return HttpResponse(json_util.dumps(out))


def get_tol_projects(request):
    project_lst = da.handle_dict["profile"].distinct(
        "type")  # Get unique list of tol projects
    project_lst.sort()  # Sort the list of tol projects

    return finish_request(project_lst)


def get_associated_tol_projects(request):
    associated_project_lst = da.handle_dict["profile"].distinct(
        "associated_type")  # Get unique list of associated tol projects
    associated_project_lst = [
        item.get('label', '') for item in associated_project_lst]  # Get labels only
    associated_project_lst.sort()  # Sort the list of associated tol projects

    return finish_request(associated_project_lst)
