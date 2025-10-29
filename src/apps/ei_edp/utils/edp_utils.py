from common.utils.logger import Logger
from sapiopylib.rest.User import SapioUser
from sapiopylib.rest.DataMgmtService import DataMgmtServer
from sapiopylib.rest.DataRecordManagerService import DataRecordManager
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel
from sapiopylib.rest.utils.recordmodel.RecordModelManager import RecordModelManager, RecordModelInstanceManager, \
    RecordModelRelationshipManager
from common.dal.profile_da import Profile
from .sapio.sapio_datamanager  import Sapio

l = Logger()

def get_sapio_sample_type_options():
    config = Sapio().picklistManager.get_picklist("Exemplar Sample Types")
    return [{"value": s, "label": s} for s in config.entry_list]
     
def post_save_edp_profile(profile):
    #create or update sapio project
    try:
        if not profile.get("sapio_project_id",""):
            project_records = Sapio().dataRecordManager.add_data_records_with_data(data_type_name="Project", field_map_list=[{"ProjectName": profile.get("jira_ticket_number",""),
                                                                                                    "ProjectDesc": profile.get("description",""),
                                                                                                    "C_BudgetHolder": profile.get("budget_user","")}])
            sapio_project_id = project_records[0].get_field_value('C_ProjectIdentifier')
            profile["sapio_project_id"] = sapio_project_id
            Profile().get_collection_handle().update_one({"_id":profile["_id"]},{"$set":{"sapio_project_id":sapio_project_id}})
        else:
            project_record = Sapio().dataRecordManager.query_data_records(data_type_name="Project", 
                                                        data_field_name="C_ProjectIdentifier", 
                                                        value_list=[profile["sapio_project_id"]]).result_list[0]
            project_record.set_field_value("ProjectName", profile.get("jira_ticket_number",""))
            project_record.set_field_value("ProjectDesc", profile.get("description",""))
            project_record.set_field_value("C_BudgetHolder", profile.get("budget_user",""))
            Sapio().dataRecordManager.commit_data_records([project_record])
    except Exception as e:        
        l.exception(e)
        l.error("Failed to create or update sapio project for profile id: " + str(profile["_id"]) + " Error: " + str(e))
        return  {"status":"warning", "message":"Profile has been saved. However, it is failed to update to Sapio! "}
        
    return {"status": "success"}


def post_delete_edp_profile(profile):
    if profile.get("sapio_project_id",""):
        try:
            record = Sapio().dataRecordManager.query_data_records(data_type_name="Project", 
                                                    data_field_name="C_ProjectIdentifier", 
                                                    value_list=[profile["sapio_project_id"]]).result_list[0]
            Sapio().dataRecordManager.delete_data_record(record=record, recursive_delete=True)
        except Exception as e:
            l.exception(e)
            l.error("Failed to delete sapio profile for profile id: " + str(profile["_id"]) + " Error: " + str(e))
            return  {"status":"warning", "message":"Profile has been deleted. However, it is failed to delete from Sapio! "}
    return {"status": "success"}