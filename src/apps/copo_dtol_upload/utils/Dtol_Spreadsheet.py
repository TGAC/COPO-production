# Created by fshaw at 03/04/2020
import os
import re
import uuid
import pickle
import importlib
from os.path import join, isfile
from pathlib import Path
from shutil import rmtree
from urllib.error import HTTPError
import jsonpath_rw_ext as jp
import pandas
from django.conf import settings
from django.core.files.storage import default_storage
from django_tools.middlewares import ThreadLocal
import common.schemas.utils.data_utils as d_utils
from common.utils.helpers import map_to_dict, get_datetime, notify_frontend
from common.dal.copo_da import  DataFile
from common.dal.profile_da import Profile
from common.dal.sample_da import Sample, Source
from .da import ValidationQueue
from .copo_email import Email
from common.lookup import lookup as lk
from common.lookup.lookup import SRA_SETTINGS
from common.schemas.utils.data_utils import json_to_pytype
from .helpers import query_public_name_service
from common.schema_versions.lookup import dtol_lookups as lookup
# from common.schema_versions import optional_field_dtol_validators as optional_validators, \
#    taxon_validators
# from common.schema_versions import required_field_dtol_validators as required_validators
from common.utils.logger import Logger
from PIL import Image
import numpy as np

Image.MAX_IMAGE_PIXELS = None

l = Logger()

'''
def make_target_sample(sample):
    # need to pop taxon info, and add back into sample_list
    if not "species_list" in sample:
        sample["species_list"] = list()
    out = dict()
    symbiont = sample.pop("SYMBIONT")
    if symbiont.upper() not in ["SYMBIONT", "TARGET"]:
        if symbiont:
            out["SYMBIONT_SOP2dot2"] = symbiont
        symbiont = "TARGET"

    out["SYMBIONT"] = symbiont.upper()
    out["TAXON_ID"] = sample.pop("TAXON_ID")
    out["ORDER_OR_GROUP"] = sample.pop("ORDER_OR_GROUP")
    out["FAMILY"] = sample.pop("FAMILY")
    out["GENUS"] = sample.pop("GENUS")
    out["SCIENTIFIC_NAME"] = sample.pop("SCIENTIFIC_NAME")
    out["INFRASPECIFIC_EPITHET"] = sample.pop("INFRASPECIFIC_EPITHET")
    out["CULTURE_OR_STRAIN_ID"] = sample.pop("CULTURE_OR_STRAIN_ID")
    out["COMMON_NAME"] = sample.pop("COMMON_NAME")
    out["TAXON_REMARKS"] = sample.pop("TAXON_REMARKS")
    sample["species_list"].append(out)

    return sample
    '''

def make_species_list(sample):
    # need to pop taxon info, and add back into sample_list
    if not "species_list" in sample:
        sample["species_list"] = list()
    out = dict()
    symbiont = sample.get("SYMBIONT")
    if symbiont.upper() not in ["SYMBIONT", "TARGET"]:
        if symbiont:
            out["SYMBIONT_SOP2dot2"] = symbiont
        symbiont = "TARGET"

    out["SYMBIONT"] = symbiont.upper()
    out["TAXON_ID"] = sample.get("TAXON_ID", "")
    out["ORDER_OR_GROUP"] = sample.get("ORDER_OR_GROUP", "")
    out["FAMILY"] = sample.get("FAMILY", "")
    out["GENUS"] = sample.get("GENUS", "")
    out["SCIENTIFIC_NAME"] = sample.get("SCIENTIFIC_NAME", "")
    out["INFRASPECIFIC_EPITHET"] = sample.get("INFRASPECIFIC_EPITHET", "")
    out["CULTURE_OR_STRAIN_ID"] = sample.get("CULTURE_OR_STRAIN_ID", "")
    out["COMMON_NAME"] = sample.get("COMMON_NAME", "")
    out["TAXON_REMARKS"] = sample.get("TAXON_REMARKS", "")
    sample["species_list"].append(out)
    return sample


def update_permit_filename(sample, permit_filename_mapping):
    # Update/Set permit filename to a unique name if it exists and it is not equal to "NOT_APPLICABLE"
    # for ERGA manifests
    for col_name in lookup.PERMIT_FILENAME_COLUMN_NAMES:
        if sample.get(col_name, "") and sample.get(col_name, "") not in lookup.BLANK_VALS:
            sample[col_name] = permit_filename_mapping.get(
                sample.get(col_name, ""), "")
    return sample


class DtolSpreadsheet:
    fields = ""
    sra_settings = d_utils.json_to_pytype(
        SRA_SETTINGS, compatibility_mode=False).get("properties", dict())

    def __init__(self, file=None, p_id="", validation_record_id=""):
        self.req = ThreadLocal.get_current_request()
        if p_id == "" and validation_record_id:
            self.vr = ValidationQueue().get_record(validation_record_id)
            p_id = self.vr.get("profile_id", "")
        if file:
            self.file = file
        else:
            # self.sample_data = self.req.session.get("sample_data", "")
            # if self.sample_data == "":
            #    self.sample_data = pickle.loads(self.vr["manifest_data"])
            self.sample_data = pickle.loads(self.vr["manifest_data"])
            self.isupdate = self.req.session.get("isupdate", False)
        self.profile_id = p_id

        sample_images = Path(settings.MEDIA_ROOT) / "sample_images"
        sample_permits = Path(settings.MEDIA_ROOT) / "sample_permits"
        display_images = Path(settings.MEDIA_URL) / "sample_images"
        self.these_images = sample_images
        self.these_permits = sample_permits / self.profile_id
        self.display_images = display_images
        self.data = None
        # self.required_field_validators = list()
        # self.optional_field_validators = list()
        # self.taxon_field_validators = list()
        # self.DtolSpreadsheet = optional_validators
        # self.required_validators = required_validators
        # self.taxon_validators = taxon_validators
        # self.symbiont_list = []
        # self.validator_list = []
        # if a file is passed in, then this is the first time we have seen the spreadsheet,
        # if not then we are looking at creating samples having previously validated

        # get type of manifest
        profile = Profile().get_record(self.profile_id)
        self.type = profile.get("type", "").upper()
        associated_type_lst = profile.get("associated_type", [])
        self.current_schema_version = settings.MANIFEST_VERSION.get(
            self.type, "")
 
        # Get associated type(s) as string separated by '|' symbol
        self.associated_type = " | ".join(associated_type_lst)

        '''
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
        '''

    def loadManifest(self, m_format):

        if self.profile_id is not None:
            notify_frontend(data={"profile_id": self.profile_id}, msg="Loading", action="info",
                            max_ellipsis_length=3, html_id="sample_info")
            try:
                # read excel and convert all to string
                if m_format == "xls":
                    self.data = pandas.read_excel(self.file, keep_default_na=False,
                                                  na_values=lookup.NA_VALS)
                elif m_format == "csv":
                    self.data = pandas.read_csv(self.file, keep_default_na=False,
                                                na_values=lookup.NA_VALS)
                self.data = self.data.loc[:, ~
                                          self.data.columns.str.contains('^Unnamed')]
                '''
                for column in self.allowed_empty:
                    self.data[column] = self.data[column].fillna("")
                '''
                length = len(self.data.index)
                if length > 1000:
                    notify_frontend(data={"profile_id": self.profile_id}, msg=f"No. of lines in the file: {length+1}, Cannot process more than 1000 samples in a single manifest file.",
                                action="error",
                                html_id="sample_info")
                    return False
                self.data.replace(r'^s*$', np.nan, regex=True, inplace=True)                
                self.data = self.data.dropna(how='all')
                self.data.replace(np.nan, '', regex=True, inplace=True)                
                self.data = self.data.apply(lambda x: x.astype(str))
                self.data = self.data.apply(lambda x: x.str.strip())
                self.data.columns = self.data.columns.str.replace(" ", "")
            except Exception as e:
                # if error notify via web socket
                notify_frontend(data={"profile_id": self.profile_id}, msg="Unable to load file. " + str(e),
                                action="error",
                                html_id="sample_info")
                l.exception(e)
                return False
            return True

    """
    def validate(self):
        flag = True
        errors = []
        warnings = []
        self.isupdate = False

        try:
            # get definitive list of mandatory DTOL fields from schema
            s = json_to_pytype(lk.WIZARD_FILES["sample_details"], compatibility_mode=False)
            self.fields = jp.match(
                '$.properties[?(@.specifications[*] == "' + self.type.lower() + '" & @.required=="true" & @.manifest_version[*]== "' + self.current_schema_version + '")].versions[0]',
                s)

            # validate for required fields
            for v in self.required_field_validators:
                errors, warnings, flag, self.isupdate = v(profile_id=self.profile_id, fields=self.fields,
                                                          data=self.data,
                                                          errors=errors, warnings=warnings, flag=flag,
                                                          isupdate=self.isupdate).validate()

            # get list of all DTOL fields from schemas
            self.fields = jp.match(
                '$.properties[?(@.specifications[*] == ' + self.type.lower() + '"& @.manifest_version[*]=="' + self.current_schema_version + '")].versions[0]',
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

                notify_frontend(data={"profile_id": self.profile_id},
                                msg="<h4>" + self.file.name + "</h4><h2>Errors</h2><ol>" + errors + "</ol>",
                                action="error",
                                html_id="sample_info")
                return False



        except Exception as e:
            l.exception(e)
            error_message = str(e).replace("<", "").replace(">", "")
            notify_frontend(data={"profile_id": self.profile_id}, msg="Server Error - " + error_message,
                            action="error",
                            html_id="sample_info")
            raise

        # if we get here we have a valid spreadsheet
        notify_frontend(data={"profile_id": self.profile_id}, msg="Spreadsheet is valid", action="info",
                        html_id="sample_info")
        notify_frontend(data={"profile_id": self.profile_id}, msg="", action="close", html_id="upload_controls")
        notify_frontend(data={"profile_id": self.profile_id}, msg="", action="make_valid", html_id="sample_info")

        return True
    """

    def validate_taxonomy(self):
        ''' check if provided scientific name, TAXON ID,
        family and order are consistent with each other in known taxonomy'''

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
                notify_frontend(data={"profile_id": self.profile_id},
                                msg="<h4>" + self.file.name + "</h4><h2>Errors</h2><ol>" + errors + "</ol>",
                                action="error",
                                html_id="sample_info")
                return False

            else:
                return True

        except HTTPError as e:

            error_message = str(e).replace("<", "").replace(">", "")
            notify_frontend(data={"profile_id": self.profile_id},
                            msg="Service Error - The NCBI Taxonomy service may be down, please try again later.",
                            action="error",
                            html_id="sample_info")
            return False
        except Exception as e:
            l.exception(e)
            error_message = str(e).replace("<", "").replace(">", "")
            notify_frontend(data={"profile_id": self.profile_id}, msg="Server Error - " + error_message,
                            action="error",
                            html_id="sample_info")
            return False

    def check_image_names(self, files):
        # compare list of sample names with specimen ids already uploaded
        samples = self.sample_data
        # get list of specimen_ids in sample
        # specimen_id_column_index = 0
        output = list()
        # for num, col_name in enumerate(samples.columns):
        #    if col_name == "SPECIMEN_ID":
        #        specimen_id_column_index = num
        #        break
        # if os.path.isdir(self.these_images):
        #    rmtree(self.these_images)

        # find distinct specimenId
        specimentIds = samples["SPECIMEN_ID"].drop_duplicates().dropna()

        thumbnail_folder = self.these_images / "thumbnail"
        thumbnail_folder.mkdir(parents=True, exist_ok=True)

        image_path = Path(self.these_images)
        display_path = Path(self.display_images)
        # image_path = Path(settings.MEDIA_ROOT) / "sample_images" / self.profile_id
        existing_images = DataFile().get_datafile_names_by_name_regx(specimentIds)

        for f in files:
            file = files[f]

            # file_path = image_path / file.name
            # write full sized image to large storage
            file_path = image_path / file.name
            thumbnail_path = thumbnail_folder / file.name
            thumbnail_display_path = display_path / "thumbnail" / file.name
            file_display_path = display_path / file.name

            filename = os.path.splitext(file.name)[0].upper()
            # now iterate through samples data to see if there is a match between specimen_id and image name
            found = False
            size = 128, 128
            for specimenId in specimentIds:
                if filename.startswith(specimenId + "-"):
                    found = True
                    if file.name in existing_images:
                        output.append(
                            {"file_name": str(file_display_path), "thumbnail": "", "specimen_id": "Duplicated",
                             "name": ""})
                        break
                    # we have a match
                    output.append({"file_name": str(file_display_path), "thumbnail": str(thumbnail_display_path),
                                   "specimen_id": specimenId, "name": file.name})

                    # logging.info("writing " + str(file_path))
                    with default_storage.open(file_path, 'wb+') as destination:
                        for chunk in file.chunks():
                            destination.write(chunk)

                    im = Image.open(file_path)
                    im.thumbnail(size)
                    im.save(thumbnail_path)
                    # logging.info("written " + str(file_path))
                    break
            if not found:
                output.append({"file_name": str(file_display_path),
                              "specimen_id": "", "name": ""})
        # save to session
        request = ThreadLocal.get_current_request()
        request.session["image_specimen_match"] = output
        notify_frontend(data={"profile_id": self.profile_id}, msg=output, action="make_images_table",
                        html_id="images")
        return output

    def check_permit_names(self, files):
        # compare list of sample names with specimen ids already uploaded
        samples = self.sample_data
        # get list of specimen_ids in sample

        specimen_id_column_index, sampling_permits_required_index, ethics_permits_required_index, nagoya_permits_required_index, sampling_permits_filename_index, ethics_permits_filename_index, nagoya_permits_filename_index = 0, 0, 0, 0, 0, 0, 0

        output = list()
        for num, col_name in enumerate(samples.columns):
            if col_name == "SPECIMEN_ID":
                specimen_id_column_index = num
            elif col_name == "SAMPLING_PERMITS_REQUIRED":
                sampling_permits_required_index = num
            elif col_name == "ETHICS_PERMITS_REQUIRED":
                ethics_permits_required_index = num
            elif col_name == "NAGOYA_PERMITS_REQUIRED":
                nagoya_permits_required_index = num
            elif col_name == "SAMPLING_PERMITS_FILENAME":
                sampling_permits_filename_index = num
            elif col_name == "ETHICS_PERMITS_FILENAME":
                ethics_permits_filename_index = num
            elif col_name == "NAGOYA_PERMITS_FILENAME":
                nagoya_permits_filename_index = num

        if os.path.isdir(self.these_permits):
            rmtree(self.these_permits)
        self.these_permits.mkdir(parents=True)

        write_path = Path(self.these_permits)
        # display_write_path = Path(self.display_images)
        for f in files:
            file = files[f]

            file_path = write_path / file.name
            file_path = Path(settings.MEDIA_ROOT) / \
                "sample_permits" / self.profile_id / file.name
            with default_storage.open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            filename = os.path.splitext(file.name)[0].upper()
            # now iterate through samples data to see if there is a match between specimen_id and permit name
        permit_path = Path(settings.MEDIA_ROOT) / \
            "sample_permits" / self.profile_id
        fail_flag = False
        for num, sample in enumerate(samples.values):

            specimen_id = sample[specimen_id_column_index].upper()

            file_list = [f for f in os.listdir(
                permit_path) if isfile(join(permit_path, f))]
            file_list = set(file_list)  # Remove duplicate filenames

            if sample[ethics_permits_required_index] == "Y":
                found = False
                for filename in file_list:
                    if filename == sample[ethics_permits_filename_index]:
                        p = Path(settings.MEDIA_URL) / \
                            "sample_permits" / self.profile_id / filename
                        output.append(
                            {"file_name": str(p), "specimen_id": specimen_id, "permit_type": "Ethics Permit"})
                        found = True
                        break
                if not found:
                    output.append({
                        "file_name": "None", "specimen_id": "No Ethics Permits found for <strong>" + specimen_id
                                                            + "</strong>",
                        "file_name_expected": sample[ethics_permits_filename_index],
                        "permit_type": "Ethics Permit"
                    })
                    fail_flag = True
            if sample[sampling_permits_required_index] == "Y":
                found = False
                for filename in file_list:
                    if filename == sample[sampling_permits_filename_index]:
                        p = Path(settings.MEDIA_URL) / \
                            "sample_permits" / self.profile_id / filename
                        output.append(
                            {"file_name": str(p), "specimen_id": specimen_id, "permit_type": "Sampling Permit"})
                        found = True
                        break
                if not found:
                    output.append({
                        "file_name": "None", "specimen_id": "No Sampling Permits found for <strong>" + specimen_id
                                                            + "</strong>",
                        "file_name_expected": sample[sampling_permits_filename_index],
                        "permit_type": "Sampling Permit"
                    })
                    fail_flag = True
            if sample[nagoya_permits_required_index] == "Y":
                found = False
                for filename in file_list:
                    if filename == sample[nagoya_permits_filename_index]:
                        p = Path(settings.MEDIA_URL) / \
                            "sample_permits" / self.profile_id / filename
                        output.append(
                            {"file_name": str(p), "specimen_id": specimen_id, "permit_type": "Nagoya Permit"})
                        found = True
                        break
                if not found:
                    output.append({
                        "file_name": "None", "specimen_id": "No Nagoya Permits found for <strong>" + specimen_id
                                                            + "</strong>",
                        "file_name_expected": sample[nagoya_permits_filename_index],
                        "permit_type": "Nagoya Permit"
                    })
                    fail_flag = True
        # save to session
        request = ThreadLocal.get_current_request()
        request.session["permit_specimen_match"] = output
        notify_frontend(data={"profile_id": self.profile_id, "fail_flag": fail_flag}, msg=output,
                        action="make_permits_table",
                        html_id="permits")
        return output

    def save_records(self):
        # create mongo sample objects from info parsed from manifest and saved to session variable
        # sample_data = self.sample_data
        #is_bge = "BGE" in self.associated_type
        binary = pickle.loads(self.vr["manifest_data"])
        try:
            sample_data = pandas.read_excel(binary, keep_default_na=False,
                                            na_values=lookup.NA_VALS)
        except ValueError:
            sample_data = binary
        sample_data = sample_data.loc[:, ~
                                      sample_data.columns.str.contains('^Unnamed')]
        '''
        for column in self.allowed_empty:
            self.data[column] = self.data[column].fillna("")
        '''
        sample_data = sample_data.apply(lambda x: x.astype(str))
        sample_data = sample_data.apply(lambda x: x.str.strip())

        # Remove special characters from column names
        sample_data.columns = [col.strip().replace(" ", "").replace(":", "").replace(".", "").replace("(", "").replace(")", "").replace(
            "/", "").replace(",", "").replace(";", "").replace("'", "").replace('"', "").replace("’", "").replace("“", "").replace("”", "").replace("\n", "") for col in sample_data.columns]
        manifest_id = str(uuid.uuid4())
        request = ThreadLocal.get_current_request()
        image_data = request.session.get("image_specimen_match", [])

        for im in image_data:
            # create matching DataFile object for image is provided
            if im["name"]:
                df = DataFile().get_records_by_fields({"name": im["name"]})
                if (len(df) == 0):
                    fields = {
                        "file_location": im["file_name"], "name": im["name"]}
                    DataFile().save_record({}, **fields)

        public_name_list = list()
        x = json_to_pytype(
            lk.WIZARD_FILES["sample_details"], compatibility_mode=False)
        self.fields = jp.match(
            '$.properties[?(@.specifications[*] == "' + self.type.lower() +
            '"& @.manifest_version[*]=="' +
            self.current_schema_version + '")].versions[0]',
            x)

        # Create a permit filename mapping
        permit_filename_mapping = dict()
        permit_filename_lst = list()

        for col_name in lookup.PERMIT_FILENAME_COLUMN_NAMES:
            if col_name in sample_data.columns:
                permit_filename_lst.extend(
                    sample_data[col_name].unique().tolist())

        # Iterate the list of permit filenames and create a mapping
        for permit_filename in permit_filename_lst:
            if permit_filename.endswith(".pdf"):
                current_date = get_datetime().strftime('%Y%m%d')
                new_permit_filename = permit_filename.replace(
                    '.pdf', "_" + str(current_date) + ".pdf")
                permit_filename_mapping[permit_filename] = new_permit_filename

        sample_data["_id"] = ""
        for index, p in sample_data.iterrows():
            s = dict(p)
            type = ""
            # store manifest version for posterity. If unknown store as 0
            if "asg" in self.type.lower():
                type = "ASG"
            elif "dtolenv" in self.type.lower():
                type = "DTOLENV"
            elif "dtol" in self.type.lower():
                type = "DTOL"
            elif "erga" in self.type.lower():
                type = "ERGA"

            s["manifest_version"] = settings.MANIFEST_VERSION.get(type, "0")
            s["sample_type"] = self.type.lower()
            s["tol_project"] = self.type
            s["associated_tol_project"] = self.associated_type
            s["biosample_accession"] = []
            s["manifest_id"] = manifest_id
            if "erga" in self.type.lower() and s.get("ASSOCIATED_TRADITIONAL_KNOWLEDGE_OR_BIOCULTURAL_PROJECT_ID", str()):
                s["status"] = "private"
            #elif type == "ERGA":
            #    s["status"] = "bge_pending"
            else :
                s["status"] = "pending"
            s["rack_tube"] = s.get("RACK_OR_PLATE_ID", "") + \
                "/" + s["TUBE_OR_WELL_ID"]
            notify_frontend(data={"profile_id": self.profile_id},
                            msg="Creating Sample with ID: " +
                                s.get("TUBE_OR_WELL_ID") +
                            "/" + s["SPECIMEN_ID"],
                            action="info",
                            html_id="sample_info")

            # change fields for symbiont
            if s["SYMBIONT"] == "SYMBIONT":
                s["ORGANISM_PART"] = "WHOLE_ORGANISM"
                for field in self.fields:
                    if field not in lookup.SYMBIONT_FIELDS:
                        target = Sample().get_target_by_field(
                            "rack_tube", s["rack_tube"])
                        if target:
                            s[field] = target[0].get(field, "")
                        else:
                            for p in range(1, len(sample_data)):
                                row = (map_to_dict(
                                    sample_data[0], sample_data[p]))
                                if row.get("RACK_OR_PLATE_ID", "") == s.get("RACK_OR_PLATE_ID", "") and row.get(
                                        "TUBE_OR_WELL_ID", "") == s.get("TUBE_OR_WELL_ID", "") and row.get("SYMBIONT",
                                                                                                           "") == "TARGET":
                                    s[field] = row.get(field, "")
                # if ASG change also sex to not collected
                if s["tol_project"] == "ASG":
                    s["SEX"] = "NOT_COLLECTED"

            # Update permit filename
            s = update_permit_filename(s, permit_filename_mapping)

            s = make_species_list(s)
            sampl = Sample(profile_id=self.profile_id).save_record(
                auto_fields={}, **s)
            Sample().timestamp_dtol_sample_created(sampl.get("_id", ""))
            # update permit filename in the database i.e. set unique filename as the permit filename

            if not sampl["species_list"][0]["SYMBIONT"] or sampl["species_list"][0]["SYMBIONT"] == "TARGET":
                public_name_list.append(
                    {"taxonomyId": int(sampl["species_list"][0]["TAXON_ID"]), "specimenId": sampl["SPECIMEN_ID"],
                     "sample_id": str(sampl["_id"])})

            p["_id"] = sampl["_id"]

            # for im in image_data:
            #    # create matching DataFile object for image is provided
            #    if s["SPECIMEN_ID"] in im["specimen_id"]:
            #        DataFile().insert_sample_id(im["name"], sampl["_id"])

        for im in image_data:
            # create matching DataFile object for image is provided
            samplelist = sample_data.loc[sample_data["SPECIMEN_ID"]
                                         == im["specimen_id"]]["_id"].tolist()
            DataFile().insert_sample_ids(im["name"], samplelist)

        uri = request.build_absolute_uri('/')
        # query public service service a first time now to trigger request for public names that don't exist
        public_names = query_public_name_service(public_name_list)
        for name in public_names:
            if name.get("status", "") == "Rejected":
                Sample().add_rejected_status_for_tolid(
                    name['specimen']["specimenId"])
                continue
            Sample().update_public_name(name)
        profile_id = request.session["profile_id"]
        profile = Profile().get_record(profile_id)

        update_fields = {}
        #update manifest created / updated datetime
        if profile.get("first_manifest_date_created", ''):
            update_fields = {"last_manifest_date_modified": get_datetime()}
        else:
            update_fields = {"first_manifest_date_created": get_datetime()}

        Profile().save_record({}, **update_fields, target_id=profile_id)

        title = profile["title"]
        description = profile["description"]
        Email().notify_manifest_pending_approval(uri + 'copo/dtol_submission/accept_reject_sample/', title=title,
                                                     description=description,
                                                     project=self.type.upper(), is_new=True, profile_id=profile_id)
        
    def update_records(self):
        #is_bge = "BGE" in self.associated_type
        binary = pickle.loads(self.vr["manifest_data"])
        try:
            sample_data = pandas.read_excel(binary, keep_default_na=False,
                                            na_values=lookup.NA_VALS)
        except ValueError:
            sample_data = binary

        request = ThreadLocal.get_current_request()
        public_name_list = list()
        sample_data["_id"] = ""
        need_send_email = False

        # Create a permit filename mapping
        permit_filename_mapping = dict()
        permit_filename_lst = list()

        for col_name in lookup.PERMIT_FILENAME_COLUMN_NAMES:
            if col_name in sample_data.columns:
                permit_filename_lst.extend(
                    sample_data[col_name].unique().tolist())

        # Iterate the list of permit filenames and create a mapping
        for permit_filename in permit_filename_lst:
            if permit_filename.endswith(".pdf"):
                current_date = get_datetime().strftime('%Y%m%d')
                new_permit_filename = permit_filename.replace(
                    '.pdf', "_" + str(current_date) + ".pdf")
                permit_filename_mapping[permit_filename] = new_permit_filename

        for p in range(0, len(sample_data)):
            s = map_to_dict(sample_data.columns, sample_data.iloc[p, :])
            notify_frontend(data={"profile_id": self.profile_id},
                            msg="Updating Sample with ID: " +
                                s["TUBE_OR_WELL_ID"] + "/" + s["SPECIMEN_ID"],
                            action="info",
                            html_id="sample_info")
            rack_tube = s.get("RACK_OR_PLATE_ID", "") + \
                "/" + s["TUBE_OR_WELL_ID"]
            recorded_sample = Sample().get_target_by_field(
                "rack_tube", rack_tube)[0]
            sample_data.at[p, '_id'] = recorded_sample["_id"]
            is_updated = False

            # Update permit filename
            for col_name in lookup.PERMIT_FILENAME_COLUMN_NAMES:
                if s.get(col_name, "") and s.get(col_name, "") not in lookup.BLANK_VALS:
                    s[col_name] = permit_filename_mapping.get(
                        s.get(col_name, ""), "")

            for field in s.keys():
                if s[field] != recorded_sample.get(field, "") and s[field].strip() != recorded_sample["species_list"][
                        0].get(field, ""):
                    if field in lookup.SPECIES_LIST_FIELDS:
                        # update sample and record change in the 'AuditCollection'
                        Sample().update_field("species_list.0." + str(field),
                                           s[field], recorded_sample["_id"])
                        #is_updated = True
                                        
                    # update sample and record change in the 'AuditCollection'
                    Sample().update_field(
                        field, s[field], recorded_sample["_id"])
                    is_updated = True

                    #remove public name if specimen_id / taxon_id changes   
                    if field in ['SPECIMEN_ID','TAXON_ID']:
                        if field == 'SPECIMEN_ID':
                           original_value = recorded_sample.get(field, "")
                           sources = Source().get_all_records_columns(filter_by={field: original_value}, projection={"_id":1, "biosampleAccession":1})
                           if sources:
                             if sources[0].get("biosampleAccession",""):
                               samples_w_same_source = Sample().get_all_records_columns(filter_by={field:original_value}, projection={"_id":1})
                               if not samples_w_same_source:
                                  source = Source().get_collection_handle().find({field: s[field]})
                                  if not source:
                                     Source().get_collection_handle().update_one({"_id": sources[0]["_id"]},{"$set":{field : s[field], "public_name": ""}})
                                  else:
                                     l.log(f"source : {source[0]['_id']} can be deleted")  
                             Sample().update_field('sampleDerivedFrom', '', recorded_sample["_id"])
                        Sample().update_field('public_name', '', recorded_sample["_id"])



            if (recorded_sample["biosampleAccession"] or recorded_sample["status"] == "rejected") and is_updated:
                is_private = "erga" in self.type.lower() and s["ASSOCIATED_TRADITIONAL_KNOWLEDGE_OR_BIOCULTURAL_PROJECT_ID"]
                is_erga = "erga" in self.type.lower()
                Sample().mark_pending(sample_ids = [str(recorded_sample["_id"])], is_erga=is_erga, is_private=is_private)
                need_send_email = True

            uri = request.build_absolute_uri('/')
            # query public service service a first time now to trigger request for public names that don't exist
            public_names = query_public_name_service(public_name_list)
            for name in public_names:
                if name.get("status", "") == "Rejected":
                    Sample().add_rejected_status_for_tolid(
                        name['specimen']["specimenId"])
                    continue
                Sample().update_public_name(name)
            
            profile_id = request.session["profile_id"]
            # Update the associated tol project for each sample in the manifest
            # get associated profile type(s) of manifest
            profile = Profile().get_record(profile_id)
            associated_type_lst = profile.get("associated_type", [])
            # Get associated type(s) as string separated by '|' symbol
            # then, update the associated tol project field in the sample
            associated_type = " | ".join(associated_type_lst)
            
            Sample().update_field("associated_tol_project",
                                    associated_type, recorded_sample["_id"])

        if need_send_email:
            profile = Profile().get_record(profile_id)
            title = profile["title"]
            description = profile["description"]
            Email().notify_manifest_pending_approval(uri + 'copo/dtol_submission/accept_reject_sample/', title=title,
                                                         description=description, 
                                                         project=self.type.upper(), is_new=False,profile_id=profile_id)

     
        #update manifest created / updated datetime
        update_fields = {"last_manifest_date_modified": get_datetime()}
        Profile().save_record({}, **update_fields, target_id=profile_id)

        image_data = request.session.get("image_specimen_match", [])
        for im in image_data:
            if im["name"]:
                samplelist = sample_data.loc[sample_data["SPECIMEN_ID"]
                                             == im["specimen_id"]]["_id"].tolist()
                df = DataFile().get_records_by_fields({"name": im["name"]})
                if (len(df) == 0):
                    fields = {
                        "file_location": im["file_name"], "name": im["name"]}
                    df = DataFile().save_record({}, **fields)
                    DataFile().insert_sample_ids(im["name"], samplelist)
                else:
                    orginallist = df[0]["description"]["attributes"]["attach_samples"]["study_samples"]
                    resultlist = [
                        sam for sam in samplelist if sam not in orginallist]
                    DataFile().insert_sample_ids(im["name"], resultlist)
