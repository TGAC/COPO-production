from django_tools.middlewares import ThreadLocal
from .copo_da import Sample, Source, Submission, DataFile, Profile, DAComponent
from django.conf import settings
from bson import ObjectId
import pandas as pd
from common.utils import helpers

def get_current_request():
    return ThreadLocal.get_current_request()

def get_samples_options():
    profile_id = get_current_request().session['profile_id']
    samples = Sample(profile_id).get_all_records()

    option_values = []
    for sd in samples:
        label = sd["name"]
        option_values.append({"value": str(sd["_id"]), "label": label})

    return option_values

def get_existing_study_options():
    subs = Submission().get_complete()
    out = list()
    out.append({
        "value": "required",
        "label": "-- select one --"
    })
    out.append({
        "value": "none",
        "label": "Not in COPO"
    })
    for s in subs:
        try:
            out.append(
                {
                    "value": s['profile_id'],
                    "label": s['accessions']['project']['accession']
                }
            )
        except:
            pass
    return out

def get_isasamples_json():
    '''
    returns isa samples in a profile
    :return
    '''
    profile_id = get_current_request().session['profile_id']
    samples = Sample(profile_id).get_all_records()

    value_field = str("id")
    label_field = str("sample_name")
    search_field = ["id", "sample_name"]
    secondary_label_field = ["meta_sample_name"]

    elem_json = dict(value_field=value_field,
                     label_field=label_field,
                     secondary_label_field=secondary_label_field,
                     search_field=search_field,
                     options=list())

    for sd in samples:
        if sd["sample_type"] == "isasample":
            elem_json.get("options").append(
                {
                    value_field: str(sd["_id"]),
                    label_field: sd["name"],
                    secondary_label_field[0]: sd["name"],
                    "sample_type": sd.get("sample_type", str())
                }
            )

    return elem_json


def generate_sources_json(target_id=None):
    profile_id = get_current_request().session['profile_id']

    if target_id:
        sources = list()
        sources.append(Source().get_record(target_id))
    else:
        sources = Source(profile_id).get_all_records()

    schema = Source().get_schema().get("schema_dict")

    value_field = str("id")
    label_field = str("source_name")
    search_field = ["id", "source_name"]
    secondary_label_field = ["meta_source_name"]
    component_records = dict()

    elem_json = dict(value_field=value_field,
                     label_field=label_field,
                     secondary_label_field=secondary_label_field,
                     search_field=search_field,
                     options=list(),
                     component_records=component_records)

    for src in sources:
        elem_json.get("options").append(
            {
                value_field: str(src["_id"]),
                label_field: src["name"],
                secondary_label_field[0]: src["name"]
            })

    return elem_json


def get_samples_json(target_id=None):
    '''
    returns all samples in a profile (i.e isa and biosamples)
    :return:
    '''
    profile_id = get_current_request().session['profile_id']

    if target_id:
        samples = list()
        samples.append(Sample().get_record(target_id))
    else:
        samples = Sample(profile_id).get_all_records()

    value_field = str("id")
    label_field = str("sample_name")
    search_field = ["id", "sample_name"]
    secondary_label_field = ["meta_sample_name"]

    elem_json = dict(value_field=value_field,
                     label_field=label_field,
                     secondary_label_field=secondary_label_field,
                     search_field=search_field,
                     options=list())

    for sd in samples:
        elem_json.get("options").append(
            {
                value_field: str(sd["_id"]),
                label_field: sd["name"],
                secondary_label_field[0]: sd["name"],
                "sample_type": sd.get("sample_type", str())
            })

    return elem_json


def get_datafiles_json(target_id=None):
    '''
    returns all datafile record
    :return:
    '''
    profile_id = get_current_request().session['profile_id']

    if target_id:
        datafiles = list()
        datafiles.append(DataFile().get_record(target_id))
    else:
        datafiles = DataFile(profile_id).get_all_records()

    value_field = str("id")
    label_field = str("datafile_name")
    search_field = ["id", "datafile_name"]
    secondary_label_field = ["meta_datafile_name"]

    elem_json = dict(value_field=value_field,
                     label_field=label_field,
                     secondary_label_field=secondary_label_field,
                     search_field=search_field,
                     options=list())

    for sd in datafiles:
        elem_json.get("options").append(
            {
                value_field: str(sd["_id"]),
                label_field: sd["name"],
                secondary_label_field[0]: sd["name"]
            })

    return elem_json


def generate_table_records(profile_id=str(), component=str(), record_id=str()):
    # function generates component records for building an UI table - please note that for effective tabular display,
    # all array and object-type fields (e.g., characteristics) are deferred to sub-table display.
    # please define such in the schema as "show_in_table": false and "show_as_attribute": true
    type = Profile().get_type(profile_id=profile_id)
    columns = list()
    data_set = list()

    # instantiate data access object
    da_object = DAComponent(profile_id, component)

    profile_type = type.lower()
    if "asg" in profile_type:
        profile_type = "asg"

    elif "dtol_env" in profile_type:
        profile_type = "dotl_env"

    elif "dtol" in profile_type:
        profile_type = "dtol"

    elif "erga" in profile_type:
        profile_type = "erga"

    current_schema_version = settings.MANIFEST_VERSION.get(profile_type.upper(), '')

    get_dtol_fields = type in ["Aquatic Symbiosis Genomics (ASG)", "Darwin Tree of Life (DTOL)",
                               "European Reference Genome Atlas (ERGA)",
                               "Darwin Tree of Life Environmental Samples (DTOL_ENV)"]
    # get and filter schema elements based on displayable columns and profile type
    if get_dtol_fields:

        schema = list()
        for x in da_object.get_schema().get("schema_dict"):
            if x.get("show_in_table", True) and profile_type in x.get("specifications",
                                                                      []) and current_schema_version in x.get(
                    "manifest_version", ""):
                schema.append(x)
    else:
        schema = list()
        for x in da_object.get_schema().get("schema_dict"):
            if (x.get("show_in_table", True) and (component != 'sample' or component == 'sample' and (
                    "biosample" in x.get("specifications", []) or "isasample" in x.get(
                    "specifications", [])))):
                schema.append(x)

    # build db column projection
    projection = [(x["id"].split(".")[-1], 1) for x in schema]

    filter_by = dict()
    if record_id:
        filter_by["_id"] = ObjectId(str(record_id))

    # retrieve and process records
    records = da_object.get_all_records_columns(sort_by="date_modified", sort_direction=1,
                                                projection=dict(projection), filter_by=filter_by)

    if len(records):
        df = pd.DataFrame(records)
        df['s_n'] = df.index

        df['record_id'] = df._id.astype(str)
        df["DT_RowId"] = df.record_id
        df.DT_RowId = 'row_' + df.DT_RowId
        df = df.drop('_id', axis='columns')

        columns.append(dict(data="record_id", visible=False))
        detail_dict = dict(className='summary-details-control detail-hover-message', orderable=False, data=None,
                           title='', defaultContent='', width="5%")

        columns.insert(0, detail_dict)

        df_columns = list(df.columns)

        for x in schema:
            x["id"] = x["id"].split(".")[-1]
            columns.append(dict(data=x["id"], title=x["label"]))
            if x["id"] not in df_columns:
                df[x["id"]] = str()
            df[x["id"]] = df[x["id"]].fillna('')

            if "dtol" not in x.get("specifications", []) or "asg" not in x.get("specifications", []):
                df[x["id"]] = df[x["id"]].apply(
                    helpers.resolve_control_output_apply, args=(x,))

        data_set = df.to_dict('records')

    return_dict = dict(dataSet=data_set,
                       columns=columns
                       )

    return return_dict