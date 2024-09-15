from src.celery import app
from common.utils.logger import Logger
from src.apps.copo_core.tasks import only_one, CopoBaseClassForTask
from .utils.da import Image

 
@app.task(bind=True, base=CopoBaseClassForTask)
@only_one(key="process_image_submission", timeout=5)
def process_image_submission(self):
    Logger().debug("Running process_image_submission")
    Image().process_image_pending_submission()
    return True

@app.task(bind=True, base=CopoBaseClassForTask)
@only_one(key="process_update_image_submission_pending", timeout=5)
def update_image_submission_pending(self):
    Logger().debug("Running update_image_submission_pending")
    Image().update_image_submission_pending()
    return True
