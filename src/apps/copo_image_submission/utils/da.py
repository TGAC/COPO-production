from common.dal.copo_da import DAComponent
from bson.objectid import ObjectId

class Image(DAComponent):
    def __init__(self, profile_id=None):
        super(Image, self).__init__(profile_id, "image")

    def process_image_pending_submission(self):
        pass

    def update_image_submission_pending(self):
        pass