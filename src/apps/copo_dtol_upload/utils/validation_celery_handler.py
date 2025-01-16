

from common.dal.copo_da import  APIValidationReport
from common.dal.profile_da import Profile
from common.dal.sample_da import Sample
from .da import ValidationQueue
from .tol_validators import optional_field_dtol_validators as optional_validators, taxon_validators
from .tol_validators import required_field_dtol_validators as required_validators
from .tol_validators.validation_messages import MESSAGES as validation_msg
from common.validators.validator import Validator
import pandas
import inspect
import pickle
import math
from common.schema_versions.lookup import dtol_lookups as lookup
from common.utils.helpers import notify_frontend
from urllib.error import HTTPError
from common.schemas.utils.data_utils import get_compliant_fields, json_to_pytype
from common.lookup import lookup as lk
import jsonpath_rw_ext as jp
from common.utils.helpers import map_to_dict
from common.utils.logger import Logger
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q
from io import BytesIO
import re
import os

class ProcessValidationQueue:

    def __init__(self):
        self.required_field_validators = list()
        self.optional_field_validators = list()
        self.taxon_field_validators = list()
        self.optional_validators = optional_validators
        self.required_validators = required_validators
        self.taxon_validators = taxon_validators
        self.symbiont_list = []
        self.validator_list = []
        self.sample_data = None
        self.profile_id = None
        self.fields = []
        self.file_name = None
        self.data = None
        self.isupdate = None
        self.type = None
        self.current_schema_version = None
        self.public_name_list = list()

    def process_validation_queue(self):
        """This method is called from celery and looks in the validationqueue collection in mongo for manifests which need validation
        once found, these are processed here"""

        # create list of required validators
        required = dict(globals().items())["required_validators"]
        for element_name in dir(required):
            element = getattr(required, element_name)
            if inspect.isclass(element) and issubclass(element, Validator) and not element.__name__ == "Validator":
                self.required_field_validators.append(element)
        # create list of optional validators
        optional = dict(globals().items())["optional_validators"]
        for element_name in dir(optional):
            element = getattr(optional, element_name)
            if inspect.isclass(element) and issubclass(element, Validator) and not element.__name__ == "Validator":
                self.optional_field_validators.append(element)
        # create list of taxon validators
        optional = dict(globals().items())["taxon_validators"]
        for element_name in dir(optional):
            element = getattr(optional, element_name)
            if inspect.isclass(element) and issubclass(element, Validator) and not element.__name__ == "Validator":
                self.taxon_field_validators.append(element)

        # get all manifests queued for validation
        queued_manifests = ValidationQueue().get_queued_manifests()

        for qm in queued_manifests:
            if not qm["report_id"] == "":
                APIValidationReport().setRunning(qm["report_id"])

            #self.sample_data = pickle.loads(qm["manifest_data"])
            bytesstring = BytesIO(qm["manifest_data"])
            self.data = pandas.read_pickle(bytesstring)
            self.profile_id = qm["profile_id"]
            self.file_name = qm["file_name"]
            self.user_id = qm["user_id"]
            t = Profile().get_type(self.profile_id)

            if "ASG" in t:
                self.type = "ASG"
            elif "DTOL_EI" in t:
                self.type = "DTOL_EI"
            elif "ERGA" in t:
                self.type = "ERGA"
            else:
                self.type = "DTOL"
            self.current_schema_version = settings.MANIFEST_VERSION.get(self.type, "")
            """
            try:
                self.data = pandas.read_excel(self.sample_data, keep_default_na=False, na_values=lookup.NA_VALS)
                #self.data = self.data.dropna(how='all')
            except:
                notify_frontend(data={"profile_id": self.profile_id}, msg="Failed to load manifest", action="info",
                                html_id="sample_info")
                return False
            """
            notify_frontend(data={"profile_id": self.profile_id}, msg="Loading", action="info",
                            max_ellipsis_length=3, html_id="sample_info")

            try:
                #self.data = self.data.loc[:, ~self.data.columns.str.contains('^Unnamed')]
                '''
                for column in self.allowed_empty:
                    self.data[column] = self.data[column].fillna("")
                '''
                #self.data = self.data.apply(lambda x: x.astype(str))
                #self.data = self.data.apply(lambda x: x.str.strip())
                
                # Remove special characters from column names
                self.data.columns = [col.strip().replace(" ", "").replace(":", "").replace(".", "").replace("(", "").replace(")", "").replace(
                    "/", "").replace(",", "").replace(";", "").replace("'", "").replace('"', "").replace("’", "").replace("“", "").replace("”", "").replace("\n", "") for col in self.data.columns]

                # validate for an empty manifest/excel file
                if len(self.data.index) == 0 or len(self.data.columns) == 0:
                    msg = "<h4>" + self.file_name + "</h4><h2>Errors</h2><ol><li>Manifest uploaded is empty</li></ol>"
                    notify_frontend(data={"profile_id": self.profile_id},
                                    msg=msg,
                                    action="error",
                                    html_id="sample_info")
                    Logger().error(msg)
                    return False
            except Exception as e:
                Logger().exception(e)
                # if error notify via web socket
                notify_frontend(data={"profile_id": self.profile_id}, msg="Unable to load file. " + str(e),
                                action="info",
                                html_id="sample_info")
                Logger().exception(e)
                return False

            """
            TAXONOMY VALIDATION
            check if provided scientific name, TAXON ID,
            family and order are consistent with each other in known taxonomy
            """

            errors = []
            warnings = []
            flag = True
            try:
                # validate for optional dtol fields
                for v in self.taxon_field_validators:
                    errors, warnings, flag = v(profile_id=self.profile_id, fields=self.fields, data=self.data,
                                               errors=errors, warnings=warnings, flag=flag).validate()

                # send warnings
                if warnings:
                    notify_frontend(data={"profile_id": self.profile_id},
                                    msg="<h2>Warnings</h2>" + "<br><br>".join(warnings),
                                    action="warning",
                                    html_id="warning_info")

                if not flag:
                    errors = list(map(lambda x: "<li>" + x + "</li>", errors))
                    errors = "".join(errors)
                    msg = "<h4>" + self.file_name + "</h4><h2>Errors</h2><ol>" + errors + "</ol>"
                    notify_frontend(data={"profile_id": self.profile_id},
                                    msg=msg,
                                    action="error",
                                    html_id="sample_info")
                    ValidationQueue().set_taxon_validation_error(qm["_id"], err=msg)
                    if not qm["report_id"] == "":
                        APIValidationReport().setFailed(qm["report_id"], msg=msg)
                    return False
                else:
                    # set validation queue taxon flag to complete
                    ValidationQueue().set_taxon_validation_complete(qm["_id"])

            except HTTPError as e:
                Logger().exception(e)
                error_message = str(e).replace("<", "").replace(">", "")
                msg = "Service Error - The NCBI Taxonomy service may be down, please try again later."
                notify_frontend(data={"profile_id": self.profile_id},
                                msg=msg,
                                action="error",
                                html_id="sample_info")
                ValidationQueue().set_taxon_validation_error(qm["_id"], err=msg)
                return False
            except Exception as e:
                Logger().exception(e)
                error_message = str(e).replace("<", "").replace(">", "")
                msg = "Server Error - " + error_message
                notify_frontend(data={"profile_id": self.profile_id}, msg=msg,
                                action="error",
                                html_id="sample_info")
                ValidationQueue().set_taxon_validation_error(qm["_id"], err=msg)
                Logger().exception(e)
                if not qm["report_id"] == "":
                    APIValidationReport().setFailed(qm["report_id"], msg=msg)
                return False

            """
            SCHEMA VALIDATION
            checks to make sure the manifest conforms to the TOL SOPs
            """
            flag = True
            errors = []
            warnings = []
            self.isupdate = False

            try:
                # get definitive list of mandatory DTOL fields from schema
                s = json_to_pytype(lk.WIZARD_FILES["sample_details"], compatibility_mode=False)
                
                # Required fields' validation
                self.fields = jp.match(
                    '$.properties[?(@.specifications[*] == "' + self.type.lower() + '" & @.required=="true" & @.manifest_version[*]== "' + self.current_schema_version + '")].versions[0]',
                    s)

                # validate for required fields
                for v in self.required_field_validators:
                    errors, warnings, flag, self.isupdate = v(profile_id=self.profile_id, fields=self.fields,
                                                              data=self.data,
                                                              errors=errors, warnings=warnings, flag=flag,
                                                              isupdate=self.isupdate).validate()
                    
                    if self.isupdate:
                        ValidationQueue().set_update_flag(qm["_id"])

                # All fields' validation
                # get list of all DTOL fields from schemas
                self.fields = jp.match(
                    '$.properties[?(@.specifications[*] == "' + self.type.lower() + '"& @.manifest_version[*]=="' + self.current_schema_version + '")].versions[0]',
                    s)

                # validate for optional dtol fields
                for v in self.optional_field_validators:
                    errors, warnings, flag = v(profile_id=self.profile_id, fields=self.fields, data=self.data,
                                               errors=errors, warnings=warnings, flag=flag).validate()

                # send warnings
                if warnings:
                    notify_frontend(data={"profile_id": self.profile_id},
                                    msg="<h2>Warnings</h2>" + "<br><br>".join(warnings),
                                    action="warning",
                                    html_id="warning_info2")
                # if flag is false, compile list of errors
                if not flag:
                    errors = list(map(lambda x: "<li>" + x + "</li>", errors))
                    errors = "".join(errors)
                    msg = "<h4>" + self.file_name + "</h4><h2>Errors</h2><ol>" + errors + "</ol>"
                    notify_frontend(data={"profile_id": self.profile_id},
                                    msg=msg,
                                    action="error",
                                    html_id="sample_info")
                    ValidationQueue().set_schema_validation_error(qm["_id"], err=msg)
                    if not qm["report_id"] == "":
                        APIValidationReport().setFailed(qm["report_id"], msg=msg)
                    return False

            except Exception as e:
                Logger().exception(e)
                error_message = str(e).replace("<", "").replace(">", "")
                msg = "Server Error - " + error_message,
                notify_frontend(data={"profile_id": self.profile_id}, msg=msg,
                                action="error",
                                html_id="sample_info")
                ValidationQueue().set_schema_validation_error(qm["_id"], err=msg)
                Logger().exception(e)
                if not qm["report_id"] == "":
                    APIValidationReport().setFailed(qm["report_id"], msg=msg)
                return False

            # if we get here we have a valid spreadsheet
            # so set validation queue taxon flag to complete

            # Copy all values from the the created column, "NEW_PURPOSE_OF_SPECIMEN" column 
            # back into the "PURPOSE_OF_SPECIMEN" column if that column exists
            if 'NEW_PURPOSE_OF_SPECIMEN' in self.data.columns:
                self.data["PURPOSE_OF_SPECIMEN"] = self.data["NEW_PURPOSE_OF_SPECIMEN"]
                # Delete the created column
                self.data.drop(columns=["NEW_PURPOSE_OF_SPECIMEN"], inplace=True)

            # Update data in database    
            ValidationQueue().update_manifest_data(qm["_id"], pickle.dumps(self.data))
            ValidationQueue().set_schema_validation_complete(qm["_id"])

            if not qm["report_id"] == "":
                APIValidationReport().setComplete(qm["report_id"])
            if self.isupdate:
                self.make_update_notifications(qm)
            else:
                self.make_table(qm)

    def make_table(self, qm):
        permits_required = False
        notify_frontend(data={"profile_id": self.profile_id}, msg="Spreadsheet is valid", action="info",
                        max_ellipsis_length=0, html_id="sample_info")
        notify_frontend(data={"profile_id": self.profile_id}, msg="", action="close", html_id="upload_controls")
        notify_frontend(data={"profile_id": self.profile_id}, msg="", action="make_valid", html_id="sample_info")

        # create table data to show to the frontend from parsed manifest
        sample_data = []
        headers = list()
        for col in list(self.data.columns):
            headers.append(col)
        sample_data.append(headers)
        if "Y" in list(self.data.get("SAMPLING_PERMITS_REQUIRED", "")) + list(
                self.data.get("ETHICS_PERMITS_REQUIRED", "")) + list(self.data.get("NAGOYA_PERMITS_REQUIRED", "")):
            permits_required = True
        for index, row in self.data.iterrows():
            r = list(row)
            for idx, x in enumerate(r):
                if x is math.nan:
                    r[idx] = ""
            sample_data.append(r)

        notify_frontend(data={"profile_id": self.profile_id}, msg=str(qm["_id"]), action="store_validation_record_id",
                        html_id="")
        notify_frontend(data={"profile_id": self.profile_id, "permits_required": permits_required}, msg=sample_data,
                        action="make_table",
                        html_id="sample_table")

    def make_update_notifications(self, qm):
        is_manager = False
        group = ""
        profile = Profile().get_record(self.profile_id)
        if profile:
            group = f"{profile.get('type','').lower()}_sample_managers"

        user = User.objects.get(pk=self.user_id)       
        if user and group:
            is_manager = user.groups.filter(name=group).exists()
        sample_data = self.data
        #sample_data = self.data
        updates = {}
        permits_required = False
        for p in range(0, len(sample_data)):
            s = map_to_dict(self.data.columns, self.data.iloc[p, :])
            rack_tube = s.get("RACK_OR_PLATE_ID", "") + "/" + s["TUBE_OR_WELL_ID"]
            if s["SYMBIONT"].upper() == "SYMBIONT":
                # this requires different logic to discriminate between symbionts
                return False
            exsam = Sample().get_target_by_field("rack_tube", rack_tube)

            # Check if ‘RACK_OR_PLATE_ID’ or ‘TUBE_OR_WELL_ID’ has been changed to 
            # prevent an assertion error and an update lag if the assertion below is executed
            if len(exsam) != 1:
                field, value =  (
                    ("RACK_OR_PLATE_ID", s["RACK_OR_PLATE_ID"])
                    if "RACK_OR_PLATE_ID" in s
                    else ("TUBE_OR_WELL_ID", s["TUBE_OR_WELL_ID"])
                )
                msg = validation_msg["validation_msg_error_new_sample_detected_in_existing_manifest"] % (field, value)
                notify_frontend(data={"profile_id": self.profile_id}, msg=msg, action="error",
                                html_id="sample_info")
                return False
            
            exsam = exsam[0]
            updates[rack_tube] = {}
            is_not_approved = exsam.get("biosampleAccession", "") == ""
            compliant_fields = get_compliant_fields(component="sample", project=self.type.lower())
            

            # Always ask user to upload permit if it is required
            #if any(s.get(x,"") == "Y" for x in
            #        lookup.PERMIT_REQUIRED_COLUMN_NAMES):
            #    permits_required = True

            for field in s.keys():
                if s[field].strip() != exsam.get(field, "") and s[field].strip() != exsam["species_list"][0].get(field,
                                                                                                                 ""):
                    if is_manager or is_not_approved or field not in compliant_fields:
                        #updates[rack_tube][field] = {}
                        if field in lookup.SPECIES_LIST_FIELDS:
                            updates[rack_tube][field] = {}
                            updates[rack_tube][field]["old_value"] = exsam["species_list"][0][field]
                            updates[rack_tube][field]["new_value"] = s[field]

                        if field.endswith("_PERMITS_FILENAME"):
                            current_name = s[field].strip() 
                            if current_name:
                                file_name, file_ext = os.path.splitext(current_name)
                                if re.search(rf"{file_name}_\d{{8}}{file_ext}", exsam.get(field,"")): 
                                    continue
                                #ask user to upload permit if the file name has been changed
                                elif any(s.get(x,"") == "Y" for x in lookup.PERMIT_REQUIRED_COLUMN_NAMES):
                                    permits_required = True
                        updates[rack_tube][field] = {}        
                        updates[rack_tube][field]["old_value"] = exsam.get(field,"")  #to cater for the case where the field not exist in the old maniest
                        updates[rack_tube][field]["new_value"] = s[field]
                    else:
                        msg = validation_msg["validation_msg_error_updating_compliance_field"] % (field, profile.get("type","").upper())
                        notify_frontend(data={"profile_id": self.profile_id}, msg=msg, action="error",
                                        html_id="sample_info")
                        return False
        # show upcoming updates here
        msg = "<ul>"
        for sample in updates:
            if updates[sample]:
                msg += "<li>Updating sample <strong>" + sample + "</strong>: <ul>"
                for field in updates[sample]:
                    msg += "<li><strong> " + field + "</strong> from " + updates[sample][field]["old_value"] + " " \
                                                                                                            "to <strong>" + \
                        updates[sample][field]["new_value"] + "</strong></li>"
                msg += "</li></ul>"
        msg += "</ul>"

        out_data = []
        headers = list()
        for col in list(self.data.columns):
            headers.append(col)
        out_data.append(headers)
        for index, row in self.data.iterrows():
            r = list(row)
            for idx, x in enumerate(r):
                if x is math.nan:
                    r[idx] = ""
            out_data.append(r)

        notify_frontend(data={"profile_id": self.profile_id}, msg=str(qm["_id"]),
                        action="store_validation_record_id",
                        html_id="")
        notify_frontend(data={"profile_id": self.profile_id}, msg=msg, action="warning",
                        html_id="warning_info3")
        notify_frontend(data={"profile_id": self.profile_id, "permits_required": permits_required}, msg=out_data, action="make_update",
                        html_id="sample_table")

        #if permits_required:
        #    notify_frontend(data={"profile_id": self.profile_id}, msg="", action="require_permits",
        #                    html_id="")
