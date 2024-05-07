from django.conf import settings
from django_tools.middlewares import ThreadLocal
from common.utils.helpers import get_env, get_datetime, get_not_deleted_flag, json_to_pytype,notify_tagged_seq_status, map_to_dict
from common.schemas.utils.data_utils import simple_utc
from common.dal.copo_da import EnaChecklist
from common.dal.submission_da import Submission
from .da import TaggedSequence
from common.utils.logger import Logger
from bson import ObjectId
from django_tools.middlewares import ThreadLocal
from lxml import etree as ET
from django.http import HttpResponse, JsonResponse
from common.ena_utils.ena_helper import SubmissionHelper
from datetime import datetime
import os
from common.lookup.lookup import SRA_SUBMISSION_TEMPLATE, SRA_PROJECT_TEMPLATE,SRA_SETTINGS
import subprocess
from pathlib import Path
import pandas as pd
import gzip
import shutil
import re
import glob
from common.ena_utils.EnaChecklistHandler import EnaCheckListSpreadsheet
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
import numpy as np


l = Logger()

class EnaTaggedSequence:
    pass_word = get_env('WEBIN_USER_PASSWORD')
    user_token = get_env('WEBIN_USER').split("@")[0]
    ena_service = get_env('ENA_SERVICE')
    headers = {'Accept': 'application/xml' }
    sra_settings = json_to_pytype(SRA_SETTINGS).get("properties", dict())
    submission_helper = None
    submission_path = os.path.join(Path(settings.MEDIA_ROOT), "ena_tagged_seq_files")
    the_submission= None

    '''
    def loadCheckList(self):
        url = "https://www.ebi.ac.uk/ena/submit/report/checklists/xml/*?type=sequence"
        with requests.Session() as session:    
            session.auth = (self.user_token, self.pass_word) 
            try:
                response = session.get(url,headers=self.headers)
                return response.text
            except Exception as e:
                l.exception(e)
                return False            
    

    def _parseCheckList(self, xmlstr):
        xml = xmlstr.encode('utf-8')
        parser = ET.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
        checklist_set = []
        dt = get_datetime()
        root = ET.fromstring(xml, parser=parser)
        checklist_ids = ["ERT000002", "ERT000020"]
        for checklist_elm in root.findall("./CHECKLIST"):
            primary_id = checklist_elm.find("./IDENTIFIERS/PRIMARY_ID").text.strip() 
            if primary_id not in checklist_ids:
                continue
            checklist_ids.remove(primary_id)
            checklist = {}
            checklist['primary_id'] = primary_id
            checklist['name'] = checklist_elm.find("./DESCRIPTOR/NAME").text.strip()
            checklist['description'] = checklist_elm.find("./DESCRIPTOR/DESCRIPTION").text.strip()
            checklist['fields'] = {}
            for field_elm in checklist_elm.findall("./DESCRIPTOR/FIELD_GROUP/FIELD"):
                field = {}
                key = field_elm.find("./LABEL").text.strip()
                field['name'] = field_elm.find("./NAME").text.strip()
                field['description'] = field_elm.find("./DESCRIPTION").text.strip()
                field['mandatory'] = field_elm.find("./MANDATORY").text.strip()
                field['multiplicity'] = field_elm.find("./MULTIPLICITY").text.strip()
                field['type'] = field_elm.find("./FIELD_TYPE")[0].tag
                choice = field_elm.find("./FIELD_TYPE/TEXT_CHOICE_FIELD")
                if choice is not None:
                    field['choice'] = []
                    for choice_elm in choice.findall("./TEXT_VALUE"):
                        field['choice'].append(choice_elm.find("./VALUE").text.strip())

                regex = field_elm.find("./FIELD_TYPE/TEXT_FIELD/REGEX_VALUE")
                if regex is not None:
                    field['regex'] = regex.text.strip()
                checklist['fields'][key] = field

            #add SPECIMEN_ID
            field = {}
            field['name'] = "SPECIMEN_ID"
            field['description'] = "SPECIMENT_ID"
            field['mandatory'] = "mandatory"
            field['multiplicity'] = "single"
            field['type'] = "TEXT_FIELD"
            checklist['fields']["SPECIMEN_ID"] = field

            checklist["modified_date"] =  dt
            checklist["deleted"] = get_not_deleted_flag()
            checklist_set.append(checklist)
            if len(checklist_ids) == 0:
                break
        return checklist_set

    def updateCheckList(self):
        xmlstr = self.loadCheckList()
        checklist_set = self._parseCheckList(xmlstr)
        for checklist in checklist_set:
            TaggedSequenceChecklist().get_collection_handle().find_one_and_update({"primary_id": checklist["primary_id"]},
                                                                            {"$set": checklist},
                                                                            upsert=True)
            df = pd.DataFrame.from_dict(list(checklist["fields"].values()), orient='columns')
            df1 = df
            df.loc[df["mandatory"] == "mandatory", "name"] = df["name"]
            df.loc[df["mandatory"] != "mandatory", "name"] = df["name"] + " (optional)"
            df1 = df.transpose()

            version = settings.MANIFEST_VERSION.get(checklist["primary_id"], str())
            if version:
                version = "_v" + version
            checklist_filename = os.path.join(settings.MANIFEST_PATH, settings.MANIFEST_FILE_NAME.format(checklist["primary_id"], version)  )
            with pd.ExcelWriter(path=checklist_filename, engine='xlsxwriter' ) as writer:  
                sheet_name = checklist["primary_id"] + " " + checklist["name"]
                df1.loc[["name"]].to_excel(writer, sheet_name=sheet_name, index=False, header=False)

                df1.columns = df1.iloc[0] 
                for field in checklist["fields"].values():
                    name = field["name"] if field["mandatory"] == "mandatory" else field["name"] + " (optional)"
                    column_index = df1.columns.get_loc(name)
                    column_length = len(name)
                    writer.sheets[sheet_name].set_column(column_index, column_index, column_length)

                    if "choice" in field:
                        choice = field["choice"]
                        if len(choice) > 0:
                            column_letter = get_column_letter(column_index + 1)
                            cell_start_end = '%s2:%s1048576' % (column_letter, column_letter)
                            writer.sheets[sheet_name].data_validation(cell_start_end,
                                                                    {'validate': 'list',
                                                                    'source': choice})
                            
                sheet_name = 'field_descriptions'           
                df.to_excel(writer, sheet_name=sheet_name)

                for column in df.columns:
                    column_length = max(df[column].astype(str).map(len).max(), len(column))
                    column_index = df.columns.get_loc(column)+1
                    writer.sheets[sheet_name].set_column(column_index, column_index, column_length)



    def get_mandatory_field(self, checklist):
        mandatory_fields = []
        for field in checklist["fields"]:
            if field["mandatory"] == "mandatory":
                mandatory_fields.append(field["label"])
        return mandatory_fields
    '''


    @method_decorator(login_required, name='dispatch')
    def parse_ena_taggedseq_spreadsheet(self, request):
        profile_id = request.session["profile_id"]
        notify_tagged_seq_status(data={"profile_id": profile_id},
                        msg='', action="info",
                        html_id="tagged_seq_info")
        # method called by rest
        file = request.FILES["file"]
        checklist_id = request.POST["checklist_id"]
        name = file.name
        ena = EnaCheckListSpreadsheet(file=file, checklist_id=checklist_id, component="tagged_seq")
        if name.endswith("xlsx") or name.endswith("xls"):
            fmt = 'xls'
        else:
            return HttpResponse(status=415, content="Please make sure your manifest is in xlxs format")

        if ena.loadManifest(fmt):
            l.log("Dtol manifest loaded")
            if ena.validate():
                ena.collect()
                return HttpResponse()
            return HttpResponse(status=400)
        return HttpResponse(status=400)

    @method_decorator(login_required, name='dispatch')
    def save_ena_taggedseq_records(self, request):
        tagged_seq_data = request.session.get("tagged_seq_data")
        profile_id = request.session["profile_id"]
        uid = str(request.user.id)
        checklist = EnaChecklist().get_collection_handle().find_one({"primary_id": request.session["checklist_id"]})
        column_name_mapping = { field["name"].upper() : key  for key, field in checklist["fields"].items()  }
        fields = checklist["fields"]
        if tagged_seq_data:
            for p in range(1, len(tagged_seq_data)):
                # for each row in the manifest
                s = (map_to_dict(tagged_seq_data[0], tagged_seq_data[p]))

                record = {}
                record["profile_id"] = profile_id
                record["updated_by"] = uid
                record["modified_date"] = get_datetime()
                record["deleted"] = get_not_deleted_flag()
                record["checklist_id"] = request.session["checklist_id"]

                for key, value in s.items():
                    header = key
                    header = header.replace(" (optional)", "", -1)
                    upper_key = header.upper()
                    if upper_key in column_name_mapping:
                        record[column_name_mapping[upper_key]] = value

                insert_record = {}
                insert_record["created_by"] = uid
                insert_record["created_date"] = get_datetime()
                insert_record["status"] = "pending"

                TaggedSequence().get_collection_handle().find_one_and_update({"profile_id": profile_id, column_name_mapping["ORGANISM"]:s["Organism"]},
                                                                            {"$set": record, "$setOnInsert": insert_record},
                                                                            upsert=True)
        
        table_data = self.generate_taggedseq_record(profile_id=profile_id, checklist_id=request.session["checklist_id"])
        result = {"table_data": table_data, "component": "taggedseq"}
        return JsonResponse(status=200, data=result)

    def submit_tagged_seq(self, profile_id, checklist_id=None, target_ids=[], target_id=str()):
        if profile_id:
            submissions = Submission().get_records_by_field("profile_id", profile_id)
            if submissions and len(submissions) > 0:
                sub_id = str(submissions[0]["_id"])
                if not target_ids:
                    target_ids = []
                if target_id:
                    target_ids.append(target_id)

                tagged_seq_obj_ids = [ ObjectId(x) for x in target_ids]
                count = TaggedSequence().get_collection_handle().count_documents({"_id": {"$in": tagged_seq_obj_ids},"profile_id": profile_id,  "accession":{"$exists": False}} )
                if count != len(target_ids):
                    return dict(status='error', message="One of the biocoding sequence have been accessed. Cannot submit again!")        

                submission_status = submissions[0].get("tagged_seq_status","complete")
                if submission_status in [ "pending", "complete" ]:
                    TaggedSequence().update_tagged_seq_processing(profile_id=profile_id, tagged_seq_ids=target_ids)
                    Submission().make_tagged_seq_submission_pending(sub_id=str(submissions[0]["_id"]), target_ids=target_ids)
                    return dict(status='success', message="Biocoding manifest submission has been scheduled!")        
                else:
                    return dict(status='error', message="Biocoding manifest submission is processing. Please wait for the current submission to complete before submitting another.")        

        return dict(status='error', message="System error. Biocoding manifest submission has NOT been scheduled! Please contact system administrator.")        

    def _get_submission_xml(self):
        """
        function creates and return submission xml path
        :return:
        """

        # create submission xml
        l.log("Creating submission xml...")

        parser = ET.XMLParser(remove_blank_text=True)
        root = ET.parse(SRA_SUBMISSION_TEMPLATE, parser).getroot()

        # set submission attributes
        root.set("broker_name", self.sra_settings["sra_broker"])
        root.set("center_name", self.sra_settings["sra_center"])
        root.set("submission_date", datetime.utcnow().replace(tzinfo=simple_utc()).isoformat())

        # set SRA contacts
        contacts = root.find('CONTACTS')

        # set copo sra contacts
        copo_contact = ET.SubElement(contacts, 'CONTACT')
        copo_contact.set("name", self.sra_settings["sra_broker_contact_name"])
        copo_contact.set("inform_on_error", self.sra_settings["sra_broker_inform_on_error"])
        copo_contact.set("inform_on_status", self.sra_settings["sra_broker_inform_on_status"])

        # set user contacts
        sra_map = {"inform_on_error": "SRA Inform On Error", "inform_on_status": "SRA Inform On Status"}
        user_contacts = self.submission_helper.get_sra_contacts()
        for k, v in user_contacts.items():
            user_sra_roles = [x for x in sra_map.keys() if sra_map[x].lower() in v]
            if user_sra_roles:
                user_contact = ET.SubElement(contacts, 'CONTACT')
                user_contact.set("name", ' '.join(k[1:]))
                for role in user_sra_roles:
                    user_contact.set(role, k[0])

        # don't release automatically
        # set release action
        release_date = self.submission_helper.get_study_release()

        # only set release info if in the past, instant release should be handled upon submission completion
        '''
        if release_date and release_date["in_the_past"] is False:
            actions = root.find('ACTIONS')
            action = ET.SubElement(actions, 'ACTION')

            action_type = ET.SubElement(action, 'HOLD')
            action_type.set("HoldUntilDate", release_date["release_date"])

        else:
            actions = root.find('ACTIONS')
            action = ET.SubElement(actions, 'ACTION')
            action_type = ET.SubElement(action, 'RELEASE')
        '''
        return self._write_xml_file(xml_object=root, file_name="submission.xml")



    def _get_edit_submission_xml(self,submission_xml_path=str()):
        """
        function creates and return submission xml path
        :return:
        """
        # create submission xml
        l.log("Creating submission xml for edit....")

        parser = ET.XMLParser(remove_blank_text=True)
        root = ET.parse(submission_xml_path, parser).getroot()
        actions = root.find('ACTIONS')
        action = actions.find('ACTION')
        add = action.find("ADD")
        if add != None:
            action.remove(add)
        modify = ET.SubElement(action, 'MODIFY')

        return self._write_xml_file(xml_object=root, file_name="submission_edit.xml")

    def _write_xml_file(self, location=str(), xml_object=None, file_name=str()):
            """
            function writes xml to the specified location or to a default one
            :param location:
            :param xml_object:
            :param file_name:
            :return:
            """

            result = dict(status=True, value='')

            output_location = self.the_submission
            if location:
                output_location = location

            xml_file_path = os.path.join(output_location, file_name)
            tree = ET.ElementTree(xml_object)

            try:
                tree.write(xml_file_path, encoding="utf8", xml_declaration=True, pretty_print=True)
            except Exception as e:
                message = 'Error writing xml file ' + file_name + ": " + str(e)
                l.error(message)
                raise

            message = file_name + ' successfully written to  ' + xml_file_path
            l.log(message)

            result['value'] = xml_file_path

            return result




    def processing_pending_tagged_seq_submission(self):

        # submit tagged seqs
        submissions = Submission().get_tagged_seq_pending_submission()
        #sub_ids = []
        if not submissions:
            return

        for sub in submissions:
            notify_tagged_seq_status(data={"profile_id": sub["profile_id"]},
                    msg="Biomanifest submitting...",
                    action="info",
                    html_id="tagged_seq_info")
            
            self.submission_helper = SubmissionHelper(submission_id=str(sub["_id"]))
            self.the_submission = os.path.join(self.submission_path, sub["profile_id"]) 
            try:
                if not os.path.exists(self.the_submission ):
                    os.makedirs(self.the_submission )

                context = self._get_submission_xml()
                submission_xml_path = context['value']

                context = self._get_edit_submission_xml(submission_xml_path) 
                modify_submission_xml_path = context['value']

 
                # register project
                if not self.submission_helper.get_study_accessions():
                    xml = submission_xml_path
                #do the modifiction
                else:
                    xml = modify_submission_xml_path
                tagged_seqs = TaggedSequence().get_records(sub["tagged_seqs"])
                context = self._register_project(sub["profile_id"], str(sub["_id"]), submission_xml_path=xml)
                if context['status'] is False:
                    self._reject_submission(sub["_id"], tagged_seqs, context.get("message", str()))
                    notify_tagged_seq_status(data={"profile_id": sub["profile_id"]}, msg=context.get("message", str()), action="error", html_id="tagged_seq_info")
                    continue

                project_accession = context['value']
                notify_tagged_seq_status(data={"profile_id": sub["profile_id"]}, msg="Project registered with accession: " + project_accession["accession"], action="info", html_id="tagged_seq_info")

                tagged_seqs_map = dict()
                accessed_tagged_seqs = []
                if tagged_seqs:
                    for tagged_seq in tagged_seqs:
                        if tagged_seq.get("accession", ""):
                            accessed_tagged_seqs.append(tagged_seq)
                            continue
                        checklist_id = tagged_seq["checklist_id"]
                        if checklist_id not in tagged_seqs_map:
                            tagged_seqs_map[checklist_id] = []
                        tagged_seqs_map[checklist_id].append(tagged_seq)
                            
                self._remove_accessed_tagged_seqs(sub["_id"], accessed_tagged_seqs)

                for checklist_id, tagged_seqs_per_checklist in tagged_seqs_map.items():

                    for tagged_seq in tagged_seqs_per_checklist:
                        # validate tagged seqs                    
                        notify_tagged_seq_status(data={"profile_id": sub["profile_id"]}, msg="Validating barcoding sequence......" , action="info", html_id="tagged_seq_info")
                        context = self._validate_tagged_seq(sub["profile_id"], str(sub["_id"]), project_accession["accession"], checklist_id, [tagged_seq])
                        table_data = self.generate_taggedseq_record(profile_id=sub["profile_id"], checklist_id=checklist_id)
                        action="info"
                        message=context.get("success", str())
                        if context.get('error',str()) :
                            self._reject_submission(sub["_id"], [tagged_seq], context.get("error", str()))
                            action="error"
                            message=context.get("error", str())
                        notify_tagged_seq_status(data={"profile_id": sub["profile_id"], "table_data": table_data, "component": "taggedseq"}, msg=message, action=action, html_id="tagged_seq_info")

            except Exception as e:
                l.exception(e)
                message = "Submission processing failed due to exception! Retry again : " + str(e)
                notify_tagged_seq_status(data={"profile_id": sub["profile_id"]}, msg=message , action="error", html_id="tagged_seq_info")
                # reset sample status to pending & remove bundle / bundle samples
                Submission().get_collection_handle().update_one(
                    {"_id": sub["_id"]},
                    {'$set': {'tagged_seq_status': 'pending'}})

    def _remove_accessed_tagged_seqs(self, submission_id, accessed_tagged_seqs):
        dt = get_datetime()
        submission = Submission().get_collection_handle().find_one({"_id": submission_id})
        accessed_tagged_seqs_ids = [x["_id"] for x in accessed_tagged_seqs]
        TaggedSequence().get_collection_handle().update_many({"_id" : {"$in":  accessed_tagged_seqs_ids}}, {'$set': {'status': 'accepted', "modified_date": dt , "error": str()}})
        submission["tagged_seqs"] = [ x for x in submission["tagged_seqs"] if ObjectId(x) not in accessed_tagged_seqs_ids]
        if len(submission["tagged_seqs"]) == 0:
            submission["tagged_seq_status"] = "complete"
        Submission().get_collection_handle().update_one({"_id": submission_id}, {"$set": submission})

    def _add_tagged_seq_accession(self, submission_id, accession, alias, tagged_seqs):
        dt = get_datetime()
        submission = Submission().get_collection_handle().find_one({"_id": submission_id})
        tagged_seq_ids = [x["_id"] for x in tagged_seqs]
        TaggedSequence().get_collection_handle().update_many({"_id" : {"$in":  tagged_seq_ids}}, {'$set': {'status': 'accepted', 'accession': accession, "modified_date": dt , "error": str(), "submission_alias": alias}})
        submission["tagged_seqs"] = [ x for x in submission["tagged_seqs"] if ObjectId(x) not in tagged_seq_ids]
        if len(submission["tagged_seqs"]) == 0:
            submission["tagged_seq_status"] = "complete"
        Submission().get_collection_handle().update_one({"_id": submission_id}, {"$set": {"tagged_seq_status": submission["tagged_seq_status"], "tagged_seqs": submission["tagged_seqs"] }, "$addToSet": {"accessions.tagged_seq_accessions": {"accession": accession, "alias": alias}}})


    def _reject_submission(self, submission_id, tagged_seqs, message=str()):
        dt = get_datetime()
        submission = Submission().get_collection_handle().find_one({"_id": submission_id})
        tagged_seq_object_ids = [x["_id"] for x in tagged_seqs]
        TaggedSequence().get_collection_handle().update_many({"_id" : {"$in":  tagged_seq_object_ids}}, {'$set': {'status': 'pending', 'error': message}})
        submission["tagged_seqs"] = [ x for x in submission["tagged_seqs"] if ObjectId(x) not in tagged_seq_object_ids]
        if len(submission["tagged_seqs"]) == 0:
            submission["tagged_seq_status"] = "complete"
        Submission().get_collection_handle().update_one({"_id": submission_id}, {'$set': {"tagged_seqs" : submission["tagged_seqs"] , 'tagged_seq_status': submission["tagged_seq_status"], "modified_date": dt}})

    def _register_project(self, profile_id, submission_id, submission_xml_path=str()):
        """
        function creates and submits project (study) xml
        :return:
        """

        # create project xml
        log_message = "Registering project..."
        l.log(log_message)
        notify_tagged_seq_status(data={"profile_id": profile_id}, msg=log_message, action="info", html_id="tagged_seq_info")

        parser = ET.XMLParser(remove_blank_text=True)
        root = ET.parse(SRA_PROJECT_TEMPLATE, parser).getroot()

        # set SRA contacts
        project = root.find('PROJECT')

        # set project descriptors
        project.set("alias", submission_id)
        project.set("center_name", self.sra_settings["sra_center"])

        study_attributes = self.submission_helper.get_study_descriptors()

        if study_attributes.get("name", str()):
            ET.SubElement(project, 'NAME').text = study_attributes.get("name", str())

        if study_attributes.get("title", str()):
            ET.SubElement(project, 'TITLE').text = study_attributes.get("title", str())

        if study_attributes.get("description", str()):
            ET.SubElement(project, 'DESCRIPTION').text = study_attributes.get("description", str())

        # set project type - sequencing project
        submission_project = ET.SubElement(project, 'SUBMISSION_PROJECT')
        ET.SubElement(submission_project, 'SEQUENCING_PROJECT')

        # write project xml
        result = self._write_xml_file(xml_object=root, file_name="project.xml")
        if result['status'] is False:
            return result

        project_xml_path = result['value']


        # register project to the ENA service
        curl_cmd = 'curl -u "' + self.user_token + ':' + self.pass_word \
                    + '" -F "SUBMISSION=@' \
                    + submission_xml_path \
                    + '" -F "PROJECT=@' \
                    + project_xml_path \
                    + '" "' + self.ena_service \
                    + '"'

        l.log("Submitting project xml to ENA via CURL. CURL command is: " + curl_cmd.replace(self.pass_word, "xxxxxx"))

        try:
            receipt = subprocess.check_output(curl_cmd, shell=True)
        except Exception as e:
            if settings.DEBUG:
                l.exception(e)
            message = 'API call error ' + "Submitting project xml to ENA via CURL. CURL command is: " + \
                        curl_cmd.replace(
                            self.pass_word, "xxxxxx")
            raise e


        root = ET.fromstring(receipt)

        if root.get('success') == 'false':
            result['status'] = False
            result['message'] = "Couldn't register STUDY due to the following errors: "
            errors = root.findall('.//ERROR')
            if errors:
                error_text = str()
                for e in errors:
                    error_text = error_text + " \n" + e.text

                result['message'] = result['message'] + error_text

            # log error
            l.error(result['message'])

            return result

        # save project accession
        self._write_xml_file(xml_object=root, file_name="project_receipt.xml")
        l.log("Saving project accessions to the database")
        project_accessions = list()
        accession = root.find('PROJECT')
        if accession is None:
            return dict(status=False, value='NO_PROJECT_ACCESSION_FOUND')
        project_accessions.append(
            dict(
                accession=accession.get('accession', default=str()),
                alias=accession.get('alias', default=str()),
                status=accession.get('status', default=str()),
                release_date=accession.get('holdUntilDate', default=str())
            )
        )

        collection_handle = Submission().get_collection_handle()
        doc = collection_handle.find_one({"_id": ObjectId(submission_id)}, {"accessions": 1})

        if doc:
            submission_record = doc
            accessions = submission_record.get("accessions", dict())
            accessions['project'] = project_accessions
            submission_record['accessions'] = accessions

            collection_handle.update_one(
                {"_id": submission_record.pop('_id')},
                {'$set': submission_record})

            # update submission status
            status_message = "Project successfully registered, and accessions saved."
            l.log(status_message)
        return dict(status=True, value=project_accessions[0])


    def _validate_tagged_seq(self, profile_id, submission_id, accession=str(), checklist_id=None, tagged_seqs=list()):
        dt = get_datetime()
        request = ThreadLocal.get_current_request()
        self.the_submission = os.path.join(self.submission_path, profile_id) 
        the_submission_url_path = f"{settings.MEDIA_URL}ena_tagged_seq_files/{profile_id}"
        tsv_file = os.path.join(self.the_submission, f"{submission_id}_{checklist_id}.tsv" )
        manifest_path = os.path.join(self.the_submission, "manifest.txt")

        #tagged_seq_obj_ids = [ObjectId(x) for x in tagged_seq_ids]

        #tagged_seqs = TaggedSequence().execute_query({"_id": {"$in": tagged_seq_obj_ids}, "profile_id": profile_id, "checklist_id": checklist_id})

        #if len(tagged_seqs) != len(tagged_seq_ids):
        #    return dict(status=False, value="Tagged sequence checklist id mismatch")

        checklists = EnaChecklist().execute_query({"primary_id": checklist_id})
        
        if not checklists:
            return dict(status=False, value="Tagged sequence checklist not found")
        checklist = checklists[0]

        fields = checklist["fields"]
        new_column_name = { key: value["name"] for key, value in fields.items() }

        df = pd.DataFrame(tagged_seqs)      

        df.drop(['SPECIMEN_ID', 'TAXON_ID'], axis=1, inplace=True)
        df.drop([x for x in df.columns if x not in fields.keys() or df[x][0].strip()==""], axis=1, inplace=True)
        df.rename(columns=new_column_name, inplace=True) 

        with open(tsv_file, "w") as destination:
            destination.write("Checklist"+"\t" + checklist_id + "\t" + checklist["name"] + "\n")
            df.to_csv(destination, sep="\t", index=False, mode="a")

        with open(tsv_file, 'rb') as f_in:
            with gzip.open(tsv_file + ".gz", "w") as f_out:
                shutil.copyfileobj(f_in, f_out)
        

        manifest_name = submission_id + "_" + str(tagged_seqs[0]["_id"]) + "_" + checklist_id
        manifest_content = "STUDY" + "\t" + accession + "\n"
        manifest_content += "NAME" + "\t" + manifest_name +  "\n"   
        manifest_content += "TAB" + "\t" +  tsv_file + ".gz" +  "\n"

    
        with open(manifest_path, "w") as destination:
            destination.write(manifest_content)

        test = ""
        if "dev" in self.ena_service:
            test = " -test "
        #cli_path = "tools/reposit/ena_cli/webin-cli.jar"
        webin_cmd = "java -Xmx2048m -jar webin-cli.jar -username " + self.user_token + " -password '" + self.pass_word + "'" + test + " -context sequence -manifest " + str(
            manifest_path) + " -validate -ascp"
        l.debug(msg=webin_cmd)
        #print(webin_cmd)
        try:
            l.log(msg='validating tagged sequence submission')
            notify_tagged_seq_status(data={"profile_id": profile_id},
                            msg="Validating barcoding sequence submission",
                            action="info",
                            html_id="tagged_seq_info")
            output = subprocess.check_output(webin_cmd, stderr=subprocess.STDOUT, shell=True)
            output = output.decode("ascii")
        except subprocess.CalledProcessError as cpe:
            return_code = cpe.returncode
            output = cpe.stdout
            output = output.decode("ascii") + " ERROR return code " + str(return_code)
        l.debug(msg=output)
        #print(output)
        #todo decide if keeping or deleting these files
        #report is being stored in webin-cli.report and manifest.txt.report so we can get errors there
        if not "ERROR" in output:
            notify_tagged_seq_status(data={"profile_id": profile_id}, msg="Submitting barcoding sequence......" , action="info", html_id="tagged_seq_info")
            output = self._submit_tagged_seq( profile_id)
            if "ERROR" in output:
                #handle possibility submission is not successfull
                #this may happen for instance if the same assembly has already been submitted, which would not get caught
                #by the validation step
                return {"error": output}
    
            accession = re.search( "ERZ\d*\w" , output).group(0).strip()
            self._add_tagged_seq_accession(ObjectId(submission_id), accession, "webin-sequence-" + manifest_name, tagged_seqs)        
            table_data = self.generate_taggedseq_record(profile_id, checklist_id)
            return {"success": f"Barcoding sequence has been submitted with accession {accession}", "table_data": table_data, "component": "taggedseq" }
        else:
            if return_code == 2:
                with open(self.the_submission / "manifest.txt.report") as report_file:
                    return {"error": (report_file.read())}
            elif return_code == 3:

                directories = sorted(glob.glob(f"{self.the_submission}/sequence/*"), key=os.path.getmtime)
                with open(f"{directories[-1]}/validate/webin-cli.report") as report_file:
                    error = report_file.read()
                
                for file in os.scandir(f"{directories[-1]}/validate"):
                    if file.name != "webin-cli.report":
                        with open(file) as report_file:
                            error = error + f'<br/><a href="{the_submission_url_path}/sequence/{os.path.basename(directories[-1])}/validate/{file.name}">{file.name}</a>'                    
                return {"error": error}
            else:
                return {"error": output}    
    

    def _submit_tagged_seq(self, profile_id):
        manifest_path = os.path.join(self.the_submission ,"manifest.txt")

        test = ""
        if "dev" in self.ena_service:
            test = " -test "
        webin_cmd = "java -Xmx2048m -jar webin-cli.jar -username " + self.user_token + " -password '" + self.pass_word + "'" + test + " -context sequence -manifest " + manifest_path + " -submit -ascp"
        l.debug(msg=webin_cmd)
        # print(webin_cmd)
        # try/except as it turns out this can fail even if validate is successfull
        try:
            l.log(msg="submitting assembly")
            notify_tagged_seq_status(data={"profile_id": profile_id},
                            msg="Submitting barcoding sequence",
                            action="info",
                            html_id="tagged_seq_info")
            output = subprocess.check_output(webin_cmd, stderr=subprocess.STDOUT, shell=True)
            output = output.decode("ascii")           
        except subprocess.CalledProcessError as cpe:
            output = cpe.stdout
            output = output.decode("ascii") + " ERROR return code " + str(cpe.returncode)
        l.debug(msg=output)

        #todo delete files after successfull submission
        #todo decide if keeping manifest.txt and store accession in assembly objec too
        return output


    def generate_taggedseq_record(self, profile_id=str(), checklist_id=str()):
        checklist = EnaChecklist().execute_query({"primary_id" : checklist_id})
        if not checklist:
            return dict(dataSet=[],
                        columns=[],
                        )

        fields = checklist[0]["fields"]
        label = [ x for x in fields.keys() if fields[x]["type"] != "TEXT_AREA_FIELD"]
        data_set = []
        columns = []

        detail_dict = dict(className='summary-details-control detail-hover-message', orderable=False, data=None,
                            title='', defaultContent='', width="5%")
        columns.insert(0, detail_dict)
        columns.append(dict(data="record_id", visible=False))
        columns.append(dict(data="DT_RowId", visible=False))

        columns.extend([dict(data=x, title=fields[x]["name"], defaultContent='') for x in label  ])
        columns.append(dict(data="status", title="STATUS", defaultContent=''))
        columns.append(dict(data="accession", title="ACCESSION", defaultContent='', className="ena-accession"))
        columns.append(dict(data="error", title="ERROR", defaultContent=''))


        tag_sequences = TaggedSequence(profile_id=profile_id).execute_query({"checklist_id" : checklist_id, "profile_id": profile_id, 'deleted': get_not_deleted_flag()})

        if len(tag_sequences):
            df = pd.DataFrame(tag_sequences)
            #df['s_n'] = df.index

            df['record_id'] = df._id.astype(str)
            df["DT_RowId"] = df.record_id
            df.DT_RowId = 'row_' + df.DT_RowId
            df = df.drop('_id', axis='columns')
            df.replace(np.nan, '', regex=True, inplace=True)

            for name in df.columns:
                if name in ["record_id", "DT_RowId", "status", "accession", "error"]:
                    continue
                if name not in label:
                    df.drop(name, axis='columns', inplace=True)

            data_set = df.to_dict('records')

        return_dict = dict(dataSet=data_set,
                        columns=columns,
                        )

        return return_dict