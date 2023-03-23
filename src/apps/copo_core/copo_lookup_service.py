__author__ = 'etuka'

import os
import pandas as pd
from bson import ObjectId
#from web.apps.copo_core.dal.copo_da import Sample, Source, CGCore
from common.dal.mongo_util import cursor_to_list, get_collection_ref
from common.lookup import lookup
from common.lookup.resolver import RESOLVER
from common.utils import helpers
#import web.apps.copo_core.schemas.utils.data_utils as d_utils

"""
class is a service for the resolution of search terms to local objects in COPO. 
Each resolver should provide a mechanism for:
1. resolving a search term to valid objects
2. resolving accessions (i.e., id, values, etc.) to obtain matching or corresponding objects
"""

Lookups = get_collection_ref("Lookups")


class COPOLookup:
    def __init__(self, **kwargs):
        self.param_dict = kwargs
        self.search_term = self.param_dict.get("search_term", str()).lower()
        self.accession = self.param_dict.get("accession", dict())
        self.data_source = self.param_dict.get("data_source", str())
        self.profile_id = self.param_dict.get("profile_id", str())
        self.referenced_field = self.param_dict.get("referenced_field", str())
        self.drop_downs_pth = RESOLVER['copo_drop_downs']

    def broker_component_search(self):
        dispatcher = {
            'agrovoclabels': self.get_lookup_type,
            'countrieslist': self.get_lookup_type,
            'mediatypelabels': self.get_lookup_type,
            'fundingbodies': self.get_lookup_type,
            'cg_dependency_lookup': self.cg_dependency_lookup,
            'isa_samples_lookup': self.get_isasamples,
            'sample_source_lookup': self.get_samplesource,
            'all_samples_lookup': self.get_allsamples
        }

        result = []
        message = 'error'

        if self.data_source in dispatcher:
            try:
                result = dispatcher[self.data_source]()
                message = 'success'
            except Exception as e:
                exception_message = "Error brokering component search. " + str(e)
                print(exception_message)
                raise

        return dict(result=result, message=message)

    def broker_data_source(self):
        """
        function resolves dropdown list given a data source handle
        :return:
        """

        pths_map = dict(
            select_yes_no=os.path.join(self.drop_downs_pth, 'select_yes_no.json'),
            select_start_end=os.path.join(self.drop_downs_pth, 'select_start_end.json'),
            cgiar_centres=os.path.join(self.drop_downs_pth, 'cgiar_centres.json'),
            crp_list=os.path.join(self.drop_downs_pth, 'crp_list.json'),
            languagelist=os.path.join(self.drop_downs_pth, 'language_list.json'),
            library_strategy=os.path.join(self.drop_downs_pth, 'library_strategy.json'),
            library_source=os.path.join(self.drop_downs_pth, 'library_source.json'),
            library_selection=os.path.join(self.drop_downs_pth, 'library_selection.json'),
            sequencing_instrument=os.path.join(self.drop_downs_pth, 'sequencing_instrument.json'),
            study_type_options=lookup.DROP_DOWNS['STUDY_TYPES'],
            rooting_medium_options=lookup.DROP_DOWNS['ROOTING_MEDIUM'],
            growth_area_options=lookup.DROP_DOWNS['GROWTH_AREAS'],
            nutrient_control_options=lookup.DROP_DOWNS['GROWTH_NUTRIENTS'],
            watering_control_options=lookup.DROP_DOWNS['WATERING_OPTIONS'],
            dataverse_subject_dropdown=lookup.DROP_DOWNS['DATAVERSE_SUBJECTS'],
            repository_options=os.path.join(self.drop_downs_pth, 'metadata_template_types.json'),
            repository_types_list=os.path.join(self.drop_downs_pth, 'repository_types.json'),
            sample_type_options=os.path.join(self.drop_downs_pth, 'sample_types.json'),
        )

        data = pths_map.get(self.data_source, str())

        if isinstance(data, str) and data:  # it's only a path, resolve to get actual data
            data = helpers.json_to_pytype(data)

        return data

    def get_lookup_type(self):
        projection = dict(label=1, accession=1, description=1)
        filter_by = dict(type=self.data_source)

        records = list()

        if self.accession or self.search_term:
            if self.accession:
                bn = list()
                bn.append(self.accession) if isinstance(self.accession, str) else bn.extend(self.accession)
                filter_by["accession"] = {'$in': bn}
            elif self.search_term:
                filter_by["label"] = {'$regex': self.search_term, "$options": 'i'}

            records = cursor_to_list(Lookups.find(filter_by, projection))

            if not records and self.search_term:
                del filter_by["label"]
                records = cursor_to_list(Lookups.find(filter_by, projection))

        return records

    def get_samplesource(self):
        """
        lookup sources related to a sample
        :return:
        """
        from .templatetags import html_tags as htags
        from common.dal.copo_da import Source


        df = pd.DataFrame()

        if self.accession:
            if isinstance(self.accession, str):
                self.accession = self.accession.split(",")

            object_ids = [ObjectId(x) for x in self.accession if x.strip()]
            records = cursor_to_list(Source().get_collection_handle().find({"_id": {"$in": object_ids}}))

            if records:
                df = pd.DataFrame(records)
                df['accession'] = df._id.astype(str)
                df['label'] = df['name']
                df['desc'] = df['accession'].apply(lambda x: htags.generate_attributes("source", x))
                df['description'] = df['desc'].apply(lambda x: self.format_description(x))
                df['server-side'] = True  # ...to request callback to server for resolving item description
        elif self.search_term:
            projection = dict(name=1)
            filter_by = dict()
            filter_by["name"] = {'$regex': self.search_term, "$options": 'i'}

            sort_by = 'name'
            sort_direction = -1

            records = Source(profile_id=self.profile_id).get_all_records_columns(filter_by=filter_by,
                                                                                 projection=projection,
                                                                                 sort_by=sort_by,
                                                                                 sort_direction=sort_direction)

            if not records:
                # try getting all records
                del filter_by["name"]
                records = Source(profile_id=self.profile_id).get_all_records_columns(filter_by=filter_by,
                                                                                     projection=projection,
                                                                                     sort_by=sort_by,
                                                                                     sort_direction=sort_direction)

            if records:
                df = pd.DataFrame(records)
                df['accession'] = df._id.astype(str)
                df['label'] = df['name']
                df['description'] = ''
                df['server-side'] = True  # ...to request callback to server for resolving item description

        result = list()

        if not df.empty:
            df = df[['accession', 'label', 'description', 'server-side']]
            result = df.to_dict('records')

        return result

    def cg_dependency_lookup(self):
        """
        lookup for cgcore dependent components
        :return:
        """
        from .templatetags import html_tags as htags
        from common.dal.copo_da import CGCore

        result = list()
        df = pd.DataFrame()
        dependent_record_label = 'copo_name'

        if self.accession:
            if isinstance(self.accession, str):
                self.accession = self.accession.split(",")

            object_ids = [ObjectId(x) for x in self.accession if x.strip()]
            records = cursor_to_list(CGCore().get_collection_handle().find({"_id": {"$in": object_ids}}))
            result = list()

            if records:
                for record in records:
                    referenced_field = record.get("dependency_id", str())
                    kwargs = dict()
                    kwargs["referenced_field"] = referenced_field
                    schema = CGCore().get_component_schema(**kwargs)

                    label = record.get(dependent_record_label, str())

                    # modify schema before generating description
                    schema = [x for x in schema if
                              'dependency' in x and x['dependency'] == referenced_field and x.get("show_in_table",
                                                                                                  True)]
                    resolved = htags.resolve_display_data(schema, record)
                    description = self.format_description(resolved)

                    item_dict = dict(accession=str(record["_id"]),
                                     label=label,
                                     description=description)
                    item_dict['server-side'] = True  # ...to request callback to server for resolving item description

                    result.append(item_dict)
        elif self.search_term:
            referenced_field = self.referenced_field
            filter_name = dependent_record_label
            projection = {filter_name: 1}
            filter_by = dict(dependency_id=referenced_field)
            filter_by[filter_name] = {'$regex': self.search_term, "$options": 'i'}

            sort_by = filter_name
            sort_direction = -1

            records = CGCore(profile_id=self.profile_id).get_all_records_columns(filter_by=filter_by,
                                                                                 projection=projection,
                                                                                 sort_by=sort_by,
                                                                                 sort_direction=sort_direction)

            if not records:
                # try getting all records
                del filter_by[filter_name]
                records = CGCore(profile_id=self.profile_id).get_all_records_columns(filter_by=filter_by,
                                                                                     projection=projection,
                                                                                     sort_by=sort_by,
                                                                                     sort_direction=sort_direction)
            if records:
                df = pd.DataFrame(records)
                df['accession'] = df._id.astype(str)
                df['label'] = df[filter_name]
                df['description'] = ''
                df['server-side'] = True  # ...to request callback to server for resolving item description

        if not df.empty:
            df = df[['accession', 'label', 'description', 'server-side']]
            result = df.to_dict('records')

        return result

    def get_isasamples(self):
        """
        lookup for ISA-based (COPO standard) samples
        :return:
        """

        from.templatetags import html_tags as htags
        from common.dal.copo_da import Sample

        df = pd.DataFrame()

        if self.accession:
            if isinstance(self.accession, str):
                self.accession = self.accession.split(",")

            object_ids = [ObjectId(x) for x in self.accession if x.strip()]
            records = cursor_to_list(Sample().get_collection_handle().find({"_id": {"$in": object_ids}}))

            if records:
                df = pd.DataFrame(records)
                df['accession'] = df._id.astype(str)
                df['label'] = df['name']
                df['desc'] = df['accession'].apply(lambda x: htags.generate_attributes("sample", x))
                df['description'] = df['desc'].apply(lambda x: self.format_description(x))
                df['server-side'] = True  # ...to request callback to server for resolving item description

        elif self.search_term:
            projection = dict(name=1)
            filter_by = dict(sample_type="isasample")
            filter_by["name"] = {'$regex': self.search_term, "$options": 'i'}

            sort_by = 'name'
            sort_direction = -1

            records = Sample(profile_id=self.profile_id).get_all_records_columns(filter_by=filter_by,
                                                                                 projection=projection,
                                                                                 sort_by=sort_by,
                                                                                 sort_direction=sort_direction)
            if not records:
                # try getting all records
                del filter_by['name']
                records = Sample(profile_id=self.profile_id).get_all_records_columns(filter_by=filter_by,
                                                                                     projection=projection,
                                                                                     sort_by=sort_by,
                                                                                     sort_direction=sort_direction)
            if records:
                df = pd.DataFrame(records)
                df['accession'] = df._id.astype(str)
                df['label'] = df['name']
                df['description'] = ''
                df['server-side'] = True  # ...to request callback to server for resolving item description

        result = list()

        if not df.empty:
            df = df[['accession', 'label', 'description', 'server-side']]
            result = df.to_dict('records')

        return result

    def get_allsamples(self):
        """
        lookup for all samples irrespective of sample type
        :return:
        """

        from .templatetags import html_tags as htags
        from common.dal.copo_da import Sample

        df = pd.DataFrame()

        if self.accession:
            if isinstance(self.accession, str):
                self.accession = self.accession.split(",")

            object_ids = [ObjectId(x) for x in self.accession if x.strip()]
            records = cursor_to_list(Sample().get_collection_handle().find({"_id": {"$in": object_ids}}))

            if records:
                df = pd.DataFrame(records)
                df['accession'] = df._id.astype(str)
                df['label'] = df['name']
                df['desc'] = df['accession'].apply(lambda x: htags.generate_attributes("sample", x))
                df['description'] = df['desc'].apply(lambda x: self.format_description(x))
                df['server-side'] = True  # ...to request callback to server for resolving item description
        elif self.search_term:
            projection = dict(name=1)
            filter_by = dict()
            filter_by["name"] = {'$regex': self.search_term, "$options": 'i'}

            sort_by = 'name'
            sort_direction = -1

            records = Sample(profile_id=self.profile_id).get_all_records_columns(filter_by=filter_by,
                                                                                 projection=projection,
                                                                                 sort_by=sort_by,
                                                                                 sort_direction=sort_direction)
            if not records:
                # try getting all records
                del filter_by['name']
                records = Sample(profile_id=self.profile_id).get_all_records_columns(filter_by=filter_by,
                                                                                     projection=projection,
                                                                                     sort_by=sort_by,
                                                                                     sort_direction=sort_direction)

            if records:
                df = pd.DataFrame(records)
                df['accession'] = df._id.astype(str)
                df['label'] = df['name']
                df['description'] = ''
                df['server-side'] = True  # ...to request callback to server for resolving item description

        result = list()

        if not df.empty:
            df = df[['accession', 'label', 'description', 'server-side']]
            result = df.to_dict('records')

        return result

    def format_description(self, desc):
        html = """<table style="width:100%">"""
        for col in desc['columns']:
            html += "<tr><td>{}</td>".format(col['title'])
            html += "<td>{}</td>".format(desc['data_set'][col['data']])
            html += "</tr>"
        html += "</table>"

        return html
