from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import uuid
import json
import subprocess
from common.dal.copo_da import Sample, DataFile, Profile, Source, Submission, Description
from common.utils import helpers 
from django.http import HttpResponse
import datetime
from common.s3.s3Connection import S3Connection as s3
from pymongo import ReturnDocument
import common.read_utils.FileTransferUtils as tx
from .utils.EnaSpreadsheetParse import ENASpreadsheet
from django.conf import settings
from os.path import join
from pathlib import Path
from bson import json_util, ObjectId
from common.utils.logger import Logger
import jsonpickle
from common.read_utils import generic_helper as ghlper

@login_required()
def ena_read_manifest_validate(request, profile_id):
    request.session["profile_id"] = profile_id
    return render(request, "copo/ena_read_manifest_validate.html", {"profile_id": profile_id})

@login_required()
def parse_ena_spreadsheet(request):
    username = request.user.username
    profile_id = request.session["profile_id"]
    channels_group_name = "s3_" + profile_id
    helpers.notify_frontend(data={"profile_id": profile_id},
                    msg='', action="info",
                    html_id="sample_info", group_name=channels_group_name)    
    # method called by rest
    file = request.FILES["file"]
    name = file.name
    ena = ENASpreadsheet(file=file)
    s3obj = s3()
    if name.endswith("xlsx") or name.endswith("xls"):
        fmt = 'xls'
    else:
        return HttpResponse(status=415, content="Please make sure your manifest is in xlxs format")

    if ena.loadManifest(fmt):
        Logger().log("Dtol manifest loaded")
        if ena.validate():
            Logger().log("About to collect Dtol manifest")
            # check s3 for bucket and files files
            bucket_name = str(request.user.id) + "_" + request.user.username
            #bucket_name = request.user.username

            if s3obj.check_for_s3_bucket(bucket_name):
                # get filenames from manifest
                file_names = ena.get_filenames_from_manifest()
                # check for files
                if not s3obj.check_s3_bucket_for_files(bucket_name=bucket_name, file_list=file_names):
                    # error message has been sent to frontend by check_s3_bucket_for_files so return so prevent ena.collect() from running
                    return HttpResponse()
                # check if the files have been submitted or not
                files = []
                for f in file_names:
                    for i in f.split(","):
                        files.append(join(settings.UPLOAD_PATH, username, i.strip()))
  
                #sub = Submission().get_collection_handle().find_one({"profile_id": profile_id, "bundle_meta.file_location": {"$in": files}})
                #if sub and sub["accessions"]:
                #        return HttpResponse(content="The sample(s) has been submitted before, it cannot be updated", status=400)
            else:
                # bucket is missing, therefore create bucket and notify user to upload files
                helpers.notify_frontend(data={"profile_id": profile_id},
                                msg='s3 bucket not found, creating it', action="info",
                                html_id="sample_info", group_name=channels_group_name)                
                s3obj.make_s3_bucket(bucket_name=bucket_name)
                helpers.notify_frontend(data={"profile_id": profile_id},
                                msg='Files not found, please click "Upload Data into COPO" and follow the '
                                    'instructions.', action="info",
                                html_id="sample_info", group_name=channels_group_name)
                return HttpResponse()

            # iff all above have passed, then run collect
            ena.collect()

    return HttpResponse()

@login_required()
def save_ena_records(request):
    # create mongo sample objects from info parsed from manifest and saved to session variable
    sample_data = request.session.get("sample_data")
    profile_id = request.session["profile_id"]
    profile_name = Profile().get_name(profile_id)
    uid = request.user.id
    username = request.user.username
    alias = str(uuid.uuid4())
    bundle = list()
    bundle_meta = list()
    pairing = list()
    datafile_list = list()
    existing_bundle = list()
    existing_bundle_meta = list()
    sub = Submission().get_collection_handle().find_one({"profile_id": profile_id, "deleted": helpers.get_not_deleted_flag()})
    if sub:
        existing_bundle = sub["bundle"]
        existing_bundle_meta = sub["bundle_meta"]

    for p in range(1, len(sample_data)):
        # for each row in the manifest

        s = (helpers.map_to_dict(sample_data[0], sample_data[p]))

        # check if sample already exists, if so, add new datafile
        sample = Sample().get_collection_handle().find_one({"name": s["sample_name"], "profile_id": profile_id})
        if not sample:
            source = dict()
            curl_cmd = "curl " + \
                       "https://www.ebi.ac.uk/ena/taxonomy/rest/scientific-name/" + s["organism"].replace(" ", "%20")
            receipt = subprocess.check_output(curl_cmd, shell=True)
            # ToDo - exit if species not found
            print(receipt)

            taxinfo = json.loads(receipt.decode("utf-8"))

            # create source from organism
            termAccession = "http://purl.obolibrary.org/obo/NCBITaxon_" + str(taxinfo[0]["taxId"])
            source["organism"] = \
                {"annotationValue": s["organism"], "termSource": "NCBITAXON", "termAccession":
                    termAccession}
            #source["profile_id"] = request.session["profile_id"]
            source["date_created"] = datetime.datetime.utcnow()
            source["profile_id"] = profile_id
            source["deleted"] = "0"
            source_id = str(
                Source().get_collection_handle().find_one_and_update({"organism.termAccession": termAccession},
                                                                     {"$set": source},
                                                                     upsert=True, return_document=ReturnDocument.AFTER)["_id"])

            # create associated sample
            sample = dict()
            sample["sample_type"] = "isasample"
            #sample["profile_id"] = request.session["profile_id"]
            sample["derivesFrom"] = [source_id]
            sample["date_modified"] = datetime.datetime.utcnow()
            sample["profile_id"] = profile_id
            sample["name"] = s["sample_name"]
            sample["deleted"] = "0"
            sample_id = str(
                Sample().get_collection_handle().find_one_and_update({"name": sample["name"]}, {"$set": sample},
                                                                     upsert=True,
                                                                     return_document=ReturnDocument.AFTER)["_id"])
        else:
            sample_id = str(sample["_id"])

        df = dict()
        p = Profile().get_record(profile_id)
        attributes = dict()
        attributes["datafiles_pairing"] = list()
        attributes["target_repository"] = {"deposition_context": "ena"}
        attributes["project_details"] = {
            "project_name": p["title"],
            "project_title": p["title"],
            "project_description": p["description"],
            "project_release_date": s["release_date"]
        }
        attributes["library_preparation"] = {
            "library_layout": s["library_layout"],
            "library_strategy": s["library_strategy"],
            "library_source": s["library_source"],
            "library_selection": s["library_selection"],
            "library_description": s["library_description"]
        }
        attributes["attach_samples"] = {"study_samples": [sample_id]}
        attributes["nucleic_acid_sequencing"] = {"sequencing_instrument": s["sequencing_instrument"]}
        df["description"] = {"attributes": attributes}
        df["title"] = p["title"]
        df["date_created"] = datetime.datetime.utcnow()
        df["profile_id"] = str(p["_id"])
        df["file_type"] = "TODO"
        df["type"] = "RAW DATA FILE"

        df["bucket_name"] = str(request.user.id) + "_" + request.user.username
        #df["bucket_name"] = username

        # create local location
        Path(join(settings.UPLOAD_PATH, username)).mkdir(parents=True, exist_ok=True)

        # check if there are two files or one
        if s["library_layout"] == "SINGLE":
            # create single record
            f_name = s["file_name"]
            df["ecs_location"] = str(request.user.id) + "_" + request.user.username + "/" + f_name
            #df["ecs_location"] = username + "/" + f_name   #temp-solution
            df["file_name"] = f_name
            file_location = join(settings.UPLOAD_PATH, username, f_name)
            df["file_location"] = file_location
            df["name"] = f_name
            df["file_id"] = "NA"
            df["file_hash"] = s["md5"].strip()
            df["deleted"] = helpers.get_not_deleted_flag()
            inserted = DataFile().get_collection_handle().find_one_and_update({"file_location": file_location},
                                                                              {"$set": df}, upsert=True,
                                                                              return_document=ReturnDocument.AFTER)
            datafile_list.append(inserted)
            if str(inserted["_id"]) not in existing_bundle:  
                existing_bundle.append(str(inserted["_id"]))
                f_meta = {"file_id": str(inserted["_id"]), "file_location": file_location,
                        "upload_status": False}
                existing_bundle_meta.append(f_meta) 
        else:
            # create record for left
            tmp_pairing = dict()
            file_names = s["file_name"].split(",")
            f_name = file_names[0].strip()
            df["file_name"] = f_name
            df["ecs_location"] = str(request.user.id) + "_" + request.user.username + "/" + f_name
            #df["ecs_location"] = username + "/" + f_name   #temp-solution
            file_location = join(settings.UPLOAD_PATH, username, f_name)
            df["file_location"] = file_location
            df["name"] = f_name
            df["file_id"] = "NA"
            df["file_hash"] = s["md5"].split(",")[0].strip()
            df["deleted"] =  helpers.get_not_deleted_flag()
            inserted = DataFile().get_collection_handle().find_one_and_update({"file_location": file_location},
                                                                              {"$set": df}, upsert=True,
                                                                              return_document=ReturnDocument.AFTER)
            datafile_list.append(inserted)
            if str(inserted["_id"]) not in existing_bundle:  
                existing_bundle.append(str(inserted["_id"]))
                f_meta = {"file_id": str(inserted["_id"]), "file_location": file_location,
                        "upload_status": False}
                existing_bundle_meta.append(f_meta)
            #bundle.append(str(inserted["_id"]))
            #f_meta = {"file_id": str(inserted["_id"]), "file_location": file_location, "upload_status": False}
            # create record for right
            tmp_pairing["_id"] = str(inserted["_id"])
            #bundle_meta.append(f_meta)
            # df.pop("_id")
            f_name = file_names[1].strip()
            df["file_name"] = f_name
            df["ecs_location"] = str(request.user.id) + "_" + request.user.username + "/" + f_name
            #df["ecs_location"] = request.user.username + "/" + f_name
            file_location = join(settings.UPLOAD_PATH, username, f_name)
            df["file_location"] = file_location
            df["name"] = f_name
            df["file_id"] = "NA"
            df["file_hash"] = s["md5"].split(",")[1].strip()
            df["deleted"] =  helpers.get_not_deleted_flag()
            inserted = DataFile().get_collection_handle().find_one_and_update({"file_location": file_location},
                                                                              {"$set": df}, upsert=True,
                                                                              return_document=ReturnDocument.AFTER)
            datafile_list.append(inserted)
            bundle.append(str(inserted["_id"]))
            f_meta = {"file_id": str(inserted["_id"]), "file_location": file_location, "upload_status": False}
            if str(inserted["_id"]) not in existing_bundle:  
                existing_bundle.append(str(inserted["_id"]))
                f_meta = {"file_id": str(inserted["_id"]), "file_location": file_location,
                        "upload_status": False}
                existing_bundle_meta.append(f_meta)
                             
            tmp_pairing["_id2"] = str(inserted["_id"])
            pairing.append(tmp_pairing)
            #bundle_meta.append(f_meta)

    attributes["datafiles_pairing"] = pairing
    #read_files = [x["file_location"] for x in bundle_meta]

    
    #if sub and sub["accessions"]:
    #    return HttpResponse(content="", status=400)
        
    if not sub:
        sub = dict()
        sub["date_created"] = datetime.datetime.utcnow()
        sub["repository"] = "ena"
        sub["accessions"] = dict()
        sub["profile_id"] = profile_id
        
    sub["complete"] = "false"
    sub["user_id"] = uid
    sub["bundle_meta"] = existing_bundle_meta
    sub["bundle"] = existing_bundle
    sub["manifest_submission"] = 1
    sub["deleted"] = helpers.get_not_deleted_flag()

    # make description records and submissions record
    dr = Description().create_description(attributes=attributes, profile_id=profile_id, component='datafile',
                                          name=profile_name)
    sub["description_token"] = dr["_id"]

    if "_id" in sub:
        Submission().get_collection_handle().update_one({"_id": sub["_id"]}, {"$set": sub})
        sub_id = sub["_id"]
    else:
        sub_id = Submission().get_collection_handle().insert_one(sub).inserted_id

   
    for f in datafile_list:
        tx.make_transfer_record(file_id=f["_id"], submission_id=str(sub_id))

    return HttpResponse()

@login_required()
def process_urls(request):
    profile_id = helpers.get_current_request().session['profile_id']
    channels_group_name = "s3_" + profile_id
    helpers.notify_frontend(data={"profile_id": profile_id},
        msg='', action="info",
        html_id="sample_info", group_name=channels_group_name)       
    file_list = json.loads(request.POST["data"])
    bucket_name = str(request.user.id) + "_" + request.user.username
    #bucket_name = request.user.username

    s3con = s3()
 
    if not s3con.check_for_s3_bucket(bucket_name):
        helpers.notify_frontend(data={"profile_id": profile_id},
                msg='s3 bucket not found, creating it', action="info",
                html_id="sample_info", group_name=channels_group_name)   
        s3con.make_s3_bucket(bucket_name)
        helpers.notify_frontend(data={"profile_id": profile_id},
                msg='s3 bucket created', action="info",
                html_id="sample_info", group_name=channels_group_name)  
    urls_list = list()
    for file_name in file_list:
        if file_name and not file_name.endswith("/"):
            file_name = file_name.replace("*", "")
            url = s3con.get_presigned_url(bucket=bucket_name, key=file_name)
            file_url = {"name": file_name, "url": url}
            urls_list.append(file_url)
    return HttpResponse(json.dumps(urls_list))

@login_required()
def get_manifest_submission_list(request):
    profile_id = request.session["profile_id"]
    docs = Submission().get_collection_handle().find({"$and": [
        {"profile_id": profile_id},
        {"manifest_submission": {"$exists": True}},
        {"manifest_submission": {"$eq": 1}}
    ]})
    output = list(docs)
    out = json_util.dumps(output)
    return HttpResponse(out)

@login_required()
def init_manifest_submission(request):
    submission_id = request.POST["submission_id"]
    submission_repo = "ena"
    

    context = dict(status=True, message='')

    if not submission_id:
        context = dict(status=False, message='Submission identifier not found!')
        return context

    collection_handle = ghlper.get_submission_queue_handle()
    doc = collection_handle.find_one({"submission_id": submission_id})

    if not doc:  # submission not in queue, add to queue
        fields = dict(
            submission_id=submission_id,
            date_modified=helpers.get_datetime(),
            repository=submission_repo,
            processing_status='pending'
        )

        collection_handle.insert(fields)
        context['message'] = 'Submission has been added to the processing queue. Status update will be provided.'
    else:
        context['message'] = 'Submission is already in the processing queue.'

    ghlper.update_submission_status(status='info', message=context['message'], submission_id=submission_id)
    ghlper.logging_info(context['message'], submission_id)
    return HttpResponse()

@login_required()
def get_manifest_submission_list(request):
    profile_id = request.session["profile_id"]
    docs = Submission().get_collection_handle().find({"$and": [
        {"profile_id": profile_id},
        {"manifest_submission": {"$exists": True}},
        {"manifest_submission": {"$eq": 1}}
    ]})
    output = list(docs)
    out = json_util.dumps(output)
    return HttpResponse(out)

@login_required()
def get_submission_status(request):
    """
    function returns the status of a submission record
    :param request:
    :return:
    """

    context = dict()
    submission_ids = json.loads(request.POST.get("submission_ids", "[]"))
    submission_ids = [ObjectId(x) for x in submission_ids]

    # get completed submissions
    submission_records = Submission().get_collection_handle().find(
        {"_id": {"$in": submission_ids}},
        {'_id': 1, 'complete': 1, 'transcript': 1, 'manifest_submission': 1})

    for rec in submission_records:

        record_id = str(rec['_id'])
        new_data = dict(record_id=record_id)
        if rec.get("manifest_submission", 0):
            new_data["manifest_submission"] = 1
        context[new_data["record_id"]] = new_data

        new_data["complete"] = str(rec.get("complete", False)).lower()

        # get any transcript to provide a clearer picture
        status = rec.get("transcript", dict()).get('status', dict())
        new_data['transcript_status'] = status.get('type', str())  # status type is: 'info', 'error', or 'success'
        new_data['transcript_message'] = status.get('message', str())

        # completed submissions
        if new_data["complete"] == 'true':  # this is where we part ways
            continue

        # processing or queued for processing
        submission_queue_handle = ghlper.get_submission_queue_handle()

        if submission_queue_handle.find_one({"submission_id": record_id}):
            new_data["complete"] = "processing"
            continue

        # not submitted, not in processing queue, must be unsubmitted or in error state
        # we turn to transcript for answer: reason why recording status in transcript is important!
        # see: update_submission_status() in generic_helper.py
        new_data["complete"] = "error" if new_data['transcript_status'] == 'error' else "pending"

    return HttpResponse(jsonpickle.encode(context), content_type='application/json')