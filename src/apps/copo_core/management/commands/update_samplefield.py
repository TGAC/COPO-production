from django.core.management import BaseCommand
from Bio import Entrez
from src.apps.copo_dtol_submission.utils.Dtol_Submission import build_specimen_sample_xml,\
    build_bundle_sample_xml, update_bundle_sample_xml
import subprocess
from common.utils import helpers
import os
from common.schema_versions.lookup.dtol_lookups import DTOL_ENA_MAPPINGS
import common.dal.sample_da as da


# The class must be named Command, and subclass BaseCommand
class Command(BaseCommand):
    help = "update metadata of samples - " \
        "provide comma separated biosamples:field:new_value"
    Entrez.email = "ei.copo@earlham.ac.uk"

    def __init__(self):
        self.TAXONOMY_FIELDS = ["TAXON_ID", "ORDER_OR_GROUP", "FAMILY", "GENUS",
                                "SCIENTIFIC_NAME", "COMMON_NAME", "TAXON_REMARKS",
                                "INFRASPECIFIC_EPITHET"]
        self.rankdict = {
            "order": "ORDER_OR_GROUP",
            "family": "FAMILY",
            "genus":  "GENUS"
        }
        self.pass_word = helpers.get_env('WEBIN_USER_PASSWORD')
        self.user_token = helpers.get_env('WEBIN_USER').split("@")[0]
        # 'https://wwwdev.ebi.ac.uk/ena/submit/drop-box/submit/'
        self.ena_service = helpers.get_env('ENA_SERVICE')
        self.ena_sample_retrieval = self.ena_service[:-len(
            'submit/')] + "samples/"  # https://devwww.ebi.ac.uk/ena/submit/drop-box/samples/" \

    def add_arguments(self, parser):
        parser.add_argument('samples', type=str)

    # A command must define handle()
    def handle(self, *args, **options):
        updates_to_make = options['samples'].split(",")
        print(updates_to_make)
        d_updates = {}
        for update in updates_to_make:
            assert len(update.split(":")) == 3
            sample = update.split(":")[0].strip()
            field = update.split(":")[1].strip()
            value = update.split(":")[2].strip()
            if sample not in d_updates:
                d_updates[sample] = {}
            d_updates[sample][field] = value
        # retrieve sample from db
        print(type(list(d_updates.keys())))
        print(list(d_updates.keys()))
        samplesindb = da.Sample().get_by_biosample_ids(list(d_updates.keys()))
        if len(samplesindb) < len(list(d_updates.keys())):
            print(
                "**********************************************************************************")
            print("one or more samples couldn't be found")
            found_accessions = [sample.get("biosampleAccession")
                                for sample in samplesindb]
            diff = [x for x in list(d_updates.keys())
                    if x not in found_accessions]
            for element in diff:
                print(element, "may be a Source")
            print(
                "**********************************************************************************")
        for sample in samplesindb:
            for field in d_updates[sample['biosampleAccession']]:
                value = d_updates[sample['biosampleAccession']][field]
                oldvalue = da.Sample().get_record(sample['_id']).get(field, "")

                # Update sample and record change in the 'AuditCollection'
                da.Sample().update_field(field, value, sample['_id'])

            # if there's source update it
            if sample.get("sampleDerivedFrom", ""):
                source_biosample = sample.get("sampleDerivedFrom")
            elif sample.get("sampleSameAs", ""):
                source_biosample = sample.get("sampleSameAs")
            else:
                source_biosample = ""
            if source_biosample:
                sourceindb = da.Source().get_by_field("biosampleAccession", source_biosample)
                assert len(sourceindb) == 1
                for field in d_updates[sample['biosampleAccession']]:
                    # only update in source fields that are there -ENA submittable- and not organism part
                    # unique handling of COLLECTION_LOCATION
                    if field == "COLLECTION_LOCATION":
                        value = d_updates[sample['biosampleAccession']][field]
                    elif field != "ORGANISM_PART" and DTOL_ENA_MAPPINGS.get(field, ""):
                        value = d_updates[sample['biosampleAccession']][field]

                    # Update source and record change in the 'AuditCollection'
                    da.Source().update_field(
                        field, value, sourceindb[0]['_id'])
            # if fields are submitted to ENA update them
            print(d_updates[sample['biosampleAccession']])
            print(list(d_updates[sample['biosampleAccession']].keys()))
            flag = False
            for field in list(d_updates[sample['biosampleAccession']].keys()):
                # TODO - this may also need to catch cases where update field is Voucher ID or biobanking_id
                if DTOL_ENA_MAPPINGS.get(field, "") or field == "COLLECTION_LOCATION":
                    flag = True
            if flag:
                self.update_sample(sample['_id'])
                if source_biosample:
                    self.update_source(sourceindb[0]['_id'])

    def update_sample(self, sample):
        # update ENA record
        updatedrecord = da.Sample().get_record(sample)
        # retrieve submitted XML for sample
        curl_cmd = "curl -u " + self.user_token + \
                   ':' + self.pass_word + " " + self.ena_sample_retrieval \
                   + updatedrecord['biosampleAccession']
        registered_sample = subprocess.check_output(curl_cmd, shell=True)

        # self.update_samplexml(registered_sample, updatedrecord['biosampleAccession'])
        build_bundle_sample_xml(str(updatedrecord['_id']))
        update_bundle_sample_xml(
            [updatedrecord['_id']], "bundle_" + str(updatedrecord['_id']) + ".xml")
        print(updatedrecord['_id'])
        self.modify_sample(updatedrecord['_id'])

    def update_source(self, source):
        # update ENA record
        updatedrecord = da.Source().get_record(source)
        # retrieve submitted XML for sample
        curl_cmd = "curl -u " + self.user_token + \
                   ':' + self.pass_word + " " + self.ena_sample_retrieval \
                   + updatedrecord['biosampleAccession']
        registered_source = subprocess.check_output(curl_cmd, shell=True)

        # self.update_samplexml(registered_source, updatedrecord['biosampleAccession'])
        build_specimen_sample_xml(updatedrecord)
        self.modify_sample(updatedrecord['_id'])

    def modify_sample(self, id):
        fileis = "bundle_" + str(id) + ".xml"
        curl_cmd = 'curl -u ' + self.user_token + ':' + self.pass_word \
                   + ' -F "SUBMISSION=@modifysubmission.xml' \
                   + '" -F "SAMPLE=@' \
                   + fileis \
                   + '" "' + self.ena_service \
                   + '"'
        try:
            receipt = subprocess.check_output(curl_cmd, shell=True)
            print(receipt)
        except Exception as e:
            message = 'API call error ' + "Submitting xml to ENA via CURL. CURL command is: " + curl_cmd.replace(
                self.pass_word, "xxxxxx")
            print(message)
            return False

        os.remove(fileis)

    '''def update_samplexml(self, registered_sample, accession):
        #only thing to update in ENA is taxon ID #TODO change this function
        doc = ET.fromstring(registered_sample)
        tree = ET.ElementTree(doc)


        ET.dump(tree)
        tree.write(open(accession + ".xml", 'w'), encoding='unicode')

        self.modify_sample(accession)'''
