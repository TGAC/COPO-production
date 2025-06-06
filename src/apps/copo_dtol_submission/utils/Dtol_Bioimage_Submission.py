from common.schemas.utils import data_utils
from common.utils.logger import Logger
from pathlib import Path
from common.dal.copo_da import DataFile
from common.dal.submission_da import Submission
from common.dal.sample_da import Source
import subprocess
from common.lookup.copo_enums import Loglvl
import os
from datetime import datetime, timedelta
from django.conf import settings
from common.utils.helpers import get_env, get_datetime, notify_frontend

BIOIMAGE_UPLOAD_PASSWORD = get_env("BIOIMAGE_PASSWORD")  # "password"
BIOIMAGE_SERVER = get_env("BIOIMAGE_SERVER")  #  
BIOIMAGE_UPLOAD_PATH = get_env("BIOIMAGE_PATH")  #  
BIOIMAGE_LOCAL_ARCHIVE_PARENT_PATH = f"{get_env('MEDIA_PATH')}sample_images/archive"
BIOIMAGE_LOCAL_ARCHIVE_PATH = {"asg_specimen" : f"{BIOIMAGE_LOCAL_ARCHIVE_PARENT_PATH}/ASG",
                             "dtol_specimen" : f"{BIOIMAGE_LOCAL_ARCHIVE_PARENT_PATH}/DToL",
                             "erga_specimen" : f"{BIOIMAGE_LOCAL_ARCHIVE_PARENT_PATH}/ERGA",
                             "copo_specimen" : f"{BIOIMAGE_LOCAL_ARCHIVE_PARENT_PATH}/COPO"}

BIOIMAGE_PATH = f"{settings.MEDIA_ROOT}sample_images"
BIOIMAGE_ARCHIVE = f"{BIOIMAGE_PATH}/archive"
BIOIMAGE_THUMBNAIL = f"{BIOIMAGE_PATH}/thumbnail"

BIOIMAGE_SENT = {"asg_specimen" : f"{BIOIMAGE_PATH}/ASG",
                 "dtol_specimen" : f"{BIOIMAGE_PATH}/DToL",
                 "erga_specimen" : f"{BIOIMAGE_PATH}/ERGA",
                 "copo_specimen" : f"{BIOIMAGE_PATH}/COPO"}

ASPERA_PATH = get_env("ASPERA_PATH")  #"/root/.aspera/cli"
BIOIMAGE_ASPERA_CMD = f"ASPERA_SCP_PASS={BIOIMAGE_UPLOAD_PASSWORD} {ASPERA_PATH}/bin/ascp -P33001 -l50M --move-after-transfer  {BIOIMAGE_ARCHIVE} -i {ASPERA_PATH}/etc/asperaweb_id_dsa.openssh -d {' '.join(BIOIMAGE_SENT.values())} {BIOIMAGE_SERVER}:{BIOIMAGE_UPLOAD_PATH}"


def housekeeping_bioimage_archive():
    housekeep_timestamp = datetime.timestamp(datetime.now() + timedelta(days=-30))
    for type in 'ASG', 'DToL', 'ERGA', 'COPO':
        try:
            with os.scandir(BIOIMAGE_ARCHIVE + "/" + type) as ls:
                for file in ls:
                    if file.is_file() and os.path.getctime(file) < housekeep_timestamp:
                        os.remove(file)
        except FileNotFoundError as e:
            pass

def process_bioimage_pending_submission():
    # submit images
    submissions = Submission().get_bioimage_pending_submission()
    specimen_ids = []
    now = get_datetime()
    complete_sub_ids = []
    pending_sub_ids = []

    #imagePath = Path(settings.MEDIA_ROOT) / "sample_images"
    #sentPath = imagePath / "sent"

    for path in BIOIMAGE_SENT.values():
        Path(path).mkdir(parents=True, exist_ok=True)

    if not submissions:
        return

    for sub in submissions:
        notify_frontend(data={"profile_id": sub["profile_id"]}, msg="Bioimage is being submitted", action="info",
                        html_id="dtol_sample_info")
        specimen_ids.extend(sub["dtol_specimen"])
        if len(sub["dtol_samples"])==0: 
          complete_sub_ids.append(sub["_id"])
        else:
          pending_sub_ids.append(sub["_id"])

    sources = Source().get_sourcemap_by_specimens(specimen_ids)
    for specimenId in specimen_ids:
        source = sources[specimenId]
        type = source.get("sample_type", "copo_specimen")
        seqno = 0
        #if "last_bioimage_submitted" in source and  source["last_bioimage_submitted"]:
        #    lastSubImageDt[specimenId] = source["last_bioimage_submitted"]
        if "bioimage_archive_seq_no" in source and source["bioimage_archive_seq_no"]:
            seqno = source["bioimage_archive_seq_no"]
        try:
            with os.scandir(BIOIMAGE_PATH) as ls:
                for imageFile in ls:
                    if imageFile.name.upper().startswith(specimenId + "-"):
                        # we have a match
                        ##if specimenId not in lastSubImageDt or os.path.getctime(imageFile) > datetime.timestamp(
                        ##        lastSubImageDt[specimenId]):
                        newname = source["biosampleAccession"] + "_" + str(seqno+1) + os.path.splitext(imageFile)[1]
                        DataFile().update_bioimage_name(imageFile.name, newname, f"{BIOIMAGE_LOCAL_ARCHIVE_PATH[type]}/{newname}")
                        os.rename(imageFile.path, Path( BIOIMAGE_SENT[type]) / newname) 
                        try:
                            os.remove(f"{BIOIMAGE_THUMBNAIL}/{imageFile.name}")
                        except FileNotFoundError as e:
                            Logger().log(e, level=Loglvl.ERROR)
                        seqno = seqno + 1
                        print(imageFile.name + " " + newname)
        
        finally:
            Source().add_fields({"last_bioimage_submitted": now,
                                     "bioimage_archive_seq_no": seqno,
                                     "date_modified": now}, source["_id"])

    is_sent = False
    for path in BIOIMAGE_SENT.values():
        if len(os.listdir(path)) > 0:
            is_sent = True
            break

    if is_sent:
        try:
            #Logger().log(BIOIMAGE_ASPERA_CMD, level=Loglvl.DEBUG)
            output = subprocess.check_output(BIOIMAGE_ASPERA_CMD, shell=True)
            notify_frontend(data={"profile_id": sub["profile_id"]}, msg="<br>Bioimage has been submitted", action="info",
                            html_id="dtol_sample_info")
            Logger().log(output)
        except subprocess.CalledProcessError as e:
            Logger().log(e.output, level=Loglvl.ERROR)
            Logger().log("Bioimage was not submitted", level=Loglvl.ERROR)
            notify_frontend(data={"profile_id": sub["profile_id"]}, msg="<br>Bioimage was not submitted due to an error",
                            action="error",
                            html_id="dtol_sample_info")
            print("error code", e.returncode, e.output)
            return
    else:
        notify_frontend(data={"profile_id": sub["profile_id"]}, msg="<br>Bioimage was not submitted", action="info",
                        html_id="dtol_sample_info")

    
    #to handle the case of approving the submission in batch
    Submission().get_collection_handle().update_many(
        {"_id" : {"$in": complete_sub_ids}}, {"$set": {"dtol_specimen": [], "dtol_status":"complete", "date_modified": now}}
    )
    Submission().get_collection_handle().update_many(
        {"_id" : {"$in": pending_sub_ids}}, {"$set": {"dtol_specimen": [], "dtol_status":"pending", "date_modified": now}}
    )