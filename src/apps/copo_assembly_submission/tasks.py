from src.celery import app
from common.utils.logger import Logger
from src.apps.copo_core.tasks import only_one, CopoBaseClassForTask
from .utils import EnaAssembly as enaAssembly

 
@app.task(bind=True, base=CopoBaseClassForTask)
@only_one(key="process_assembly_submission", timeout=5)
def process_assembly_submission(self):
    Logger().debug("Running process_assembly_submission")
    enaAssembly.process_assembly_pending_submission()
    return True

@app.task(bind=True, base=CopoBaseClassForTask)
@only_one(key="process_update_assembly_submission_pending", timeout=5)
def update_assembly_submission_pending(self):
    Logger().debug("Running update_assembly_submission_pending")
    enaAssembly.update_assembly_submission_pending()
    return True
