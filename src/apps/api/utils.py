__author__ = 'felix.shaw@tgac.ac.uk - 20/01/2016'

import bson.json_util as jsonb
import json
import pandas as pd
import shortuuid
import uuid
from .views.mapping import get_mapped_result
from common.dal.profile_da import Profile
from common.lookup.lookup import API_RETURN_TEMPLATES
from common.schemas.utils.data_utils import get_export_fields
from django.http import HttpResponse
from django_tools.middlewares import ThreadLocal


# Helpers related to template generation
def get_return_template(type):
    '''
    Method to return a python object representation of the given api template return type
    :param type: a string naming the template type
    :return: an python object representation of the json contained in the template
    '''
    path = API_RETURN_TEMPLATES[type.upper()]
    with open(path) as data_file:
        data = json.load(data_file)
    return data


def extract_to_template(object=None, template=None):
    '''
    Method to examine fields in object and extract those which match the field names in template along with their values
    :param object: the object to search
    :param template: the fields to look for
    :return: the template with the values completed
    '''
    for f in object:
        for t in template:
            if f == t:
                template[t] = object[t]

    return template


def generate_rocrate_person_object(
    df, personlist, person_field_name, prefix, person_map
):
    # items = []
    for people in personlist:
        person_affiliations = (
            df[df[person_field_name] == people][f'{prefix}_AFFILIATION'].unique()[0]
            if f'{prefix}_AFFILIATION' in df.columns
            else str()
        )
        orcid_ids = (
            df[df[person_field_name] == people][f'{prefix}_ORCID_ID'].unique()[0]
            if f'{prefix}_ORCID_ID' in df.columns
            else str()
        )

        person_list = people.split('|')
        person_affiliation_list = person_affiliations.split('|')
        orcid_id_list = orcid_ids.split('|')
        affiliation = ''

        for index, person in enumerate(person_list):
            name = person.strip()
            item = person_map.get(name, dict())
            person_map[name] = item

            if orcid_ids and len(orcid_id_list) > index:
                item['@id'] = 'http://orcid.org/' + orcid_id_list[index].strip()
            else:
                item['@id'] = uuid.uuid4().hex
            item['name'] = name
            item['@type'] = 'Person'

            affiliation_list = item.get('affiliation', list())
            item['affiliation'] = affiliation_list

            # item['role'] = person_field_name
            if person_affiliation_list:
                if len(person_affiliation_list) > index:
                    affiliation = person_affiliation_list[index].strip()
                    if affiliation not in item['affiliation']:
                        item['affiliation'].append(affiliation)
                elif affiliation:
                    if affiliation not in item['affiliation']:
                        item['affiliation'].append(affiliation)

            # items.append(item)
    return person_map


def generate_rocrate_object(request, samples):
    '''
    result_list = []
    manifest_map = dict()
    for samples in data:
        if type(samples) != dict or  'manifest_id' not in samples:
            result_list = ['Not Implemented']
            return result_list
        manifest_id = samples.get('manifest_id','')
        if manifest_id:
            if manifest_id not in manifest_map:
                manifest_map[manifest_id] = []
            manifest_map[manifest_id].append(samples)
    if len(manifest_map.keys()) > 1:
        result_list = ['Not Implemented']
        return result_list
    '''
    rocrate_json = {}
    manifest_id = samples[0].get('manifest_id', '')
    profile_title = samples[0].get('copo_profile_title', '')
    profile_description = Profile().get_description_by_title(profile_title)
    uri = request.build_absolute_uri('/')

    if not manifest_id:
        rocrate_json['error'] = 'Not Implemented'
    else:
        # @type: context
        # for key, samples in manifest_map.items():
        # rocrate_json = {}
        context = [
            'https://w3id.org/ro/crate/1.1/context',
            'https://w3id.org/ro/terms/sample',
            'https://w3id.org/ro/terms/copo',
        ]

        info_dict = {
            'BioSample': 'https://bioschemas.org/BioSample',
            'collector': 'https://bioschemas.org/BioSample#collector',
            'custodian': 'https://bioschemas.org/BioSample#custodian',
            'dwc': 'http://rs.tdwg.org/dwc/terms/',
            'dwciri': 'http://rs.tdwg.org/dwc/iri/',
            'isControl': 'https://bioschemas.org/BioSample#isControl',
            'parentTaxon': 'https://schema.org/parentTaxon',
            'samplingAge': 'https://bioschemas.org/BioSample#samplingAge',
            'taxonomicRange': 'http://schema.org/taxonomicRange',
        }

        context.append(info_dict)
        rocrate_json['@context'] = context
        graph_list = list()

        # @type: CreativeWork
        creativeWork = {'@id': 'ro-crate-metadata.json', '@type': 'CreativeWork'}
        creativeWork['conformsTo'] = {'@id': 'https://w3id.org/ro/crate/1.1'}
        # {'@id':f'{uri}api/manifest/{key}' }
        creativeWork['about'] = {'@id': f'{uri}api/manifest/{manifest_id}/'}
        graph_list.append(creativeWork)

        df = pd.DataFrame(samples)
        dateCreated = df['time_created'].min()
        dateModified = df['time_updated'].max()

        # @type: Person
        # updatedby = df['updated_by'].unique()
        # author = df['created_by'].unique()
        collectedby = df['COLLECTED_BY'].unique()
        coordinator = (
            df['SAMPLE_COORDINATOR'].unique()
            if 'SAMPLE_COORDINATOR' in df.columns
            else []
        )
        perservedby = (
            df['PRESERVED_BY'].unique() if 'PRESERVED_BY' in df.columns else []
        )
        identifiedby = (
            df['IDENTIFIED_BY'].unique() if 'IDENTIFIED_BY' in df.columns else []
        )

        rocrate_person = dict()
        rocrate_person = generate_rocrate_person_object(
            df, collectedby, 'COLLECTED_BY', 'COLLECTOR', rocrate_person
        )
        rocrate_person = generate_rocrate_person_object(
            df, coordinator, 'SAMPLE_COORDINATOR', 'SAMPLE_COORDINATOR', rocrate_person
        )
        rocrate_person = generate_rocrate_person_object(
            df, perservedby, 'PRESERVED_BY', 'PRESERVER', rocrate_person
        )
        rocrate_person = generate_rocrate_person_object(
            df, identifiedby, 'IDENTIFIED_BY', 'IDENTIFIER', rocrate_person
        )

        # @type: Dataset
        # f'{uri}api/manifest/{key}/'
        manifest_item = {
            '@id': f'{uri}api/manifest/{manifest_id}/',
            '@type': 'Dataset',
            'datePublished': dateCreated,
            'name': profile_title,
            'description': profile_description,
            'dateModified': dateModified,
            'license': {'@id': 'https://creativecommons.org/publicdomain/zero/1.0'},
        }
        manifest_item['contributor'] = []
        manifest_item['contributor'].extend(
            {'@id': p['@id']} for p in rocrate_person.values()
        )

        manifest_item['hasPart'] = [
            {
                '@id': (
                    f"http://identifiers.org/biosample:{x.get('biosampleAccession','')}"
                    if x.get('biosampleAccession', '')
                    else f"{uri}api/sample/copo_id/{x['copo_id']}"
                )
            }
            for x in samples
        ]
        manifest_item['taxonomicRange'] = [
            {'@id': f'http://identifiers.org/taxonomy:{x}'}
            for x in df['TAXON_ID'].unique()
        ]
        location_mapping = [
            {f'#place{str(shortuuid.ShortUUID().random(length=10))}': x}
            for x in df['COLLECTION_LOCATION'].unique()
        ]
        manifest_item['location'] = [
            {'@id': k} for element in location_mapping for k, v in element.items()
        ]

        graph_list.append(manifest_item)
        graph_list.extend(rocrate_person.values())

        # @type: Taxon
        for x in df['TAXON_ID'].unique():
            item = {'@id': f'http://identifiers.org/taxonomy:{x}'}
            item['@type'] = 'TAXON'
            item['name'] = (
                df[df['TAXON_ID'] == x]['SCIENTIFIC_NAME'].unique()[0]
                if 'SCIENTIFIC_NAME' in df.columns
                else ''
            )
            # The commented code below is not allowed because it is not
            # present in the context. It is a  URI to be in the context but it is not unique
            item['parentTaxon'] = {
                '@id': f"{uri}api/sample_field/ORDER_OR_GROUP/{df[df['TAXON_ID']== x ]['ORDER_OR_GROUP'].unique()[0]}"
            }
            graph_list.append(item)

        # @type: Place
        lat_prefix = 'LATITUDE'
        long_prefix = 'LONGITUDE'
        latLong_startEnd_lst = [
            f'{lat_prefix}_START',
            f'{lat_prefix}_END',
            f'{long_prefix}_START',
            f'{long_prefix}_END',
        ]

        for element in location_mapping:
            for key, value in element.items():
                item = {'@id': key}
                item['@type'] = 'Place'
                item['name'] = value
                item['latitude'] = (
                    df[df['COLLECTION_LOCATION'] == value]['DECIMAL_LATITUDE'].unique()[
                        0
                    ]
                    if 'DECIMAL_LATITUDE' in df.columns
                    else ''
                )
                item['longitude'] = (
                    df[df['COLLECTION_LOCATION'] == value][
                        'DECIMAL_LONGITUDE'
                    ].unique()[0]
                    if 'DECIMAL_LONGITUDE' in df.columns
                    else ''
                )

                if all(element in df.columns for element in latLong_startEnd_lst):
                    for i in latLong_startEnd_lst:
                        item[i] = (
                            df[df['COLLECTION_LOCATION'] == value][i].unique()[0]
                            if i in df.columns
                            else ''
                        )

                graph_list.append(item)

        # @type: BioSample
        # Function to insert a key, value pair into a dictionary at a specified position/index
        def insert(_dict, obj, pos):
            return {
                k: v
                for k, v in (
                    list(_dict.items())[:pos]
                    + list(obj.items())
                    + list(_dict.items())[pos:]
                )
            }

        for x in samples:
            sample_type = x.get('tol_project', '').upper()
            keys_lst = list(x.keys())
            biosampleAccession = x.get('biosampleAccession', '')

            sample_item = {
                '@id': (
                    f'http://identifiers.org/biosample:{biosampleAccession}'
                    if biosampleAccession
                    else f"{uri}api/sample/copo_id/{x['copo_id']}"
                ),
                '@type': 'BioSample',
            }

            if 'TAXON_ID' in x:
                # sample_item['taxonomicRange'] = {'@id': "http://identifiers.org/taxonomy:{x['TAXON_ID']}"}
                # Get index/position to insert new key, value into sample item dictionary
                index = keys_lst.index('TAXON_ID') + 1
                # Insert new key, value into dictionary at specified position
                x = insert(
                    x,
                    {
                        'taxonomicRange': {
                            '@id': f"https://identifiers.org/taxonomy:{x['TAXON_ID']}"
                        }
                    },
                    index,
                )

            if biosampleAccession:
                sample_item['sameAs'] = {
                    '@id': f"{uri}api/sample/copo_id/{x['copo_id']}"
                }

            for p in (
                'COLLECTOR:COLLECTED_BY',
                'SAMPLE_COORDINATOR:SAMPLE_COORDINATOR',
                'PRESERVER:PRESERVED_BY',
                'IDENTIFIER:IDENTIFIED_BY',
            ):
                pp = p.split(':')
                collectors = x.get(pp[1], '')
                if collectors:
                    # sample_item[pp[0].lower()] = []
                    # Recalculate the list of keys since it has been adjusted since a key, value pair insertion was done
                    keys_lst = list(x.keys())

                    field = ''
                    if pp[0].lower() != 'collector':
                        field = 'custodian'
                        # Get index/position to insert new key, value pair into sample item dictionary
                        index = keys_lst.index(f'{pp[0]}_AFFILIATION') + 1
                    else:
                        field = pp[0].lower()
                        # Get index/position to insert new key, value pair into sample item dictionary
                        index = keys_lst.index(pp[1]) + 1

                    # Insert new key, value into dictionary at specified position
                    x = insert(x, {field: []}, index)

                    for c in collectors.split('|'):
                        collector = rocrate_person.get(c.strip(), dict())
                        if collector:
                            # sample_item[pp[0].lower()].append({'@id': collector['@id']})
                            x[field].append({'@id': collector['@id']})

            export_fields = get_export_fields(component='sample', project=sample_type)
            filtered_x = {
                key: value for key, value in x.items() if key in export_fields
            }

            # Set the rest of the data as additional properties in the sample_item
            sample_item['additionalProperty'] = []
            for key, value in filtered_x.items():
                sample_item['additionalProperty'].append(
                    {'@type': 'PropertyValue', 'name': key, 'value': value}
                )

            # Update sample_item with the filtered item
            # sample_item.update(filtered_x)
            graph_list.append(sample_item)

        rocrate_json['@graph'] = graph_list
        # result_list.append(rocrate_json)
    return rocrate_json


# Output responses
def generate_rocrate_response(request, template):
    '''
        Run Ro-Crate validation using the command line
        Replace <manifest_id> with the actual manifest_id in the URL below
        Install the validator using: $ pip3 install roc-validator
        Validate rocrate: $ rocrate-validator validate <path_to_rocrate>
        e.g. rocrate-validator validate https://copo-project.org/api/manifest/<manifest_id>?return_type=rocrate
    '''
    df = pd.DataFrame(template)
    manifest_ids = df['manifest_id'].unique() if 'manifest_id' in df.columns else []

    if len(manifest_ids) == 1:
        # Generate the rocrate_objs
        rocrate_objs = generate_rocrate_object(request, template)

        return HttpResponse(
            content=json.dumps(rocrate_objs), content_type='application/json'
        )
    return HttpResponse(content='Not Implemented')


def generate_csv_response(standard, template):
    sanitised_standard = standard.replace(' ', '_').replace('/', '-')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename={sanitised_standard}_export.csv'
    )

    df = pd.DataFrame(template)
    df.to_csv(response, index=False)

    return response


def generate_wrapper_response(error=None, num_found=None, template=None):
    wrapper = get_return_template('WRAPPER')

    if error is None:
        if num_found == None:
            wrapper['number_found'] = 0
            if template == None:
                wrapper['number_found'] = 0
            if type(template) == type(list()):
                wrapper['number_found'] = len(template)
            # else:
            #     wrapper['number_found'] = 1
        else:
            wrapper['number_found'] = num_found
        wrapper['data'] = template
        wrapper['status'] = 'OK'
    else:
        wrapper['status'] = 'Error'
        wrapper['error_details'] = error
        wrapper['number_found'] = None
        wrapper['data'] = None

    return wrapper


# Main method for API return
def finish_request(
    template=None, error=None, num_found=None, return_http_response=True
):
    '''
    Method to tidy up data before returning API caller
    :param template: completed template of resource data
    :param error_info: error created if any
    :return: the complete API return
    '''
    request = ThreadLocal.get_current_request()
    return_type = request.GET.get('return_type', 'json').lower()
    standard = request.GET.get('standard', 'tol').lower()

    # Set template with data based on the standard if there is no error and template exists
    if not error and template:
        template = (
            template
            if standard == 'tol'
            else get_mapped_result(standard=standard, template=template, project=str())
        )

    wrapper = generate_wrapper_response(error, num_found, template)
    output = jsonb.dumps(wrapper)

    if return_http_response:
        if return_type == 'csv':
            return generate_csv_response(standard, template)
        elif return_type == 'rocrate':
            return generate_rocrate_response(request, template)
        else:
            return HttpResponse(output, content_type='application/json')
    else:
        return output


# Helper for sorting dictionaries
def sort_dict_list_by_priority(dict_list, export_fields):
    '''
    Sorts a list of dictionaries so that:
    - Uppercase keys remain at the top in their original order
    - Lowercase camel case keys are alphabetically sorted and placed below

    Args:
        dict_list (list[dict]): A list of dictionaries to be sorted.
        export_fields (list[str]): A list specifying the priority order of uppercase keys.

    Returns:
        list[dict]: A new list of sorted dictionaries.
    '''
    # Retrieve fields that are uppercase
    export_fields_uppercase = [field for field in export_fields if field.isupper()]

    def sort_fields_prioritised(data):
        # Preserve uppercase key order based on export_fields
        uppercase_keys = [
            k for k in export_fields_uppercase if k in data and k.isupper()
        ]
        # uppercase_keys = [k for k in data if k.isupper()]
        lowercase_keys = sorted(k for k in data if not k.isupper())

        sorted_keys = uppercase_keys + lowercase_keys
        return {key: data[key] for key in sorted_keys}

    # Apply sorting to each dictionary in the list
    return [sort_fields_prioritised(d) for d in dict_list]
