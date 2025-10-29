from sapiopylib.rest.pojo.DataRecord import DataRecord
from src.apps.ei_edp.utils.sapio_datamanager import Sapio
class DataType():
    """
    Represents a generic data type.

    Attributes:
        data_type (str): The name of the data type.
    """

    def __init__(self):
        
        """
        Initializes a new instance of the DataType class.
        """
        self.data_type = None

    def create(self, data):
        """
        Creates a new data record.

        Args:
            data (dict): The data to be included in the data record.

        Returns:
            dict: The created data record.
        """
        objects = Sapio().dataRecordManager.add_data_records_with_data(data_type_name=self.data_type, field_map_list=[data])
        return objects[0] if len(objects)>0 else None

    def read(self, _id):
        """
        Retrieves a specific data record.

        Args:
            _id (str): The ID of the data record.

        Returns:
            dict: The retrieved data record.
        """
        return Sapio().dataRecordManager.query_system_for_record(data_type_name=self.data_type, record_id=_id)

    def update(self, _id, data):
        """
        Updates a specific data record.

        Args:
            _id (str): The ID of the data record.
            data (dict): The updated data.

        Returns:
            dict: The updated data record.
        """
        data_record = self.read(_id=_id)
        data_record.set_fields(data)
        Sapio().dataRecordManager.commit_data_records(records_to_update= [data_record])

    def delete(self, _id, recursive_delete=False):
        """
        Deletes a specific data record.

        Args:
            _id (str): The ID of the data record.

        Returns:
            dict: The response indicating the success of the deletion.
        """
        data_record = DataRecord(data_type_name=self.data_type, record_id=_id, fields=[])
        Sapio().dataRecordManager.delete_data_record(record=data_record, recursive_delete=recursive_delete)


class Sample(DataType):
    """
    Represents a sample data type.

    Inherits from the DataType class.
    """

    def __init__(self):
        """
        Initializes a new instance of the Sample class.
        """
        super().__init__()
        self.data_type = "Sample"


class Project(DataType):
    """
    Represents a project data type.

    Inherits from the DataType class.
    """

    def __init__(self):
        """
        Initializes a new instance of the Project class.
        """
        super().__init__()
        self.data_type = "Project"

class Request(DataType):
    """
    Represents a project data type.

    Inherits from the DataType class.
    """

    def __init__(self):
        """
        Initializes a new instance of the Project class.
        """
        super().__init__()
        self.data_type = "Request"

class AssignedProcess(DataType):
    """
    Represents a project data type.

    Inherits from the DataType class.
    """

    def __init__(self):
        """
        Initializes a new instance of the Project class.
        """
        super().__init__()
        self.data_type = "AssignedProcess"    