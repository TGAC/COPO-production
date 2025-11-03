from common.utils.logger import Logger
from sapiopylib.rest.utils.recordmodel.PyRecordModel import PyRecordModel
from common.dal.profile_da import Profile
from .sapio.sapio_datamanager  import Sapio
from typing import List


l = Logger()

def get_sapio_sample_type_options():
    config = Sapio().picklistManager.get_picklist("Exemplar Sample Types")
    return [{"value": s, "label": s} for s in config.entry_list]
     
def pre_save_edp_profile(auto_fields, **kwargs):
    target_id = kwargs.get("target_id","")
    if not target_id:
        return {"status": "success"}
    profile = Profile().get_record(target_id)
    sapio_project_id = profile.get("sapio_project_id","")

    if not sapio_project_id:
        return {"status": "success"}
    else:
        no_of_samples = auto_fields.get("copo.profile.no_of_samples", [])
        plate_ids = auto_fields.get("copo.profile.sapio_plate_ids", [])
        project_records = Sapio().dataRecordManager.query_data_records(data_type_name="Project", 
                                                data_field_name="C_ProjectIdentifier", 
                                                value_list=[sapio_project_id]).result_list
        if not project_records or len(project_records) ==0:
            return {"status": "error", "message": f"Sapio Project {profile['sapio_project_id']} not found."}                
        project_record = project_records[0]
        project: PyRecordModel = Sapio().inst_man.add_existing_record(project_record)  
        Sapio().relationship_man.load_children([project], 'Sample')
        samples_under_project: List[PyRecordModel] = project.get_children_of_type('Sample')
        if samples_under_project:
            if len(samples_under_project) > int(no_of_samples):
                diff = len(samples_under_project) - int(profile["no_of_samples"])
                for sample in samples_under_project:
                    if not sample.get_field_value("C_CustomerSampleName",""):
                        diff -=1

                    if diff <=0:
                        break
                if diff >0:
                    return {"status": "error", "message": f"Sapio Project {profile['sapio_project_id']} has customer samples associated. Cannot decrease the no. of samples."}
                
            plates = plate_ids.split(",")            
            assigned_plates = set()
            for sample in samples_under_project:
                assigned_plate = sample.get_field_value("PlateId","")
                if assigned_plate:
                    assigned_plates.add(assigned_plate)
                    if assigned_plate not in plates:
                        return {"status": "error", "message": f"Sapio Project {profile['sapio_project_id']} has samples associated with plate {assigned_plate}. Cannot remove this plate from profile."}                    
        return {"status": "success"}


def post_save_edp_profile(profile):
    project_record = None
    try:
        #update /create Sapio Project
        if not profile.get("sapio_project_id",""):
            project_records = Sapio().dataRecordManager.add_data_records_with_data(data_type_name="Project", field_map_list=[{"ProjectName": profile.get("jira_ticket_number",""),
                                                                                                    "ProjectDesc": profile.get("description",""),
                                                                                                    "C_BudgetHolder": profile.get("budget_user","")}])            
            
            sapio_project_id = project_records[0].get_field_value('C_ProjectIdentifier')
            profile["sapio_project_id"] = sapio_project_id
            Profile().get_collection_handle().update_one({"_id":profile["_id"]},{"$set":{"sapio_project_id":sapio_project_id}})
            project_record = project_records[0]
        else:
            project_records = Sapio().dataRecordManager.query_data_records(data_type_name="Project", 
                                                        data_field_name="C_ProjectIdentifier", 
                                                        value_list=[profile["sapio_project_id"]]).result_list
            if not project_records or len(project_records) ==0:
                raise Exception(f"Failed to Find Sapio Project {profile["sapio_project_id"]}")
            project_record = project_records[0]
            project_record.set_field_value("ProjectName", profile.get("jira_ticket_number",""))
            project_record.set_field_value("ProjectDesc", profile.get("description",""))
            project_record.set_field_value("C_BudgetHolder", profile.get("budget_user",""))
            Sapio().dataRecordManager.commit_data_records([project_record])

        #attach samples to Sapio Project
        #get all samples for Sapio Project
        project: PyRecordModel = Sapio().inst_man.add_existing_record(project_record)  
        Sapio().relationship_man.load_children([project], 'Sample')
        samples_under_project: List[PyRecordModel] = project.get_children_of_type('Sample')
        Sapio().relationship_man.load_children([project], 'Plate')
        plate_under_project: List[PyRecordModel] = project.get_children_of_type('Plate')

        #create samples if not exists
        if not samples_under_project or len(samples_under_project) < profile["no_of_samples"]:    
            existing_no_of_samples = len(samples_under_project) if samples_under_project else 0
            sample_records = Sapio().dataRecordManager.add_data_records_with_data(data_type_name="Sample", 
                                                                                  field_map_list=[{"ExemplarSampleType": profile["sample_type"], 
                                                                                                  "ContainerType": profile["container_type"]}
                                                                                                  for _ in range(existing_no_of_samples, int(profile["no_of_samples"]))])
            samples : List[PyRecordModel] = Sapio().inst_man.add_existing_records(sample_records)
            project.add_children(samples)
            samples_under_project.extend(samples)

        existing_plate_ids = set()
        existing_plate_ids_under_project = set()

        for plate in plate_under_project:
            existing_plate_ids_under_project.add(plate.get_field_value("PlateId"))

        #attach plate to Sapio Project, assume it is  96 well plate (8 rows x 12 columns)
        plates = profile.get("sapio_plate_ids","").split(",")
        if plates:
            missing_plates = set(plates) - existing_plate_ids_under_project
            plate_records = Sapio().dataRecordManager.query_data_records(data_type_name="Plate", 
                                                data_field_name="PlateId", 
                                                value_list=list(missing_plates)).result_list
            existing_plate_ids_sapio = set()
            for plate_record in plate_records:
                existing_plate_ids_sapio.add(plate_record.get_field_value("PlateId"))
            
            plate_record_models: List[PyRecordModel] = Sapio().inst_man.add_existing_records(plate_records)  

            project.add_children(plate_record_models)

            missing_plates_not_in_sapio = missing_plates - existing_plate_ids_sapio
            remove_plates = existing_plate_ids_under_project - set(plates)

            if missing_plates_not_in_sapio:
                plate_records = Sapio().dataRecordManager.add_data_records_with_data(data_type_name="Plate", field_map_list=[{"PlateId": plate,
                                                                                "PlateColumns": 12, "PlateRows":8}for plate in missing_plates_not_in_sapio])            
                plate_record_models: List[PyRecordModel] = Sapio().inst_man.add_existing_records(plate_records)  
                #attach new plate to Sapio project
                project.add_children(plate_record_models)
                            
            if remove_plates:
                #check if not attached samples to these plates
                for sample in samples_under_project:
                    assigned_plate = sample.get_field_value("PlateId")
                    if assigned_plate in remove_plates:
                        raise Exception(f"Sapio Project {profile['sapio_project_id']} has samples associated with plate {assigned_plate}. Cannot remove this plate from profile.")

                plate_records = Sapio().dataRecordManager.query_data_records(data_type_name="Plate", 
                                                data_field_name="PlateId", 
                                                value_list=list(remove_plates)).result_list           
                #remove plate from Sapio project
                plate_record_models: List[PyRecordModel] = Sapio().inst_man.add_existing_records(plate_records)  
                project.remove_children(plate_record_models)
                
        Sapio().relationship_man.load_children([project], 'Plate')
        plates_under_project: List[PyRecordModel] = project.get_children_of_type('Plate')

        samples_without_plate = set()
        if samples_under_project:
            for sample in samples_under_project:
                assigned_plate = sample.get_field_value("PlateId")
                if not assigned_plate:
                    samples_without_plate.add(sample)

        if samples_without_plate:
            Sapio().relationship_man.load_children(plates_under_project, 'Sample')
            for plate in plates_under_project:
                samples_under_plate: List[PyRecordModel] = plate.get_children_of_type('Sample')
                for _ in range(len(samples_under_plate), 96): #assume 96 well plate, 8X12
                    if not samples_without_plate:
                        break
                    sample = samples_without_plate.pop()
                    #sample_model = Sapio().inst_man.add_existing_record(sample)  
                    plate.add_child(sample)
                    sample.set_field_value("PlateId", plate.get_field_value("PlateId"))
        

        Sapio().rec_man.store_and_commit()
        """
        for plate in plates_under_project:
            plate.do_commit()
        for sample in samples_under_project:
            sample.do_commit()
        project.do_commit()
        """

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