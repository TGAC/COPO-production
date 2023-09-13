__author__ = 'etuka'
__date__ = '13 May 2016'

import json
from bson import ObjectId
from django.contrib.auth.models import User
import common.lookup.lookup as lkup
from src.apps.copo_read_submission.utils import ena_read
from src.apps.copo_assembly_submission.utils import EnaAssembly
from src.apps.copo_seq_annotation_submission.utils import EnaAnnotation
from src.apps.copo_accession.utils import Accession as accession
from src.apps.copo_file.utils import CopoFiles as copo_file
from common.utils import html_tags_utils as htags
from common.utils.copo_lookup_service import COPOLookup
from common.dal.copo_da import Profile, Source, Person, Sample, Submission, DataFile, DAComponent, \
    CGCore, MetadataTemplate, Assembly, Sequnece_annotation, TaggedSequence
from common.schemas.utils import data_utils
from common.utils import helpers
from common.utils.logger import Logger
from common.dal.mongo_util import cursor_to_list_str 
from src.apps.copo_barcoding_submission.utils.EnaTaggedSequence import EnaTaggedSequence
from common.s3.s3Connection import S3Connection as s3



class BrokerDA:
    def __init__(self, **kwargs):
        self.param_dict = kwargs
        self.context = self.param_dict.get("context", dict())
        self.component = self.param_dict.get("component", str())
        self.visualize = self.param_dict.get("visualize", str())
        self.profile_id = self.param_dict.get("profile_id", str())
        self.auto_fields = self.param_dict.get("auto_fields", dict())
        self.request_dict = self.param_dict.get("request_dict", dict())

        if self.auto_fields and isinstance(self.auto_fields, str):
            self.auto_fields = json.loads(self.auto_fields)

        self.broker_visuals = BrokerVisuals(**kwargs)
        self.da_object = DAComponent(self.profile_id, self.component)

        da_dict = dict(
            #publication=Publication,
            person=Person,
            sample=Sample,
            source=Source,
            profile=Profile,
            datafile=DataFile,
            submission=Submission,
            #annotation=Annotation,
            cgcore=CGCore,
            metadata_template=MetadataTemplate,
            #repository=Repository
            seqannotation=Sequnece_annotation,
            assembly=Assembly,
            files=s3,
            taggedseq=TaggedSequence            
        )

        if self.component in da_dict:
            self.da_object = da_dict[self.component](self.profile_id)

    def set_extra_params(self, extra_param):
        for k, v in extra_param.items():
            self.param_dict[k] = v

    def do_form_control_schemas(self):
        """
        function returns object type control schemas used in building form controls
        :return:
        """
        return []

        copo_schemas = dict()
        for k, v in data_utils.object_type_control_map().items():
            copo_schemas[k] = data_utils.get_copo_schema(v)

        self.context["copo_schemas"] = copo_schemas
        return self.context

    def do_save_edit(self):
        kwargs = dict()
        kwargs["target_id"] = self.param_dict.get("target_id", str())

        # set report parameter
        status = "success"  # 'success', 'warning', 'info', 'danger' - modelled after bootstrap alert classes
        action_type = "add"
        action_message = "creating"

        report_metadata = dict()

        if self.param_dict.get("target_id", str()):
            action_type = "edit"
            action_message = "updating"

        # validate record
        validation_result = self.da_object.validate_record(auto_fields=self.auto_fields, **kwargs)

        if validation_result.get("status", True) is False:
            report_metadata["status"] = "error"
            report_metadata["message"] = validation_result.get("message",
                                                               "There was a problem " + action_message
                                                               + " the " + self.component + " record!")
            self.context["action_feedback"] = report_metadata
            return self.context

        # check the title is not duplicated for profiles
        # initialise to empty to keep a single check for all types
        existingprofile = []
        if isinstance(self.da_object, Profile):
            existingprofile = self.da_object.get_by_title(self.auto_fields["copo.profile.title"])

        if not existingprofile:
            # check users are not changing the type of an existing profile
            if action_type == "edit":
                targetprofiletype = self.da_object.get_record(kwargs["target_id"]).get("type", "")
                if targetprofiletype != self.auto_fields["copo.profile.type"]:
                    record_object = {}
                    status = "forbidden action"
                else:
                    # edit record
                    record_object = self.da_object.save_record(auto_fields=self.auto_fields, **kwargs)
            else:
                # save record
                record_object = self.da_object.save_record(auto_fields=self.auto_fields, **kwargs)
        else:
            record_object = {}
            status = "duplicated"

        if not record_object and status not in ["duplicated", "forbidden action"]:
            status = "danger"

        if action_type == "add" and status == "success":
            if "profile" in self.component:
                report_metadata[
                    "message"] = "New " + self.component + " record created! <br><br>Web page will refresh in 3 seconds."
            else:
                report_metadata["message"] = "New " + self.component + " record created!"
        elif action_type == "add" and status == "duplicated":
            report_metadata["message"] = "Record already exist with title, " + self.auto_fields["copo.profile.title"]
            status = "error"
        elif action_type == "add" and status != "success":
            report_metadata["message"] = "There was a problem creating the " + self.component + " record!"
        elif action_type == "edit" and status == "success":
            report_metadata["message"] = "Record updated! <br><br>Web page will refresh in 3 seconds."
        elif action_type == "edit" and status == "duplicated":
            targetid = kwargs["target_id"]
            targetprofiletitle = self.da_object.get_record(targetid).get("title", "")
            user_id = helpers.get_user_id()
            existing_profiles_ids = Profile().get_collection_handle().find(
                {"user_id": user_id, "title": self.auto_fields["copo.profile.title"]}, {"_id": 1})

            # Get a list of profile IDs that have the same profile title as the profile record to be edited
            lst_of_profile_ids = cursor_to_list_str(existing_profiles_ids)

            # Get target profile type
            targetprofiletype = self.da_object.get_record(kwargs["target_id"]).get("type", "")

            if targetprofiletype != self.auto_fields["copo.profile.type"]:
                # Profile type cannot be changed
                report_metadata["message"] = "Forbidden action, it is not possible to modify the profile type"
                status = "error"
            elif targetprofiletitle == self.auto_fields["copo.profile.title"] and targetid == lst_of_profile_ids[0].get(
                    "_id", "") and len(lst_of_profile_ids) == 1:
                # if the target ID  matches the ID in the list and the targeted profile title matches the title
                # in the editable field then, proceed with the 'edit' task
                record_object = self.da_object.save_record(auto_fields=self.auto_fields, **kwargs)
                report_metadata["message"] = "Record updated! <br><br>Web page will refresh in 3 seconds."
                status = "success"
            elif targetprofiletitle != self.auto_fields["copo.profile.title"] and targetid != lst_of_profile_ids[0].get(
                    "_id", "") and len(lst_of_profile_ids) == 1:
                # if the target ID  does not match the ID in the list and the targeted profile title is not the
                # same as the title in the editable field then, the title already exists
                report_metadata["message"] = "Record already exist with title, " + self.auto_fields["copo.profile.title"]
                status = "error"
            else:
                report_metadata["message"] = "Record already exist with title, " + self.auto_fields["copo.profile.title"]
                status = "error"
        elif action_type == "edit" and status == "forbidden action":
            report_metadata["message"] = "Forbidden action, it is not possible to modify the profile type"
            status = "error"
        elif action_type == "edit" and status != "success":
            report_metadata["message"] = "There was a problem updating the " + self.component + " record!"

        report_metadata["status"] = status
        self.context["action_feedback"] = report_metadata

        # process visualisation context,

        # set extra parameters which will be passed along to the visualize object
        self.broker_visuals.set_extra_params(
            dict(record_object=record_object, data_source=self.param_dict.get("data_source", str())))

        # build dictionary of executable tasks/functions
        visualize_dict = dict(profiles_counts=self.broker_visuals.do_profiles_counts,
                              created_component_json=self.broker_visuals.get_created_component_json,
                              last_record=self.broker_visuals.get_last_record,
                              get_profile_count=self.broker_visuals.get_profile_count
                              )

        if self.visualize in visualize_dict:
            self.context = visualize_dict[self.visualize]()
        elif self.param_dict.get("target_id", str()):
            self.context = self.broker_visuals.do_table_data()
        else:
            self.context = self.broker_visuals.do_row_data()

        return self.context

    def validate_and_delete(self):
        """
        function handles the delete of a record for those components
        that have provided a way of first validating (dependencies checks etc.) this action
        :return:
        """

        validate_delete_method = getattr(self.da_object, "validate_and_delete", None)

        if validate_delete_method is None:
            return self.context

        if not callable(validate_delete_method):
            return self.context

        target_id = self.param_dict.get("target_id", str())
        target_ids = self.param_dict.get("target_ids", [])
        result = self.da_object.validate_and_delete(target_id=target_id, target_ids=target_ids)
        if result.get("status", "") == "success":
            self.context = self.broker_visuals.do_table_data()
        self.context["action_feedback"] = result
        return self.context
    
    def do_delete(self):
        target_ids = [ObjectId(i) for i in self.param_dict.get("target_ids")]

        # if ever it was needed to re-implement 'soft' delete uncomment the following lines and
        # comment out the 'hard' delete query

        # soft delete
        # self.da_object.get_collection_handle().update_many(
        #     {"_id": {"$in": target_ids}}, {"$set": {"deleted": d_utils.get_deleted_flag()}}
        # )

        # hard delete
        self.da_object.get_collection_handle().remove({'_id': {'$in': target_ids}})

        self.context = self.broker_visuals.do_table_data()
        return self.context

    """  need to move to copo_read_submission
    """
    def do_lift_submission_embargo(self):
        '''
        function brokers the release of a submission
        :return:
        '''

        return Submission().lift_embargo(submission_id=self.param_dict.get("target_id", str()))
   

    def do_form(self):
        target_id = self.param_dict.get("target_id")
        component_dict = self.param_dict.get("component_dict", dict())
        message_dict = self.param_dict.get("message_dict", dict())

        kwargs = dict()
        kwargs["referenced_field"] = self.param_dict.get("referenced_field", str())
        kwargs["referenced_type"] = self.param_dict.get("referenced_type", str())

        self.context["form"] = htags.generate_copo_form(self.component, target_id, component_dict, message_dict,
                                                        self.profile_id, **kwargs)
        self.context["form"]["visualize"] = self.param_dict.get("visualize")
        return self.context

    def do_form_and_component_records(self):
        # generates form, and in addition returns records of the form component, this could, for instance, be
        # used for cloning of a record

        kwargs = dict()
        kwargs["referenced_field"] = self.param_dict.get("referenced_field", str())
        kwargs["referenced_type"] = self.param_dict.get("referenced_type", str())

        self.context = self.do_form()
        self.context["component_records"] = htags.generate_component_records(self.component, self.profile_id, **kwargs)

        return self.context
    
    """
    def do_doi(self):
        id_handle = self.param_dict.get("id_handle")
        id_type = self.param_dict.get("id_type")

        doi_resolve = DOI2Metadata(id_handle, id_type).get_resolve(self.component)

        self.set_extra_params(dict(target_id=str(),
                                   component_dict=doi_resolve.get("component_dict", dict()),
                                   message_dict=doi_resolve.get("message_dict", dict()))
                              )

        return self.do_form()
    """
    
    def do_initiate_submission(self):
        kwarg = dict(datafile_ids=self.param_dict.get("datafile_ids", list()))
        self.context["submission_token"] = str(self.da_object.save_record(dict(), **kwarg).get("_id", str()))
        return self.context

    def do_user_email(self):
        # user_id = self.param_dict.get("user_id", str())
        user_id = data_utils.get_current_user().id
        user_email = self.param_dict.get("user_email", str())
        user = User.objects.get(pk=int(user_id))
        user.email = user_email
        user.save()

        return self.context

    def do_component_record(self):
        self.context["component_record"] = self.da_object.get_record(self.param_dict.get("target_id"))

        return self.context

    def component_form_record(self):
        target_id = self.param_dict.get("target_id")
        component_dict = self.param_dict.get("component_dict", dict())
        message_dict = self.param_dict.get("message_dict", dict())

        kwargs = dict()
        kwargs["referenced_field"] = self.param_dict.get("referenced_field", str())
        kwargs["referenced_type"] = self.param_dict.get("referenced_type", str())
        kwargs["action_type"] = self.param_dict.get("action_type", str())

        form_value = htags.generate_copo_form(self.component, target_id, component_dict, message_dict,
                                              self.profile_id, **kwargs)

        self.context["component_record"] = form_value["form_value"]
        self.context["component_schema"] = form_value["form_schema"]
        return self.context

    '''
    def do_sanitise_submissions(self):

        records = self.da_object.get_all_records()

        for submission in records:
            if "bundle_meta" not in submission:
                bundle_meta = list()

                for file_id in submission.get("bundle", list()):
                    datafile = DataFile().get_record(file_id)
                    if datafile:
                        upload_status = False

                        if str(submission.get("complete", False)).lower() == 'true':
                            upload_status = True
                        bundle_meta.append(
                            dict(
                                file_id=file_id,
                                file_path=datafile.get("file_location", str()),
                                upload_status=upload_status
                            )
                        )
                submission["bundle_meta"] = bundle_meta
                submission['target_id'] = str(submission.pop('_id'))
                self.da_object.save_record(dict(), **submission)

        self.context["sanitise_status"] = True

        return self.context
    
    def do_clone_description_bundle(self):
        """
        function creates a new description by cloning an existing (specified) bundle
        :return:
        """

        target_id = self.param_dict.get("target_id", str())
        bundle_name = self.param_dict.get("bundle_name", str())

        result = dict(status="success", message="")

        if Description().get_description_handle().find(
                {"name": {'$regex': "^" + bundle_name + "$",
                          "$options": 'i'}}).count() >= 1:
            result["status"] = "error"
            result["message"] = "Bundle name must be unique"

            self.context["result"] = result
            return self.context

        # retrieve clone target
        description = Description().GET(target_id)

        # new bundle being created
        try:
            bundle = Description().create_description(profile_id=self.profile_id, component=self.component,
                                                      name=bundle_name, stages=description.get('stages', list()),
                                                      attributes=description.get('attributes', dict()),
                                                      meta=description.get('meta', dict()))

            result["data"] = dict(id=str(bundle["_id"]), name=bundle["name"])
        except Exception as e:
            message = "Couldn't create bundle: " + bundle_name + " " + str(e)
            result["status"] = "error"
            result["message"] = message

        self.context["result"] = result
        return self.context
    
    def create_rename_description_bundle(self):
        """
        function creates a new description bundle or renames an existing one
        :return:
        """

        target_id = self.param_dict.get("target_id", str())
        bundle_name = self.param_dict.get("bundle_name", str())

        result = dict(status="success", message="")

        if Description().get_description_handle().find(
                {"name": {'$regex': "^" + bundle_name + "$",
                          "$options": 'i'}}).count() >= 1:
            result["status"] = "error"
            result["message"] = "Bundle name must be unique"
        elif target_id:
            # updating existing bundle
            Description().edit_description(target_id, {"name": bundle_name})

            try:
                Description().edit_description(target_id, {"name": bundle_name})
            except Exception as e:
                message = "Couldn't update bundle: " + bundle_name + " " + str(e)
                result["status"] = "error"
                result["message"] = message
        else:
            # new bundle being created
            try:
                bundle = Description().create_description(profile_id=self.profile_id, component=self.component,
                                                          name=bundle_name)
                result["data"] = dict(id=str(bundle["_id"]), name=bundle["name"])
            except Exception as e:
                message = "Couldn't create bundle: " + bundle_name + " " + str(e)
                result["status"] = "error"
                result["message"] = message

        self.context["result"] = result
        return self.context
    '''

    def do_submit_assembly(self):
        """
        function handles the delete of a record for those components
        that have provided a way of first validating (dependencies checks etc.) this action
        :return:
        """
        '''
        submit_assembly = getattr(self.da_object, "submit_assembly", None)

        if submit_assembly is None:
            return self.context

        if not callable(submit_assembly):
            return self.context
        '''
        target_id = self.param_dict.get("target_id", str())
        target_ids = self.param_dict.get("target_ids", [])
        result = EnaAssembly.submit_assembly(profile_id=self.profile_id,  target_id=target_id, target_ids=target_ids)
    
        report_metadata = dict()
        report_metadata["status"] = result.get("status", "success")
        report_metadata["message"] = result.get("message", "success")
        self.context["action_feedback"] = report_metadata

        return self.context
    
    def do_submit_annotation(self):
        """
        function handles the delete of a record for those components
        that have provided a way of first validating (dependencies checks etc.) this action
        :return:
        """

        target_id = self.param_dict.get("target_id", str())
        target_ids = self.param_dict.get("target_ids", [])

        result = EnaAnnotation.submit_seq_annotation(profile_id=self.profile_id, target_ids=target_ids,
                                                     target_id=target_id)
        report_metadata = dict()
        report_metadata["status"] = result.get("status", "success")
        report_metadata["message"] = result.get("message", "success")
        self.context["action_feedback"] = report_metadata

        return self.context

    def do_submit_read(self):
        """
        function handles the delete of a record for those components
        that have provided a way of first validating (dependencies checks etc.) this action
        :return:
        """

        target_id = self.param_dict.get("target_id", str())
        target_ids  = self.param_dict.get("target_ids", [])
        sample_checklist_id = self.request_dict.get("sample_checklist_id", str())

        result = ena_read.submit_read(profile_id=self.profile_id, target_ids=target_ids, target_id=target_id,checklist_id=sample_checklist_id)
        report_metadata = dict()
        report_metadata["status"] = result.get("status", "success")
        report_metadata["message"] = result.get("message", "success")
        self.context["action_feedback"] = report_metadata       
        if result.get("status","success") == "success":
            self.context["table_data"] = ena_read.generate_read_record(profile_id=self.profile_id,checklist_id=sample_checklist_id)
            self.context["component"] = "read"
        return self.context

    def do_delete_read(self):
        """
        function handles the delete of a record for those components
        that have provided a way of first validating (dependencies checks etc.) this action
        :return:
        """

        target_id = self.param_dict.get("target_id", str())
        target_ids  = self.param_dict.get("target_ids", [])
        sample_checklist_id  = self.request_dict.get("sample_checklist_id", [])

        result = ena_read.delete_ena_records(profile_id=self.profile_id, target_ids=target_ids,
                                                        target_id=target_id)
        report_metadata = dict()
        report_metadata["status"] = result.get("status", "success")
        report_metadata["message"] = result.get("message", "success")
        self.context["action_feedback"] = report_metadata
        if result.get("status","success") == "success":
            self.context["table_data"] = ena_read.generate_read_record(profile_id=self.profile_id, checklist_id=sample_checklist_id)
            self.context["component"] = "read"
        return self.context

    def do_submit_tagged_seq(self):
        target_id = self.param_dict.get("target_id", str())
        target_ids  = self.param_dict.get("target_ids", [])
        tagged_seq_checklist_id = self.request_dict.get("tagged_seq_checklist_id", str())
        result = EnaTaggedSequence().submit_tagged_seq(profile_id=self.profile_id, checklist_id=tagged_seq_checklist_id, target_ids=target_ids, target_id=target_id)
        report_metadata = dict()
        report_metadata["status"] = result.get("status","success")
        report_metadata["message"] = result.get("message", "success")
        self.context["action_feedback"] = report_metadata
        if result.get("status","success") == "success":
            self.context["table_data"] = EnaTaggedSequence().generate_taggedseq_record(profile_id=self.profile_id, checklist_id=tagged_seq_checklist_id)
            self.context["component"] = "taggedseq"
        return self.context
    
class BrokerVisuals:
    def __init__(self, **kwargs):
        self.param_dict = kwargs
        self.component = self.param_dict.get("component", str())
        self.profile_id = self.param_dict.get("profile_id", str())
        self.user_id = self.param_dict.get("user_id", str())
        self.context = self.param_dict.get("context", dict())
        self.request_dict = self.param_dict.get("request_dict", dict())

    def set_extra_params(self, extra_param):
        for k, v in extra_param.items():
            self.param_dict[k] = v

    def do_table_data(self):
        table_data_dict = dict(
            accessions=(accession.generate_accessions_record, dict(profile_id=self.profile_id, isUserProfileActive=self.request_dict.get("isUserProfileActive", str()), isSampleProfileTypeStandalone=self.request_dict.get("isSampleProfileTypeStandalone", str()))),
            accessions_dashboard=(accession.generate_accessions_record, dict(profile_id=self.profile_id, isUserProfileActive=self.request_dict.get("isUserProfileActive", str()), isSampleProfileTypeStandalone=self.request_dict.get("isSampleProfileTypeStandalone", str()))),
            #annotation=(htags.generate_copo_table_data, dict(profile_id=self.profile_id, component=self.component)),
            #publication=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
            #person=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
            #datafile=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
            sample=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
            #source=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
            #repository=(htags.generate_repositories_records, dict(component=self.component)),
            metadata_template=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
            profile=(htags.generate_copo_profiles_data, dict(profiles=Profile().get_all_profiles())),
            submission=(htags.generate_submissions_records, dict(profile_id=self.profile_id, component=self.component)),
            seqannotation=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
            assembly=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
            read = (ena_read.generate_read_record, dict(profile_id=self.profile_id,checklist_id=self.request_dict.get("sample_checklist_id", str()))),
            files = (copo_file.generate_files_record, dict(user_id=self.user_id)),
            taggedseq = (EnaTaggedSequence().generate_taggedseq_record, dict(profile_id=self.profile_id,checklist_id=self.request_dict.get("tagged_seq_checklist_id", str()))),
        )

        # NB: in table_data_dict, use an empty dictionary as a parameter for listed functions that define zero arguments

        if self.component in table_data_dict:
            kwargs = table_data_dict[self.component][1]
            self.context["table_data"] = table_data_dict[self.component][0](**kwargs)

        self.context["component"] = self.component

        return self.context

    '''
    def do_managed_repositories(self):
        """
        function returns repositories for which the request user is a manager
        :return:
        """

        self.context["table_data"] = htags.generate_managed_repositories(component=self.component, user_id=self.user_id)
        self.context["component"] = self.component

        return self.context
    
    def do_get_submission_meta_repo(self):
        """
        function brokers metadata and repository details for a submission
        :return:
        """
        target_id = self.param_dict.get("target_id", str())
        self.context["result"] = htags.get_submission_meta_repo(submission_id=target_id, user_id=self.user_id)
        return self.context
    '''
    def do_view_submission_remote(self):
        """
        function brokers the generation of resource url/identifier to a submission in its remote location
        :return:
        """

        self.context = htags.get_submission_remote_url(submission_id=self.param_dict.get("target_id", str()))
        return self.context

    def do_server_side_table_data(self):
        self.context["component"] = self.component
        request_dict = self.param_dict.get("request_dict", dict())

        data = htags.generate_server_side_table_records(self.profile_id, component=self.component, request=request_dict)
        self.context["draw"] = data["draw"]
        self.context["records_total"] = data["records_total"]
        self.context["records_filtered"] = data["records_filtered"]
        self.context["data_set"] = data["data_set"]

        return self.context

    def do_row_data(self):
        record_object = self.param_dict.get("record_object", dict())

        target_id = record_object.get("_id", str())

        table_data_dict = dict(
            publication=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
            person=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
            sample=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
            profile=(htags.generate_copo_profiles_data, dict(profiles=Profile().get_for_user())),
            datafile=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
            #repository=(htags.generate_repositories_records, dict(component=self.component)),
        )

        # NB: in table_data_dict, use an empty dictionary as a parameter to functions that define zero arguments

        if self.component in table_data_dict:
            kwargs = table_data_dict[self.component][1]
            self.context["table_data"] = table_data_dict[self.component][0](**kwargs)

        self.context["component"] = self.component
        return self.context

    def do_get_submission_accessions(self):
        target_id = self.param_dict.get("target_id", str())
        self.context["submission_accessions"] = htags.generate_submission_accessions_data(submission_id=target_id)
        return self.context

    def do_get_submission_datafiles(self):
        target_id = self.param_dict.get("target_id", str())
        self.context["table_data"] = htags.generate_submission_datafiles_data(submission_id=target_id)
        return self.context

    '''
    def do_get_destination_repo(self):
        """
        function brokers submission destination repository details
        :return:
        """
        target_id = self.param_dict.get("target_id", str())
        self.context["result"] = htags.get_destination_repo(submission_id=target_id)
        return self.context
    '''
    # do_get_repo_stats
    def do_get_repo_stats(self):
        """
        function brokers statistics for the target repository
        :return:
        """
        self.context["result"] = htags.get_repo_stats(repository_id=self.param_dict.get("target_id", str()))
        return self.context

    def do_profiles_counts(self):
        self.context["profiles_counts"] = htags.generate_copo_profiles_counts(Profile().get_all_profiles())
        return self.context

    def get_profile_count(self):
        self.context["profile_count"] = True
        return self.context

    def get_created_component_json(self):
        record_object = self.param_dict.get("record_object", dict())
        data_source = self.param_dict.get("data_source", str())

        target_id = str(record_object.get("_id", str()))
        option_values = list()

        if data_source:
            option_values = COPOLookup(accession=[target_id],
                                       data_source=data_source, profile_id=self.profile_id).broker_component_search()['result']

        self.context["option_values"] = option_values
        self.context["created_record_id"] = target_id

        return self.context

    def get_last_record(self):
        self.context["record_object"] = self.param_dict.get("record_object", dict())
        return self.context

    '''  deprecated
    def do_wizard_messages(self):
        self.context['wiz_message'] = d_utils.json_to_pytype(lkup.MESSAGES_LKUPS["wizards_messages"])["properties"]
        return self.context
    def do_metadata_ratings(self):
        self.context['metadata_ratings'] = MetadataRater(self.param_dict.get("datafile_ids")).get_datafiles_rating()
        return self.context
    
    def do_description_summary(self):
        record = DataFile().get_record(self.param_dict.get("target_id"))
        self.context['description'] = htags.resolve_description_data(record.get("description", dict()), dict())

        description_token = record.get('description_token', str())
        self.context['description']['description_record'] = dict()

        if description_token:
            description_record = Description().GET(description_token)
            if description_record:
                if not description_record["name"]:
                    description_record["name"] = "N/A"
                self.context['description']['description_record'] = dict(name=description_record["name"],
                                                                         id=str(description_record["_id"]))

        return self.context
    
    def do_un_describe(self):
        datafile_ids = [ObjectId(i) for i in self.param_dict.get("datafile_ids")]

        DataFile().get_collection_handle().update_many(
            {"_id": {"$in": datafile_ids}}, {"$set": {"description": dict()}}
        )

        return self.context
    '''
    def do_attributes_display(self):
        target_id = self.param_dict.get("target_id", str())
        self.context['component_attributes'] = htags.generate_attributes(self.component, target_id)
        self.context['component_label'] = htags.get_labels().get(self.component, dict()).get("label", str())

        return self.context

    def get_component_help_messages(self):
        self.context['context_help'] = dict()
        self.context['help_messages'] = dict()

        paths_dict = lkup.MESSAGES_LKUPS['HELP_MESSAGES']

        if self.component in paths_dict:
            self.context['help_messages'] = data_utils.json_to_pytype(lkup.MESSAGES_LKUPS['HELP_MESSAGES'][self.component])

        # context help, relevant to the current component (e.g., datafile)
        if "context_help" in paths_dict:
            help_dict = data_utils.json_to_pytype(lkup.MESSAGES_LKUPS['HELP_MESSAGES']["context_help"])
            properties_temp = help_dict['properties']
            v = [x for x in properties_temp if len(x['context']) > 0 and x['context'][0] == self.component]
            if v:
                help_dict['properties'] = v
            self.context['context_help'] = help_dict

        # get user email
        self.context = self.do_user_has_email()

        return self.context

    def do_user_has_email(self):
        req = helpers.get_current_request()
        user = User.objects.get(pk=int(req.user.id))

        self.context['user_has_email'] = bool(user.email.strip())

        return self.context

    def do_update_quick_tour_flag(self):
        req = helpers.get_current_request()
        quick_tour_flag = self.param_dict.get("quick_tour_flag", "false")

        if quick_tour_flag == "false":
            quick_tour_flag = False
        else:
            quick_tour_flag = True

        req.session["quick_tour_flag"] = quick_tour_flag
        self.context["quick_tour_flag"] = req.session["quick_tour_flag"]

        return self.context

    def do_get_component_info(self):
        target_id = self.param_dict.get("target_id", str())
        da_object = DAComponent(target_id, self.component)
        self.context["component_info"] = "welcome to " + str(da_object.get_component_count())

        return self.context

    def do_get_profile_info(self):
        self.context["component_info"] = "welcome to " + self.component

        return self.context
