import pandas as pd

from common.dal.copo_da import DAComponent

class ImageSchema(DAComponent):
    def __init__(self, profile_id=None, subcomponent=None):
        super(ImageSchema, self).__init__(
            profile_id, 'imageschema', subcomponent=subcomponent
        )
    
    def get_schema(self, schema_name, target_id=str()) :
        schemas = {}

        if target_id:
            image = ImageSchema().get_collection_handle().find_one({'name':schema_name},{'schemas':1})
            image_schemas = image['schemas']

            if image_schemas:
                for component, item in image_schemas.items():
                    component_schema_df = pd.DataFrame.from_records(item)
                    component_schema_df = component_schema_df.drop(component_schema_df[pd.isna(component_schema_df[target_id])].index)
                    if component_schema_df.empty:
                        continue    

                    component_schema_df['label'] = component_schema_df['term_label']
                    component_schema_df['control'] = 'text'
                    component_schema_df['show_as_attribute'] = True
                    component_schema_df['id'] = component_schema_df['term_name']

                    schemas[component] = component_schema_df.to_dict(orient='records')      

        return schemas
    
    def get_checklists(self, schema_name, checklist_id=str()):

        projection = {'checklists': 1}
        if checklist_id:
            projection = {'checklists.' + checklist_id: 1}
        projection['_id'] = 0
        checklists = self.get_collection_handle().find_one(
            {'name': schema_name}, projection
        )

        if checklists:
            return checklists.get('checklists', {})
        else:
            return {}
