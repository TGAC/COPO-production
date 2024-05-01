import json
import os
import shutil
import subprocess
import uuid
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, date
from common.utils.logger import Logger
import requests
# from celery.utils.log import get_task_logger
from common.lookup.copo_enums import *
import common.schemas.utils.data_utils as d_utils
from common.dal.sample_da import Sample, Source
from common.dal.profile_da import Profile
from common.dal.submission_da import Submission
from common.utils.helpers import notify_frontend, get_env
from common.schema_versions.lookup.dtol_lookups import DTOL_ENA_MAPPINGS, DTOL_UNITS, PERMIT_COLUMN_NAMES_PREFIX, PERMIT_FILENAME_COLUMN_NAMES
from common.lookup.lookup import SRA_SETTINGS, SRA_SUBMISSION_TEMPLATE, SRA_SAMPLE_TEMPLATE, SRA_PROJECT_TEMPLATE, DTOL_SAMPLE_COLLECTION_LOCATION_STATEMENT
from .helpers import query_public_name_service
from bson import ObjectId
import re
from .copo_email import Email
from pathlib import Path
from django.conf import settings


with open(SRA_SETTINGS, "r") as settings_stream:
    sra_settings = json.loads(settings_stream.read())["properties"]

# logger = get_task_logger(__name__)
l = Logger()
# todo list of keys that shouldn't end up in the sample.xml file
exclude_from_sample_xml = []
ena_service = get_env('ENA_SERVICE')
ena_v2_service_async = get_env("ENA_V2_SERVICE_ASYNC")
ena_v2_service_sync = get_env("ENA_V2_SERVICE_SYNC")
ena_report = get_env('ENA_ENDPOINT_REPORT') + "samples"

# public_name_service = resolve_env.get_env('PUBLIC_NAME_SERVICE')

pass_word = get_env('WEBIN_USER_PASSWORD')
user_token = get_env('WEBIN_USER').split("@")[0]

sample_permits_directory_path = Path(settings.MEDIA_ROOT) / "sample_permits"
b2drop_permits_directory_path = get_env('B2DROP_PERMITS')

submission_id = ""
profile_id = ""


def process_pending_dtol_samples():
    '''
    method called from celery to initiate transfers to ENA, see celery.py for timings
    :return:
    '''

    # get all pending dtol submissions
    sub_id_list = Submission().get_pending_dtol_samples()
    tolidflag = True
    specimenID_map = dict()  # Map of specimen IDs

    # send each to ENA for Biosample ids
    for submission in sub_id_list:

        # check if study exist for this submission and/or create one
        profile_id = submission["profile_id"]
        type_submission = submission["type"]
        # removing study for general case, will be useful for subset of submissions
        '''if not Submission().get_study(submission['_id']):
            create_study(submission['profile_id'], collection_id=submission['_id'])'''
        file_subfix = str(
            uuid.uuid4())  # use this to recover bundle sample file
        build_bundle_sample_xml(file_subfix)
        s_ids = []
        # check for public name with Sanger Name Service
        public_name_list = list()
        rejected_sample = {}
        for s_id in submission["dtol_samples"]:
            log_message(
                f"Submission: Processing {s_id}", Loglvl.INFO, profile_id=profile_id)
            try:
                sam = Sample().get_record(s_id)
                if not sam:
                    log_message("No samples found for ID: " + str(s_id),
                                Loglvl.ERROR, profile_id=profile_id)
                    Submission().dtol_sample_rejected(
                        submission['_id'], sam_ids=[str(s_id)], submission_id=[])
                    # notify_frontend(data={"profile_id": profile_id}, msg="No sample found for id " + str(s_id), action="error",
                    #                html_id="dtol_sample_info")
                    # l.error("Dtol submission : 74 - no sample found for id " + str(s_id))
                    continue
            except:
                log_message("No samples found for ID: " + str(s_id),
                            Loglvl.ERROR, profile_id=profile_id)
                Submission().dtol_sample_rejected(
                    submission['_id'], sam_ids=[str(s_id)], submission_id=[])

                # notify_frontend(data={"profile_id": profile_id}, msg="No sample found for id " + str(s_id), action="error",
                #            html_id="dtol_sample_info")
                # l.error("Dtol submission : 77 - no sample found for id " + str(s_id))
                continue

            if sam["status"] == "sending":
                log_message(f"{s_id} is being processed by another celery task",
                            Loglvl.INFO, profile_id=profile_id)
                continue
            else:
                Sample().update_field("status", "sending", s_id)

            issymbiont = sam["species_list"][0].get("SYMBIONT", "TARGET")
            if issymbiont == "SYMBIONT":
                targetsam = Sample().get_target_by_specimen_id(
                    sam["SPECIMEN_ID"])
                try:
                    assert targetsam
                except AssertionError:
                    log_message("No target found by SPECIMEN_ID: " + sam["SPECIMEN_ID"], Loglvl.ERROR,
                                profile_id=profile_id)
                    # notify_frontend(data={"profile_id": profile_id}, msg="No target found " + sam["SPECIMEN_ID"], action="error",
                    #        html_id="dtol_sample_info")
                    # l.error("Dtol Submission : 78 - Assertion error, no target found")
                    break
                # ASSERT ALL TAXON ID ARE THE SAME, they can only be associated to one specimen
                try:
                    assert all(x["species_list"][0]["TAXON_ID"] == targetsam[0]["species_list"][0]["TAXON_ID"] for x in
                               targetsam)
                except AssertionError:
                    log_message("All taxon IDs are not the same, they can only be associated to one specimen",
                                Loglvl.ERROR, profile_id=profile_id)
                    # l.error("Dtol submission : 83 - Assertion error")
                    break
                targetsam = targetsam[0]
            else:
                # this is to speed up source public id call
                targetsam = sam
            print(type(sam['public_name']), sam['public_name'])

            if not sam["public_name"]:  # todo
                l.log("Dtol submission : 91 - sample has no public name")
                try:
                    if issymbiont == "TARGET":
                        public_name_list.append(
                            {"taxonomyId": int(sam["species_list"][0]["TAXON_ID"]), "specimenId": sam["SPECIMEN_ID"],
                             "sample_id": str(sam["_id"])})
                    else:
                        public_name_list.append(
                            {"taxonomyId": int(targetsam["species_list"][0]["TAXON_ID"]),
                             "specimenId": targetsam["SPECIMEN_ID"],
                             "sample_id": str(sam["_id"])})
                except ValueError:
                    log_message(" Invalid tax id found ",
                                Loglvl.ERROR, profile_id=profile_id)
                    # notify_frontend(data={"profile_id": profile_id}, msg="Invalid Taxon ID found", action="info",
                    #                html_id="dtol_sample_info")
                    # l.error("Dtol_submission : 105 - invalid taxon ID")
                    break

            s_ids.append(s_id)

            if not sam["SPECIMEN_ID"] in specimenID_map.keys():    
                # check if specimen ID biosample was already registered, if not do it
                specimen_sample = Source().get_specimen_biosample(
                    sam["SPECIMEN_ID"])
                try:
                    assert len(specimen_sample) <= 1
                except AssertionError:
                    log_message("Multiple sources for SPECIMEN_ID " + sam["SPECIMEN_ID"], Loglvl.ERROR,
                                profile_id=profile_id)
                    # l.error("Multiple sources for SPECIMEN_ID " + sam["SPECIMEN_ID"])
                    break
                specimen_accession = ""
                target_id = ""
                if specimen_sample:
                    target_id = str(specimen_sample[0]["_id"])
                    specimen_accession = specimen_sample[0].get(
                        "biosampleAccession", "")
                #    l.log("Specimen accession at 119 is " + specimen_accession)
                #else:
                    # create specimen object and submit
                log_message("Creating/Updating sample for SPECIMEN_ID: " + sam.get("RACK_OR_PLATE_ID", "") + "/" + sam[
                    "SPECIMEN_ID"], Loglvl.INFO, profile_id=profile_id)
                # l.log("creating specimen level sample for " + sam["SPECIMEN_ID"])
                # notify_frontend(data={"profile_id": profile_id},
                #                msg="Creating Sample for SPECIMEN_ID " + sam.get("RACK_OR_PLATE_ID", "") + "/" + sam[
                #                    "SPECIMEN_ID"],
                #                action="info",
                #                html_id="dtol_sample_info")
                if type_submission == "asg":
                    sample_type = "asg_specimen"
                elif type_submission == "erga":
                    sample_type = "erga_specimen"
                else:
                    sample_type = "dtol_specimen"

                # Save source/specimen and add object fields to the source/specimen
                if issymbiont == "TARGET":
                    specimen_obj_fields = {"SPECIMEN_ID": sam["SPECIMEN_ID"],
                                            "TAXON_ID": sam["species_list"][0]["TAXON_ID"],
                                            "sample_type": sample_type, "profile_id": sam['profile_id'], "target_id":target_id}

                    # Add permit filename to the source/specimen of erga sources
                    permit_filename_field = {}

                    if sam.get("SAMPLING_PERMITS_FILENAME", ""):
                        permit_filename_field.update(
                            {"SAMPLING_PERMITS_FILENAME": sam.get("SAMPLING_PERMITS_FILENAME", "")})

                    if sam.get("ETHICS_PERMITS_FILENAME", ""):
                        permit_filename_field.update(
                            {"ETHICS_PERMITS_FILENAME": sam.get("ETHICS_PERMITS_FILENAME", "")})

                    if sam.get("NAGOYA_PERMITS_FILENAME", ""):
                        permit_filename_field.update(
                            {"NAGOYA_PERMITS_FILENAME": sam.get("NAGOYA_PERMITS_FILENAME", "")})

                    obj_fields = {**specimen_obj_fields, **
                                    permit_filename_field }  # Merge dictionaries
                    Source().save_record(auto_fields={}, **obj_fields, )  # Save source/specimen record
                    specimen_obj_fields = populate_source_fields(sam)
                else:
                    # look for sample with same specimen ID which is target
                    specimen_obj_fields = {"SPECIMEN_ID": targetsam["SPECIMEN_ID"],
                                            "TAXON_ID": targetsam["species_list"][0]["TAXON_ID"],
                                            "sample_type": sample_type, "profile_id": targetsam['profile_id'], "target_id":target_id}

                    # Add permit filename to the source/specimen of erga sources
                    permit_filename_field = {}

                    if targetsam.get("SAMPLING_PERMITS_FILENAME", ""):
                        permit_filename_field.update(
                            {"SAMPLING_PERMITS_FILENAME": targetsam.get("SAMPLING_PERMITS_FILENAME", "")})

                    if targetsam.get("ETHICS_PERMITS_FILENAME", ""):
                        permit_filename_field.update(
                            {"ETHICS_PERMITS_FILENAME": targetsam.get("ETHICS_PERMITS_FILENAME", "")})

                    if targetsam.get("NAGOYA_PERMITS_FILENAME", ""):
                        permit_filename_field.update(
                            {"NAGOYA_PERMITS_FILENAME": targetsam.get("NAGOYA_PERMITS_FILENAME", "")})

                    obj_fields = {**specimen_obj_fields, **
                                    permit_filename_field}  # Merge dictionaries
                    Source().save_record(auto_fields={}, **obj_fields, target_id=target_id)  # Save source/specimen record
                    specimen_obj_fields = populate_source_fields(targetsam)

                # Add fields to the source/specimen
                sour = Source().get_by_specimen(sam["SPECIMEN_ID"])[0]
                Source().add_fields(specimen_obj_fields, str(sour['_id']))

                log_message("Specimen level sample for " + sam["SPECIMEN_ID"] + " was created/updated", Loglvl.INFO,
                            profile_id=profile_id)
                # l.log("created specimen level sample for " + sam["SPECIMEN_ID"])

                # source exists but doesn't have accession/source didn't exist
                #if not specimen_accession:
                log_message("Retrieving specimen level sample biosampleAccession for " + sam["SPECIMEN_ID"],
                            Loglvl.INFO, profile_id=profile_id)
                # l.log("retrieving specimen level sample biosampleAccession for " + sam["SPECIMEN_ID"])
                sour = Source().get_by_specimen(sam["SPECIMEN_ID"])
                try:
                    assert len(
                        sour) == 1, "more than one source for SPECIMEN_ID " + sam["SPECIMEN_ID"]
                except AssertionError:
                    log_message("AssertionError: more than one source for SPECIMEN_ID " + sam[
                        "SPECIMEN_ID" + ". Please contact COPO"], Loglvl.ERROR, profile_id=profile_id)
                    # l.error("AssertionError: more than one source for SPECIMEN_ID " + sam["SPECIMEN_ID"])
                    Sample().mark_processing(sample_ids=s_ids)
                    break
                sour = sour[0]
                if not sour['public_name']:
                    # retrieve public name
                    spec_tolid = query_public_name_service(
                        [{"taxonomyId": int(targetsam["species_list"][0]["TAXON_ID"]),
                            "specimenId": targetsam["SPECIMEN_ID"],
                            "sample_id": str(sam["_id"])}])
                    try:
                        assert len(spec_tolid) == 1
                    except AssertionError:
                        log_message("Cannot retrieve public name",
                                    Loglvl.ERROR, profile_id=profile_id)
                        # l.error("AssertionError: line 170 dtol submission")
                        Sample().mark_processing(sample_ids=s_ids)
                        break
                    if not spec_tolid[0].get("tolId", ""):
                        # hadle failure to get public names and halt submission
                        if spec_tolid[0].get("status", "") == "Rejected":
                            # halt submission and reject sample
                            toliderror = "public name error - " + \
                                spec_tolid[0].get("reason", "")
                            status = {}
                            status["msg"] = toliderror
                            Source().update_field(
                                "error", toliderror, sour["_id"])
                            Sample().add_rejected_status(status, s_id)
                            s_ids.remove(s_id)
                            Submission().dtol_sample_rejected(
                                submission['_id'], sam_ids=[s_id], submission_id=[])
                            rejected_sample[sam["rack_tube"]] = toliderror

                            msg = "A public name request was rejected, some submissions were halted -" + toliderror
                            log_message(msg, Loglvl.ERROR,
                                        profile_id=profile_id)
                            # notify_frontend(data={"profile_id": profile_id}, msg=msg, action="info",
                            #                html_id="dtol_sample_info")
                            continue
                        # change dtol_status to "awaiting_tolids"
                        msg = "We couldn't retrieve one or more public names, a request for a new tolId has been " \
                                "sent, COPO will try again in 24 hours"
                        log_message(msg, Loglvl.INFO, profile_id=profile_id)
                        # notify_frontend(data={"profile_id": profile_id}, msg=msg, action="info",
                        #                html_id="dtol_sample_info")
                        Submission().make_dtol_status_awaiting_tolids(
                            submission['_id'])
                        Sample().mark_processing(sample_ids=s_ids)
                        tolidflag = False
                        break
                    Source().update_public_name(spec_tolid[0])
                    sour = Source().get_by_specimen(sam["SPECIMEN_ID"])
                    assert len(sour) == 1
                    sour = sour[0]

                build_specimen_sample_xml(sour)
                build_submission_xml(str(sour['_id']), release=True, modify=sour.get("biosampleAccession", ""))
                log_message("Submitting specimen level sample to ENA for " + sam["SPECIMEN_ID"], Loglvl.INFO,
                            profile_id=profile_id)
                accessions = submit_biosample_v2(str(sour['_id']), Source(), submission['_id'], {}, type="source",
                                                    async_send=False)
                # l.log("submission status is " + str(accessions.get("status", "")), type=Logtype.FILE)
                if not accessions or accessions.get("status", "") == "error":
                    # Check for type/instance of accessions because it can be a boolean
                    if isinstance(accessions, dict): 
                        if handle_common_ENA_error(accessions.get("msg", ""), sour['_id']):
                            pass
                    else:
                        # msg = "Submission rejected: specimen level " + sam["SPECIMEN_ID"] + "<p>" + accessions[
                        #     "msg"] + "</p>" if accessions else "<p>" + " ERROR " + "</p>"
                        
                        msg_content =  "<br>" + accessions.get("msg", "") if accessions else "<br>" + " ERROR "
                        msg =  "Submission rejected: Specimen level " + sam["SPECIMEN_ID"] + msg_content

                        notify_frontend(data={"profile_id": profile_id}, msg=msg, action="error",
                                        html_id="dtol_sample_info")
                        status = {}
                        status["msg"] = msg
                        Sample().add_rejected_status(status, s_id)
                        s_ids.remove(s_id)
                        Submission().dtol_sample_rejected(
                            submission['_id'], sam_ids=[s_id], submission_id=[])
                        rejected_sample[sam["rack_tube"]] = msg
                        Source().get_collection_handle().delete_one(
                            {"_id": sour['_id'] , "biosampleAccession" : {"$ne": ""} })  
                        # Submission().make_dtol_status_pending(submission['_id'])
                        continue
                specimen_accession = Source().get_specimen_biosample(sam["SPECIMEN_ID"])[0].get("biosampleAccession",
                                                                                                "")

                if not specimen_accession:
                    l.log("No accessions found, set submission to pending")
                    Submission().make_dtol_status_pending(submission['_id'])
                    msg = "Connection issue - please try resubmit later"
                    log_message(msg, Loglvl.INFO, profile_id=profile_id)
                    # notify_frontend(data={"profile_id": profile_id}, msg=msg, action="info",
                    #                html_id="dtol_sample_info")
                    Submission().make_dtol_status_pending(submission['_id'])
                    Sample().mark_processing(sample_ids=s_ids)
                    break #break current submission and do next submission

                # Transfer permit files to b2drop
                sample_permits_directory = os.path.join(
                    sample_permits_directory_path, profile_id)

                # Check if sample permits directory exists and if specimen accession is not in the list of specimen IDs
                if  os.path.exists(sample_permits_directory):  # Check if sample permits directory exists
                    taxonID_directory = os.path.join(
                        b2drop_permits_directory_path, sam["TAXON_ID"])
                    for col_name in PERMIT_COLUMN_NAMES_PREFIX:  
                        if sam.get(f"{col_name}_REQUIRED", "N") == "N":
                            continue
                        # Skip if permit filename column is empty
                        b2drop_filename = sam.get(f"{col_name}_FILENAME", "")
                        if not b2drop_filename:
                            continue

                        # Get actual permit filename
                        permit_file = b2drop_filename.replace(
                            f"_{b2drop_filename.split('_')[-1]}", ".pdf")
                        permit_file_path = os.path.join(
                            sample_permits_directory, permit_file)
                        permit_type = col_name.title()

                        # Copy permit file from COPO 'media/sample_permits' directory to b2drop directory
                        try:
                            # Create taxonID directory if it doesn't exist
                            if not os.path.exists(taxonID_directory):
                                os.makedirs(taxonID_directory)

                            b2drop_file_path = Path(b2drop_permits_directory_path) / sam[
                                "TAXON_ID"] / b2drop_filename

                            shutil.copy2(permit_file_path, b2drop_file_path)

                            l.log(f"{b2drop_filename} file copied to b2drop")

                            # Create "readme.txt" file (if it doesn't exist) to store the permit file name,
                            # permit type and specimen ID
                            with open(os.path.join(b2drop_permits_directory_path, sam["TAXON_ID"], 'readme.txt'),
                                    'a+') as readmeFile:
                                # Check if the file is empty
                                # Traverse to the start of the file
                                readmeFile.seek(0)
                                # Get the first character in the file
                                first_character = readmeFile.read(1)

                                if not first_character:
                                    # Add a line to the readme if file is empty
                                    readmeFile.write(
                                        "This file contains all the permit files and types associated with each specimen ID." + "\n \n")
                                    readmeFile.write(
                                        "SPECIMEN_ID" + "  " + "Permit_Type" + "  " + "Permit_Filename" + "\n")
                                else:
                                    # Traverse to the end of the file
                                    readmeFile.seek(0, os.SEEK_END)

                                # Add a line to the readme file
                                readmeFile.write(
                                    sam["SPECIMEN_ID"] + "  " + permit_type.replace(" ", "_") + "  " + sam.get(
                                        f"{col_name}_FILENAME", "") + "\n")

                        except Exception as error:
                            print("Error:", error)
                            l.exception(error)

                # Add specimen ID to list
                specimenID_map[sam["SPECIMEN_ID"]] = specimen_accession  


            specimen_accession = specimenID_map.get(sam["SPECIMEN_ID"],"")
            if not specimen_accession:
                l.log("no accession found, set submission to pending")
                Submission().make_dtol_status_pending(submission['_id'])
                msg = "Connection issue - please try resubmit later"
                log_message(msg, Loglvl.INFO, profile_id=profile_id)
                # notify_frontend(data={"profile_id": profile_id}, msg=msg, action="info",
                #                html_id="dtol_sample_info")
                Submission().make_dtol_status_pending(submission['_id'])
                Sample().mark_processing(sample_ids=s_ids)
                break  #break the current submission and do next submission

            # set appropriate relationship to specimen level sample
            l.log("setting relationship to specimen level sample for " +
                  sam["SPECIMEN_ID"])
            if issymbiont == "SYMBIONT":
                Sample().update_field("sampleSymbiontOf",
                                      specimen_accession, sam['_id'])
                sam["sampleSymbiontOf"] = specimen_accession
            elif sam.get('ORGANISM_PART', '') == "WHOLE_ORGANISM":
                Sample().update_field("sampleSameAs",
                                      specimen_accession, sam['_id'])
                sam["sampleSameAs"] = specimen_accession
            else:
                Sample().update_field("sampleDerivedFrom",
                                      specimen_accession, sam['_id'])
                sam["sampleDerivedFrom"] = specimen_accession

            # making sure relationship between sample and specimen level sample is set
            try:
                updated_sample = Sample().get_record(sam['_id'])
                assert any([updated_sample.get("sampleSymbiontOf", ""), updated_sample.get("sampleSameAs", ""),
                            updated_sample.get("sampleDerivedFrom", "")])
            except AssertionError:
                log_message("Missing relationship to parent sample for sample " + str(sam["_id"]), Loglvl.ERROR,
                            profile_id=profile_id)
                Submission().make_dtol_status_pending(submission['_id'])
                break

            log_message(f"Adding to Sample {s_id} Batch: " +
                        sam["SPECIMEN_ID"], Loglvl.INFO, profile_id=profile_id)
            # notify_frontend(data={"profile_id": profile_id}, msg="Adding to Sample Batch: " + sam["SPECIMEN_ID"],
            #                action="info",
            #                html_id="dtol_sample_info")

        else:

            # query for public names and update
            notify_frontend(data={"profile_id": profile_id}, msg="Querying public naming service", action="info",
                            html_id="dtol_sample_info")
            l.log("Querying public name service at line 489")
            public_names = query_public_name_service(public_name_list)
            tolidflag = True
            if any(not public_names[x].get("tolId", "") for x in range(len(public_names))):
                # hadle failure to get public names and halt submission
                if all(public_names[x].get("status", "") == "Rejected" for x in range(len(public_names))):
                    Submission().dtol_sample_rejected(submission['_id'], sam_ids=[submission["dtol_samples"]],
                                                      submission_id=[])
                    rejected_sample["All"] = "all missing tolid request were rejected"
                    log_message(msg, Loglvl.ERROR, profile_id=profile_id)
                    tolidflag = False
                else:
                    # change dtol_status to "awaiting_tolids"
                    # l.log("one or more public names missing, setting to awaiting_tolids")
                    msg = "We couldn't retrieve one or more public names, a request for a new public name (tolId) has been sent, " \
                          "COPO will try again in 24 hours"
                    log_message(msg, Loglvl.INFO, profile_id=profile_id)
                    # notify_frontend(data={"profile_id": profile_id}, msg=msg, action="info",
                    #                html_id="dtol_sample_info")
                    Submission().make_dtol_status_awaiting_tolids(
                        submission['_id'])
                    Sample().mark_processing(sample_ids=s_ids)
                    notify_frontend(data={"profile_id": profile_id}, msg=msg, action="info",
                                    html_id="dtol_sample_info")
                    tolidflag = False

            for name in public_names:
                l.log("adding public names to samples")
                if name.get("tolId", ""):
                    Sample().update_public_name(name)
                if name.get("status", "") == "Rejected":
                    Sample().add_rejected_status_for_tolid(
                        name['specimen']["specimenId"])
                    processed = Sample().get_by_profile_and_field(submission["profile_id"], "SPECIMEN_ID",
                                                                  [name['specimen']["specimenId"]])
                    processedids = [str(x) for x in processed]
                    # for sampleid in processedids:
                    Submission().dtol_sample_rejected(
                        submission['_id'], sam_ids=processedids, submission_id=[])
                    rejected_sample[name['specimen']["specimenId"]
                                    ] = "all missing tolid request were rejected"

            if rejected_sample:
                profile = Profile().get_record(profile_id)
                if profile:
                    Email().notify_sample_rejected_after_approval(project=d_utils.get_profile_type(profile["type"]),
                                                                  title=profile["title"],
                                                                  description=profile["description"],
                                                                  rejected_sample=rejected_sample)
            # if tolid missing for specimen skip
            if not tolidflag:
                l.log("missing tolid, removing draft xml")
                os.remove("bundle_" + file_subfix + ".xml")
                continue

            l.log("updating bundle xml")
            if len(s_ids) == 0:
                notify_frontend(data={"profile_id": profile_id}, msg="Nothing more to submit", action="info",
                                html_id="dtol_sample_info")
                # if all samples were moved to rejected
                continue

            # for update
            build_bundle_sample_xml(file_subfix + "-01")
            if update_bundle_sample_xml(s_ids, "bundle_" + file_subfix + "-01" + ".xml", is_modify=True):
                build_submission_xml(file_subfix + "-01", modify=True)
                # store accessions, remove sample id from bundle and on last removal, set status of submission
                l.log("submitting modify bundle xml to ENA")
                accessions = submit_biosample_v2(file_subfix + "-01", Sample(), submission['_id'], s_ids,
                                                 async_send=True)

            # for add
            build_bundle_sample_xml(file_subfix + "-02")
            if update_bundle_sample_xml(s_ids, "bundle_" + file_subfix + "-02" + ".xml", is_modify=False):
                build_submission_xml(file_subfix + "-02", release=True)
                # store accessions, remove sample id from bundle and on last removal, set status of submission
                l.log("submitting bundle xml to ENA")
                accessions = submit_biosample_v2(file_subfix + "-02", Sample(), submission['_id'], s_ids,
                                                 async_send=True)


def query_awaiting_tolids():
    # get all submission awaiting for tolids
    l.log("Running awaiting tolid task ")
    sub_id_list = Submission().get_awaiting_tolids()
    for submission in sub_id_list:
        rejected_sample = {}
        public_name_list = list()
        samplelist = submission["dtol_samples"]
        l.log("samplelist to go trough is " + str(samplelist))
        for samid in samplelist:
            try:
                sam = Sample().get_record(samid)
            except Exception as e:
                l.error("error at line 270 " + str(e))
            l.log("sample is " + str(sam))
            if not sam["public_name"]:
                try:
                    public_name_list.append(
                        {"taxonomyId": int(sam["species_list"][0]["TAXON_ID"]), "specimenId": sam["SPECIMEN_ID"],
                         "sample_id": str(sam["_id"])})
                except ValueError:
                    l.error("Value Error" + str(sam))
                    return False
        try:
            assert len(public_name_list) > 0
        except AssertionError:
            l.error("Assertion Error in query awaiting tolids")
        public_names = query_public_name_service(public_name_list)
        # still no response, do nothing
        # NOTE the query fails even if only one TAXON_ID can't be found
        if not public_names:
            l.error("No public names returned")
            return
        # update samples and set dtol_sattus to pending
        else:
            for name in public_names:
                if name.get("tolId", ""):
                    Sample().update_public_name(name)
                elif name.get("status", "") == "Rejected":
                    toliderror = "public name error - " + \
                        name.get("reason", "")
                    status = {}
                    status["msg"] = toliderror
                    toreject = Sample().get_target_by_field("SPECIMEN_ID",
                                                            name.get("specimen", "").get("specimenId", ""))
                    for rejsam in toreject:
                        Sample().update_field(
                            "error", toliderror, rejsam["_id"])
                        Sample().add_rejected_status(status, rejsam["_id"])
                        # remove samples from submissionlist
                        print(str(rejsam["_id"]))
                        Submission().dtol_sample_rejected(submission['_id'], sam_ids=[str(rejsam["_id"])],
                                                          submission_id=[])
                        rejected_sample[name.get("specimen", "").get(
                            "specimenId", "")] = toliderror
                else:
                    l.log("Still no tolId identified for " + str(name))
                    return
        l.log("Changing submission status from awaiting tolids to pending")
        Submission().make_dtol_status_pending(submission["_id"])
        if rejected_sample:
            profile = Profile().get_record(profile_id)
            if profile:
                Email().notify_sample_rejected_after_approval(project=d_utils.get_profile_type(profile["type"]),
                                                              title=profile["title"],
                                                              description=profile["description"],
                                                              rejected_sample=rejected_sample)


def populate_source_fields(sampleobj):
    '''populate source in db to copy most of sample fields
    but change organism part and gal sample_id'''
    fields = {}
    project = sampleobj["tol_project"]
    for item in sampleobj.items():
        # print(item)
        try:
            if project == "DTOL":
                if item[0] == "PARTNER" or item[0] == "PARTNER_SAMPLE_ID":
                    continue
            elif project == "ASG":
                if item[0] == "GAL" or item[0] == "GAL_SAMPLE_ID":
                    continue
            print(item[0])
            if item[0] == "COLLECTION_LOCATION" or DTOL_ENA_MAPPINGS[item[0]]['ena']:
                if item[0] == "GAL_SAMPLE_ID" or item[0] == "PARTNER_SAMPLE_ID":
                    fields[item[0]] = "NOT_PROVIDED"
                elif item[0] == "ORGANISM_PART":
                    fields[item[0]] = "WHOLE_ORGANISM"
                elif item[0] != "sampleDerivedFrom" :
                    fields[item[0]] = item[1]
        except KeyError:
            pass
    return fields


def build_bundle_sample_xml(file_subfix):
    '''build structure and save to file bundle_file_subfix.xml'''
    shutil.copy(SRA_SAMPLE_TEMPLATE, "bundle_" + file_subfix + ".xml")


def update_bundle_sample_xml(sample_list, bundlefile, is_modify=False):
    '''update the sample with submission alias adding a new sample'''
    # print("adding sample to bundle sample xml")
    tree = ET.parse(bundlefile)
    root = tree.getroot()
    project = Sample().get_record(sample_list[0]).get('tol_project', 'DTOL')
    is_found = False
    for sam in sample_list:
        sample = Sample().get_record(sam)
        if sample["biosampleAccession"] and not is_modify:
            continue
        elif not sample["biosampleAccession"] and is_modify:
            continue
        is_found = True
        sample_alias = ET.SubElement(root, 'SAMPLE')
        # updated to copo id to retrieve it when getting accessions
        sample_alias.set('alias', str(sample['_id']))
        # mandatory for broker account
        sample_alias.set('center_name', 'EarlhamInstitute')
        title = str(uuid.uuid4()) + "-" + project.lower()

        title_block = ET.SubElement(sample_alias, 'TITLE')
        title_block.text = title
        sample_name = ET.SubElement(sample_alias, 'SAMPLE_NAME')
        taxon_id = ET.SubElement(sample_name, 'TAXON_ID')
        taxon_id.text = sample.get("species_list", [])[0].get('TAXON_ID', "")
        # add sample description
        collection_location = sample.get("COLLECTION_LOCATION", "")
        collection_country = collection_location.split("|")[0].strip()
        if collection_country:
            statement = DTOL_SAMPLE_COLLECTION_LOCATION_STATEMENT.get(
                collection_country.upper(), "")
            if statement:
                description = ET.SubElement(sample_alias, "DESCRIPTION")
                description.text = statement

        sample_attributes = ET.SubElement(sample_alias, 'SAMPLE_ATTRIBUTES')
        # validating against TOL checklist
        sample_attribute = ET.SubElement(sample_attributes, 'SAMPLE_ATTRIBUTE')
        tag = ET.SubElement(sample_attribute, 'TAG')
        tag.text = 'ENA-CHECKLIST'
        value = ET.SubElement(sample_attribute, 'VALUE')
        value.text = 'ERC000053'

        sample_attribute = ET.SubElement(sample_attributes, 'SAMPLE_ATTRIBUTE')
        tag = ET.SubElement(sample_attribute, 'TAG')
        tag.text = 'project name'
        value = ET.SubElement(sample_attribute, 'VALUE')
        value.text = project
        # if project is ASG add symbiont
        if project == "ASG":
            sample_attribute = ET.SubElement(
                sample_attributes, 'SAMPLE_ATTRIBUTE')
            tag = ET.SubElement(sample_attribute, 'TAG')
            tag.text = 'SYMBIONT'
            value = ET.SubElement(sample_attribute, 'VALUE')
            if sample.get("species_list", [])[0].get('SYMBIONT', "") == "symbiont":
                issymbiont = True
            else:
                issymbiont = False
            if issymbiont:
                value.text = "Y"
            else:
                value.text = "N"
        # for item in obj_id: if item in checklist (or similar according to some criteria).....
        for item in sample.items():
            if item[1]:
                try:
                    # exceptional handling of fields that should only be present for certain projects
                    if project == "DTOL":
                        if item[0] == "PARTNER" or item[0] == "PARTNER_SAMPLE_ID" or item[
                                0] == "SYMBIONT":  # TODO CHANGE IN SOP2.3
                            continue
                    elif project == "ASG":
                        if item[0] == "GAL" or item[0] == "GAL_SAMPLE_ID":
                            continue
                    # exceptional handling of COLLECTION_LOCATION
                    if item[0] == 'COLLECTION_LOCATION':
                        attribute_name = DTOL_ENA_MAPPINGS['COLLECTION_LOCATION_1']['ena']
                        sample_attribute = ET.SubElement(
                            sample_attributes, 'SAMPLE_ATTRIBUTE')
                        tag = ET.SubElement(sample_attribute, 'TAG')
                        tag.text = attribute_name
                        value = ET.SubElement(sample_attribute, 'VALUE')
                        value.text = str(item[1]).split('|')[0].strip()
                        attribute_name = DTOL_ENA_MAPPINGS['COLLECTION_LOCATION_2']['ena']
                        sample_attribute = ET.SubElement(
                            sample_attributes, 'SAMPLE_ATTRIBUTE')
                        tag = ET.SubElement(sample_attribute, 'TAG')
                        tag.text = attribute_name
                        value = ET.SubElement(sample_attribute, 'VALUE')
                        value.text = '|'.join(str(item[1]).split('|')[1:])
                          
                    elif item[0] in ["DATE_OF_COLLECTION"]:
                        attribute_name = DTOL_ENA_MAPPINGS[item[0]]['ena']
                        sample_attribute = ET.SubElement(
                            sample_attributes, 'SAMPLE_ATTRIBUTE')
                        tag = ET.SubElement(sample_attribute, 'TAG')
                        tag.text = attribute_name
                        value = ET.SubElement(sample_attribute, 'VALUE')
                        collection_dates = item[1].split("-")
                        collection_date =  collection_dates[0]+("-"+ collection_dates[1] if len(collection_dates) >= 2 else "") + ("-"+ collection_dates[2] if len(collection_dates) >= 3 else "")
                        value.text = collection_date
                        if len(collection_dates) >= 3 and sample.get("TIME_OF_COLLECTION",""):
                            collection_date = datetime.strptime(collection_date + " " + sample["TIME_OF_COLLECTION"], "%Y-%m-%d %H:%M")
                            value.text = collection_date.isoformat()

                    elif item[0] in ["DECIMAL_LATITUDE", "DECIMAL_LONGITUDE", "LATITUDE_START", "LONGITUDE_START", "LATITUDE_END", "LONGITUDE_END"]:
                        if item[1] != "NOT_COLLECTED":
                            attribute_name = DTOL_ENA_MAPPINGS[item[0]]['ena']
                            sample_attribute = ET.SubElement(
                                sample_attributes, 'SAMPLE_ATTRIBUTE')
                            tag = ET.SubElement(sample_attribute, 'TAG')
                            tag.text = attribute_name
                            value = ET.SubElement(sample_attribute, 'VALUE')
                            value.text = str(round(float(item[1]), 8))
                        else:
                            continue
                    # handling annoying edge case below
                    elif item[0] == "LIFESTAGE" and item[1] == "SPORE_BEARING_STRUCTURE":
                        attribute_name = DTOL_ENA_MAPPINGS[item[0]]['ena']
                        sample_attribute = ET.SubElement(
                            sample_attributes, 'SAMPLE_ATTRIBUTE')
                        tag = ET.SubElement(sample_attribute, 'TAG')
                        tag.text = attribute_name
                        value = ET.SubElement(sample_attribute, 'VALUE')
                        value.text = "spore-bearing structure"
                    else:
                        attribute_name = DTOL_ENA_MAPPINGS[item[0]]['ena']
                        sample_attribute = ET.SubElement(
                            sample_attributes, 'SAMPLE_ATTRIBUTE')
                        tag = ET.SubElement(sample_attribute, 'TAG')
                        tag.text = attribute_name
                        value = ET.SubElement(sample_attribute, 'VALUE')
                        value.text = str(item[1]).replace("_", " ")
                    # add ena units where necessary
                    if DTOL_UNITS.get(item[0], ""):
                        if DTOL_UNITS[item[0]].get('ena_unit', ""):
                            unit = ET.SubElement(sample_attribute, 'UNITS')
                            unit.text = DTOL_UNITS[item[0]]['ena_unit']
                except KeyError:
                    # pass, item is not supposed to be submitted to ENA
                    pass

    ET.dump(tree)
    tree.write(open(bundlefile, 'w'),
               encoding='unicode')
    return is_found


def build_specimen_sample_xml(sample):
    # build specimen sample XML
    tree = ET.parse(SRA_SAMPLE_TEMPLATE)
    root = tree.getroot()
    project = sample['sample_type'].split("_")[0].upper()
    # from toni's code below
    # set sample attributes
    sample_alias = ET.SubElement(root, 'SAMPLE')
    # updated to copo id to retrieve it when getting accessions
    sample_alias.set('alias', str(sample['_id']))
    # mandatory for broker account
    sample_alias.set('center_name', 'EarlhamInstitute')
    title = str(uuid.uuid4()) + "-" + project + "-specimen"

    title_block = ET.SubElement(sample_alias, 'TITLE')
    title_block.text = title
    sample_name = ET.SubElement(sample_alias, 'SAMPLE_NAME')
    taxon_id = ET.SubElement(sample_name, 'TAXON_ID')
    taxon_id.text = sample.get('TAXON_ID', "")

    sample_attributes = ET.SubElement(sample_alias, 'SAMPLE_ATTRIBUTES')
    # validating against DTOL checklist
    sample_attribute = ET.SubElement(sample_attributes, 'SAMPLE_ATTRIBUTE')
    tag = ET.SubElement(sample_attribute, 'TAG')
    tag.text = 'ENA-CHECKLIST'
    value = ET.SubElement(sample_attribute, 'VALUE')
    value.text = 'ERC000053'
    # adding project name field (ie copo profile name)
    # validating against DTOL checklist
    sample_attribute = ET.SubElement(sample_attributes, 'SAMPLE_ATTRIBUTE')
    tag = ET.SubElement(sample_attribute, 'TAG')
    tag.text = 'project name'
    value = ET.SubElement(sample_attribute, 'VALUE')
    value.text = project
    # for item in obj_id: if item in checklist (or similar according to some criteria).....
    for item in sample.items():
        if item[1]:
            try:
                # exceptional handling of fields that may be empty in different projects
                if project == "ASG":
                    if item[0] == 'GAL' or item[0] == "GAL_SAMPLE_ID":
                        continue
                elif project == "DTOL" or project == "ERGA":
                    if item[0] == "PARTNER" or item[0] == "PARTNER_SAMPLE_ID":
                        continue
                # exceptional handling of COLLECTION_LOCATION
                if item[0] == 'COLLECTION_LOCATION':
                    attribute_name = DTOL_ENA_MAPPINGS['COLLECTION_LOCATION_1']['ena']
                    sample_attribute = ET.SubElement(
                        sample_attributes, 'SAMPLE_ATTRIBUTE')
                    tag = ET.SubElement(sample_attribute, 'TAG')
                    tag.text = attribute_name
                    value = ET.SubElement(sample_attribute, 'VALUE')
                    value.text = str(item[1]).split('|')[0].strip()
                    attribute_name = DTOL_ENA_MAPPINGS['COLLECTION_LOCATION_2']['ena']
                    sample_attribute = ET.SubElement(
                        sample_attributes, 'SAMPLE_ATTRIBUTE')
                    tag = ET.SubElement(sample_attribute, 'TAG')
                    tag.text = attribute_name
                    value = ET.SubElement(sample_attribute, 'VALUE')
                    value.text = '|'.join(str(item[1]).split('|')[1:])
                elif item[0] in ["DATE_OF_COLLECTION"]:
                    attribute_name = DTOL_ENA_MAPPINGS[item[0]]['ena']
                    sample_attribute = ET.SubElement(
                        sample_attributes, 'SAMPLE_ATTRIBUTE')
                    tag = ET.SubElement(sample_attribute, 'TAG')
                    tag.text = attribute_name
                    value = ET.SubElement(sample_attribute, 'VALUE')
                    collection_dates = item[1].split("-")
                    collection_date =  collection_dates[0]+("-"+ collection_dates[1] if len(collection_dates) >= 2 else "") + ("-"+ collection_dates[2] if len(collection_dates) >= 3 else "")
                    value.text = collection_date
                    if len(collection_dates) >= 3 and sample.get("TIME_OF_COLLECTION",""):
                        collection_date = datetime.strptime(collection_date + " " + sample["TIME_OF_COLLECTION"], "%Y-%m-%d %H:%M")
                        value.text = collection_date.isoformat()

                elif item[0] in ["DECIMAL_LATITUDE", "DECIMAL_LONGITUDE", "LATITUDE_START", "LONGITUDE_START", "LATITUDE_END", "LONGITUDE_END"]:
                    if item[1] != "NOT_COLLECTED":
                        attribute_name = DTOL_ENA_MAPPINGS[item[0]]['ena']
                        sample_attribute = ET.SubElement(
                            sample_attributes, 'SAMPLE_ATTRIBUTE')
                        tag = ET.SubElement(sample_attribute, 'TAG')
                        tag.text = attribute_name
                        value = ET.SubElement(sample_attribute, 'VALUE')
                        value.text = str(round(float(item[1]), 8))
                    else:
                        continue

                elif item[0] == "LIFESTAGE" and item[1] == "SPORE_BEARING_STRUCTURE":
                    attribute_name = DTOL_ENA_MAPPINGS[item[0]]['ena']
                    sample_attribute = ET.SubElement(
                        sample_attributes, 'SAMPLE_ATTRIBUTE')
                    tag = ET.SubElement(sample_attribute, 'TAG')
                    tag.text = attribute_name
                    value = ET.SubElement(sample_attribute, 'VALUE')
                    value.text = "spore-bearing structure"
                elif item[0] == "VOUCHER_ID" or item[0] == "DNA_VOUCHER_ID_FOR_BIOBANKING":
                    attribute_name = DTOL_ENA_MAPPINGS[item[0]]['ena']

                    for val_text in item[1].split('|'):
                        sample_attribute = ET.SubElement(
                            sample_attributes, 'SAMPLE_ATTRIBUTE')
                        tag = ET.SubElement(sample_attribute, 'TAG')
                        tag.text = attribute_name
                        value = ET.SubElement(sample_attribute, 'VALUE')
                        value.text = val_text.strip()
                else:
                    attribute_name = DTOL_ENA_MAPPINGS[item[0]]['ena']
                    sample_attribute = ET.SubElement(
                        sample_attributes, 'SAMPLE_ATTRIBUTE')
                    tag = ET.SubElement(sample_attribute, 'TAG')
                    tag.text = attribute_name
                    value = ET.SubElement(sample_attribute, 'VALUE')
                    value.text = str(item[1]).replace("_", " ")
                # add ena units where necessary
                if DTOL_UNITS.get(item[0], ""):
                    if DTOL_UNITS[item[0]].get('ena_unit', ""):
                        unit = ET.SubElement(sample_attribute, 'UNITS')
                        unit.text = DTOL_UNITS[item[0]]['ena_unit']
            except KeyError:
                # pass, item is not supposed to be submitted to ENA
                pass

    ET.dump(tree)
    sample_id = str(sample['_id'])
    samplefile = "bundle_" + str(sample_id) + ".xml"
    tree.write(open(samplefile, 'w'),
               encoding='unicode')


def build_submission_xml(sample_id, hold="", release=False, modify=""):
    # build submission XML
    tree = ET.parse(SRA_SUBMISSION_TEMPLATE)
    root = tree.getroot()
    # from toni's code below
    # set submission attributes
    root.set("submission_date", datetime.utcnow().replace(
        tzinfo=d_utils.simple_utc()).isoformat())

    # set SRA contacts
    contacts = root.find('CONTACTS')

    # set copo sra contacts
    copo_contact = ET.SubElement(contacts, 'CONTACT')
    copo_contact.set("name", sra_settings["sra_broker_contact_name"])
    copo_contact.set("inform_on_error",
                     sra_settings["sra_broker_inform_on_error"])
    copo_contact.set("inform_on_status",
                     sra_settings["sra_broker_inform_on_status"])
    if modify:
        actions = root.find('ACTIONS')
        action = actions.find('ACTION')
        add = action.find("ADD")
        if add != None:
            action.remove(add)
        modify = ET.SubElement(action, 'MODIFY')
    elif release:
        actions = root.find('ACTIONS')
        action = ET.SubElement(actions, 'ACTION')
        release_block = ET.SubElement(action, 'RELEASE')        
    elif hold:
        actions = root.find('ACTIONS')
        action = ET.SubElement(actions, 'ACTION')
        hold_block = ET.SubElement(action, 'HOLD')
        hold_block.set("HoldUntilDate", hold)

    ET.dump(tree)
    submissionfile = "submission_" + str(sample_id) + ".xml"
    tree.write(open(submissionfile, 'w'),
               encoding='unicode')  # overwriting at each run, i don't think we need to keep it


def build_validate_xml(sample_id):
    # TODO do we need this method at all? Its never actually used right?
    # build submission XML
    tree = ET.parse(SRA_SUBMISSION_TEMPLATE)
    root = tree.getroot()
    # set submission attributes
    root.set("submission_date", datetime.utcnow().replace(
        tzinfo=d_utils.simple_utc()).isoformat())
    # set SRA contacts
    contacts = root.find('CONTACTS')
    # set copo sra contacts
    copo_contact = ET.SubElement(contacts, 'CONTACT')
    copo_contact.set("name", sra_settings["sra_broker_contact_name"])
    copo_contact.set("inform_on_error",
                     sra_settings["sra_broker_inform_on_error"])
    copo_contact.set("inform_on_status",
                     sra_settings["sra_broker_inform_on_status"])
    # set user contacts
    sra_map = {"inform_on_error": "SRA Inform On Error",
               "inform_on_status": "SRA Inform On Status"}
    # change ADD to VALIDATE
    root.find('ACTIONS').find('ACTION').clear()
    action = root.find('ACTIONS').find('ACTION')
    ET.SubElement(action, 'VALIDATE')
    ET.dump(tree)
    submissionvalidatefile = "submission_validate_" + str(sample_id) + ".xml"
    tree.write(open(submissionvalidatefile, 'w'),
               encoding='unicode')


def submit_biosample_v2(subfix, sampleobj, collection_id, sample_ids, type="sample", async_send=False):
    submissionfile = "submission_" + str(subfix) + ".xml"
    samplefile = "bundle_" + str(subfix) + ".xml"

    submission_dom = minidom.parse(submissionfile)
    samplefile_dom = minidom.parse(samplefile)
    root = minidom.Document()

    webin = root.createElement('WEBIN')
    root.appendChild(webin)
    submission_set = root.createElement("SUBMISSION_SET")
    webin.appendChild(submission_set)
    submission_set.appendChild(submission_dom.firstChild)

    webin.appendChild(samplefile_dom.firstChild)

    xml_str = root.toprettyxml(indent="\t")
    save_path_file = "filesubmisison_" + str(subfix) + ".xml"

    with open(save_path_file, "w") as f:
        f.write(xml_str)

    cmd = ena_v2_service_sync
    if async_send:
        cmd = ena_v2_service_async

    # curl_cmd = 'curl -m 300 -u ' + user_token + ':' + pass_word \
    #           + ' -F "file=@' \
    #           + save_path_file \
    #           + '" "' + cmd \
    #           + '"'

    session = requests.Session()
    session.auth = (user_token, pass_word)

    try:
        response = session.post(cmd, data={}, files={
                                'file': open(save_path_file)})
        receipt = response.text
        l.log("ENA RECEIPT " + receipt)
        print(receipt)
        if response.status_code == requests.codes.ok:
            # receipt = subprocess.check_output(curl_cmd, shell=True)
            if async_send:
                return handle_async_receipt(receipt, sample_ids, collection_id)
            else:
                tree = ET.fromstring(receipt)
                return handle_submit_receipt(sampleobj, collection_id, tree, type)
        else:
            l.log("General Error " + response.status_code)
            message = 'API call error ' + \
                "Submitting project xml to ENA via cURL. cURL command is: " + cmd
            notify_frontend(data={"profile_id": profile_id}, msg=message, action="error",
                            html_id="dtol_sample_info")
            Submission().reset_dtol_submission_status(collection_id, sample_ids)
    except ET.ParseError as e:
        l.log("Unrecognised response from ENA " + str(e))
        message = " Unrecognised response from ENA - " + str(
            receipt) + " Please try again later, if it persists, contact admin"
        notify_frontend(data={"profile_id": profile_id}, msg=message, action="error",
                        html_id="dtol_sample_info")
        Submission().reset_dtol_submission_status(collection_id, sample_ids)
        return False
    except Exception as e:
        l.exception(e)
        message = 'API call error ' + "Submitting project xml to ENA via cURL. href is: " + cmd
        notify_frontend(data={"profile_id": profile_id}, msg=message, action="error",
                        html_id="dtol_sample_info")
        Submission().reset_dtol_submission_status(collection_id, sample_ids)
        return False
    finally:
        os.remove(submissionfile)
        os.remove(samplefile)
        os.remove(save_path_file)


def handle_async_receipt(receipt, sample_ids, sub_id):
    result = json.loads(receipt)
    submission_id = result["submissionId"]
    href = result["_links"]["poll"]["href"]
    return Submission().update_submission_async(sub_id, href, sample_ids, submission_id)


def poll_asyn_ena_submission():
    submissions = Submission().get_async_submission()

    with requests.Session() as session:
        session.auth = (user_token, pass_word)
        headers = {'Accept': 'application/xml'}
        for submission in submissions:
            for sub in submission["submission"]:
                accessions = ""
                response = session.get(sub["href"], headers=headers)
                if response.status_code == requests.codes.accepted:
                    continue
                elif response.status_code == requests.codes.ok:
                    l.log("ENA RECEIPT " + response.text)
                    try:
                        tree = ET.fromstring(response.text)
                        accessions = handle_submit_receipt(
                            Sample(), submission["_id"], tree)
                    except ET.ParseError as e:
                        l.log("Unrecognised response from ENA " +
                              str(e))
                        message = " Unrecognised response from ENA - " + str(
                            response.content) + " Please try again later, if it persists, contact admin"
                        notify_frontend(data={"profile_id": submission["profile_id"]}, msg=message, action="error",
                                        html_id="dtol_sample_info")
                        continue
                    except Exception as e:
                        l.exception(e)
                        message = 'API call error ' + \
                            "Submitting project xml to ENA via cURL. href is: " + \
                            sub["href"]
                        notify_frontend(data={"profile_id": submission["profile_id"]}, msg=message, action="error",
                                        html_id="dtol_sample_info")
                        continue

                if not accessions:
                    notify_frontend(data={"profile_id": submission["profile_id"]},
                                    msg="Error creating sample: No accessions were found",
                                    action="info",
                                    html_id="dtol_sample_info")
                    continue
                elif accessions["status"] == "ok":
                    msg = "<br>Last sample submitted:  - ENA Submission ID: " + accessions[
                        "submission_accession"]  # + " - Biosample ID: " + accessions["biosample_accession"]
                    notify_frontend(data={"profile_id": submission["profile_id"]}, msg=msg, action="info",
                                    html_id="dtol_sample_info")
                    sample_ids_bson = list(
                        map(lambda id: ObjectId(id), sub["sample_ids"]))
                    specimen_ids = Sample().get_collection_handle().distinct('SPECIMEN_ID',
                                                                             {"_id": {"$in": sample_ids_bson}})
                    specimens = [id for id in specimen_ids if
                                 not submission["dtol_specimen"] or id not in submission["dtol_specimen"]]
                    Submission().update_dtol_specimen_for_bioimage_tosend(
                        submission['_id'], specimens)
                    Submission().dtol_sample_processed(
                        sub_id=submission["_id"], submission_id=sub["id"])
                    
                    # Send an email to user and contact person for the sequencing centre 
                    # conveying that the manifest/samples have been accepted
                    # after the accessions have been added to the sample
                    profile = Profile().get_record(submission["profile_id"])

                    if profile and isinstance(profile, dict):
                        Email().notify_sample_accepted_after_approval(profile=profile)
                    else:
                        l.log("No profiles found to send email for accepted samples")                    

                else:
                    msg = "Submission rejected: <br>" + \
                        accessions["msg"]
                    notify_frontend(data={"profile_id": submission["profile_id"]}, msg=msg, action="error",
                                    html_id="dtol_sample_info")
                    Submission().dtol_sample_rejected(
                        sub_id=submission["_id"], sam_ids=[], submission_id=sub["id"])

                notify_frontend(data={"profile_id": submission["profile_id"]}, msg="", action="hide_sub_spinner",
                                html_id="dtol_sample_info")


def handle_submit_receipt(sampleobj, collection_id, tree, type="sample"):
    success_status = tree.get('success')
    rejected_sample = {}
    if success_status == 'false':
        msg = ""
        error_blocks = tree.find('MESSAGES').findall('ERROR')
        for error in error_blocks:
            msg += error.text + "<br>"
        if not msg:
            msg = "Undefined error"
        status = {"status": "error", "msg": msg}
        # print(status)
        profile_id = ""
        for child in tree.iter():
            if child.tag == 'SAMPLE':
                sample_id = child.get('alias')
                sampleobj.add_rejected_status(status, sample_id)
                sam = Sample().get_record(sample_id)
                if sam:
                    rejected_sample[sam["rack_tube"]] = msg
                    profile_id = sam["profile_id"]

        if rejected_sample:
            profile = Profile().get_record(profile_id)
            if profile:
                Email().notify_sample_rejected_after_approval(project=d_utils.get_profile_type(profile["type"]),
                                                              title=profile["title"],
                                                              description=profile["description"],
                                                              rejected_sample=rejected_sample)

                # print('error')
        l.log("Success False" + str(msg))
        return status
    else:
        # retrieve id and update record
        # return get_biosampleId(receipt, sample_id, collection_id)
        return get_bundle_biosampleId(tree, collection_id, type)


def submit_biosample(subfix, sampleobj, collection_id, type="sample"):
    # register project to the ENA service using XML files previously created

    submissionfile = "submission_" + str(subfix) + ".xml"
    samplefile = "bundle_" + str(subfix) + ".xml"
    curl_cmd = 'curl -m 300 -u "' + user_token + ':' + pass_word \
               + '" -F "SUBMISSION=@' \
               + submissionfile \
               + '" -F "SAMPLE=@' \
               + samplefile \
               + '" "' + ena_service \
               + '"'

    try:
        receipt = subprocess.check_output(curl_cmd, shell=True)

        l.log("ENA RECEIPT " + str(receipt))
        print(receipt)
    except Exception as e:
        l.log("General Error " + str(e))
        message = 'API call error ' + "Submitting project xml to ENA via cURL. cURL command is: " + curl_cmd.replace(
            pass_word, "xxxxxx")
        notify_frontend(data={"profile_id": profile_id}, msg=message, action="error",
                        html_id="dtol_sample_info")
        os.remove(submissionfile)
        os.remove(samplefile)

        Submission().reset_dtol_submission_status(collection_id)
        return False
        # print(message)

    try:
        tree = ET.fromstring(receipt)
    except ET.ParseError as e:
        l.log("Unrecognised response from ENA " + str(e))
        message = " Unrecognised response from ENA - " + str(
            receipt) + " Please try again later, if it persists, contact admin"
        notify_frontend(data={"profile_id": profile_id}, msg=message, action="error",
                        html_id="dtol_sample_info")
        os.remove(submissionfile)
        os.remove(samplefile)
        Submission().reset_dtol_submission_status(collection_id)
        return False

    os.remove(submissionfile)
    os.remove(samplefile)
    success_status = tree.get('success')
    if success_status == 'false':

        msg = ""
        error_blocks = tree.find('MESSAGES').findall('ERROR')
        for error in error_blocks:
            msg += error.text + "<br>"
        if not msg:
            msg = "Undefined error"
        status = {"status": "error", "msg": msg}
        # print(status)
        for child in tree.iter():
            if child.tag == 'SAMPLE':
                sample_id = child.get('alias')
                sampleobj.add_rejected_status(status, sample_id)

        # print('error')
        l.log("Success False" + str(msg))
        return status
    else:
        # retrieve id and update record
        # return get_biosampleId(receipt, sample_id, collection_id)
        tree = ET.fromstring(receipt)
        return get_bundle_biosampleId(tree, collection_id, type)


def get_bundle_biosampleId(tree, collection_id, type="sample"):
    '''parsing ENA sample bundle accessions from receipt and
    storing in sample and submission collection object'''
    # tree = ET.fromstring(receipt)
    submission_accession = tree.find('SUBMISSION').get('accession')
    for child in tree.iter():
        if child.tag == 'SAMPLE':
            sample_id = child.get('alias')
            sra_accession = child.get('accession')
            biosample_accession = child.find('EXT_ID').get('accession')
            if type == "sample":
                Sample().add_accession(biosample_accession,
                                       sra_accession, submission_accession, sample_id)
                Submission().add_accession(biosample_accession, sra_accession, submission_accession, sample_id,
                                           collection_id)
            elif type == "source":
                Source().add_accession(biosample_accession,
                                       sra_accession, submission_accession, sample_id)
                
    accessions = {"submission_accession": submission_accession, "status": "ok"}
    return accessions


def get_studyId(receipt, collection_id):
    # parsing ENA study accessions from receipt and storing in submission collection
    tree = ET.fromstring(receipt)
    project = tree.find('PROJECT')
    bioproject_accession = project.get('accession')
    ext_id = project.find('EXT_ID')
    sra_study_accession = ext_id.get('accession')
    submission = tree.find('SUBMISSION')
    study_accession = submission.get('accession')
    # print(bioproject_accession, sra_study_accession, study_accession) ######
    Submission().add_study_accession(bioproject_accession,
                                     sra_study_accession, study_accession, collection_id)
    accessions = {"bioproject_accession": bioproject_accession, "sra_study_accession": sra_study_accession,
                  "study_accession": study_accession, "status": "ok"}
    return accessions


def create_study(profile_id, collection_id):
    # build study XML
    profile = Profile().get_record(profile_id)
    tree = ET.parse(SRA_PROJECT_TEMPLATE)
    root = tree.getroot()
    # set study attributes
    project = root.find('PROJECT')
    project.set('alias', str(profile['copo_id']))
    project.set('center_name', 'EarlhamInstitute')
    title_block = ET.SubElement(project, 'TITLE')
    title_block.text = profile['title']
    project_description = ET.SubElement(project, 'DESCRIPTION')
    project_description.text = profile['description']
    submission_project = ET.SubElement(project, 'SUBMISSION_PROJECT')
    sequencing_project = ET.SubElement(
        submission_project, 'SEQUENCING_PROJECT')
    ET.dump(tree)
    studyfile = "study_" + profile_id + ".xml"
    # print(studyfile)
    tree.write(open(studyfile, 'w'),
               encoding='unicode')

    submissionfile = "submission_" + profile_id + ".xml"
    build_submission_xml(profile_id, hold=date.today().strftime("%Y-%m-%d"))

    curl_cmd = 'curl -u -m 300 "' + user_token + ':' + pass_word \
               + '" -F "SUBMISSION=@' \
               + submissionfile \
               + '" -F "PROJECT=@' \
               + studyfile \
               + '" "' + ena_service \
               + '"'
    try:
        receipt = subprocess.check_output(curl_cmd, shell=True)
        # print(receipt)
    except Exception as e:
        message = 'API call error ' + "Submitting project xml to ENA via cURL. cURL command is: " + curl_cmd.replace(
            pass_word, "xxxxxx")
        notify_frontend(data={"profile_id": profile_id}, msg=message, action="error",
                        html_id="dtol_sample_info")
        os.remove(submissionfile)
        os.remove(studyfile)
        l.exception(e)
        return False
    # print(receipt)
    try:
        tree = ET.fromstring(receipt)
    except ET.ParseError as e:
        message = " Unrecognised response from ENA - " + str(
            receipt) + " Please try again later, if it persists, contact admin"
        notify_frontend(data={"profile_id": profile_id}, msg=message, action="error",
                        html_id="dtol_sample_info")
        os.remove(submissionfile)
        os.remove(studyfile)
        return False

    os.remove(submissionfile)
    os.remove(studyfile)
    success_status = tree.get('success')
    if success_status == 'false':
        msg = tree.find('MESSAGES').findtext(
            'ERROR', default='Undefined error')
        status = {"status": "error", "msg": msg}
        return status
    else:
        # retrieve id and update record
        accessions = get_studyId(receipt, collection_id)

    if accessions["status"] == "ok":
        msg = "Study submitted " + " - BioProject ID: " + accessions["bioproject_accession"] + " - SRA study ID: " + \
              accessions["sra_study_accession"]
        notify_frontend(data={"profile_id": profile_id}, msg=msg, action="info",
                        html_id="dtol_sample_info")
    else:
        msg = "Submission rejected: " + "<br>" + accessions["msg"]
        notify_frontend(data={"profile_id": profile_id}, msg=msg, action="error",
                        html_id="dtol_sample_info")


def handle_common_ENA_error(error_to_parse, source_id):
    if "The object being added already exists in the submission account with accession" in error_to_parse:
        # catch alias and accession
        pattern_accession = "ERS\d{7}"
        accession = re.search(pattern_accession, error_to_parse).group()
    else:
        return False

    curl_cmd = 'curl -m 300 -u ' + user_token + ':' + pass_word \
               + ' ' + ena_report \
               + accession
    try:
        receipt = subprocess.check_output(curl_cmd, shell=True)
        l.log("ENA RECEIPT REGISTERED SAMPLE for sample " +
              accession + " " + str(receipt))
    except Exception as e:
        l.log("General Error " + str(e))
        return False

    try:
        report = json.loads(receipt.decode('utf8').replace("'", '"'))
    except Exception as e:
        l.log("Unrecognised response from ENA - " + str(e))
        return False

    sra_accession = report[0]["report"].get("id", "")
    biosample_accession = report[0]["report"].get("secondaryId", "")
    submission_accession = "ERA0000000"
    error1 = "submission accession is default to avoid db inconsistencies, handle common ENA error"

    if not any([sra_accession, biosample_accession]):
        return False
    else:
        Source().add_accession(biosample_accession,
                               sra_accession, submission_accession, source_id)
        Source().update_field("error1", error1, source_id)
        return True

    # on hold
    '''build_submission_xml(alias, actionxml="RECEIPT", alias=alias)

    submissionfile = "submission_" + str(alias) + ".xml"
    curl_cmd = 'curl -m 300 -u "' + user_token + ':' + pass_word \
               + '" -F "SUBMISSION=@' \
               + submissionfile \
               + '" "' + ena_service \
               + '"'

  '''


'''def query_public_name_service(sample_list):
    headers = {"api-key": API_KEY}
    url = urljoin(public_name_service, 'tol-ids')  # public-name
    try:
        r = requests.post(url=url, json=sample_list, headers=headers, verify=False)
        if r.status_code == 200:
            resp = json.loads(r.content)
        else:
            # in the case there is a network issue, just return an empty dict
            resp = {}
        return resp
    except Exception as e:
        print("PUBLIC NAME SERVER ERROR: " + str(e))
        Logger().exception(e)
        return {}'''


def log_message(msg, loglvl=Loglvl.INFO, to_frontend=True, profile_id=profile_id):
    if to_frontend:
        if loglvl == Loglvl.ERROR:
            action = "error"
        else:
            action = "info"
        notify_frontend(data={"profile_id": profile_id},
                        msg=msg, action=action, html_id="dtol_sample_info")
    l.log("Submission for profile " +
          profile_id + " : " + msg, level=loglvl)
