__author__ = 'felixshaw'

from .mongo_util import get_collection_ref

Schemas = get_collection_ref("Schemas")

class DataSchemas:
    def __init__(self, schema):
        self.schema = schema.upper()

    def add_ui_template(self, template):
        # remove any existing UI templates for the target schema
        self.delete_ui_template()

        doc = {"schemaName": self.schema, "schemaType": "UI", "data": template}
        Schemas.insert(doc)

    def delete_ui_template(self):
        Schemas.remove({"schemaName": self.schema, "schemaType": "UI"})

    def get_ui_template(self):
        try:
            doc = Schemas.find_one({"schemaName": self.schema, "schemaType": "UI"})
            doc = doc["data"]
        except Exception as e:
            exception_message = "Couldn't retrieve component schema. " + str(e)
            print(exception_message)
            raise

        return doc

    def get_ui_template_node(self, identifier):
        doc = self.get_ui_template()
        doc = {k.lower(): v for k, v in doc.items() if k.lower() == 'copo'}
        doc = {k.lower(): v for k, v in doc.get("copo", dict()).items() if k.lower() == identifier.lower()}

        return doc.get(identifier.lower(), dict()).get("fields", list())
