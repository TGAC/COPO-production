from django.core.management import BaseCommand
from Bio import Entrez
import xml.etree.ElementTree as ET
import subprocess
from common.utils.helpers import get_env
import os
import common.dal.sample_da as da
from common.utils.logger import Logger


# The class must be named Command, and subclass BaseCommand
class Command(BaseCommand):
    help = "update taxonomy information of samples - " \
        "provide comma separated biosamples:'new scientific name'"
    Entrez.email = "copo@earlham.ac.uk"

    def __init__(self):
        self.TAXONOMY_FIELDS = ["TAXON_ID", "ORDER_OR_GROUP", "FAMILY", "GENUS",
                                "SCIENTIFIC_NAME", "COMMON_NAME", "TAXON_REMARKS",
                                "INFRASPECIFIC_EPITHET"]
        self.rankdict = {
            "order": "ORDER_OR_GROUP",
            "family": "FAMILY",
            "genus":  "GENUS"
        }
        self.pass_word = get_env('WEBIN_USER_PASSWORD')
        self.user_token = get_env('WEBIN_USER').split("@")[0]
        # 'https://wwwdev.ebi.ac.uk/ena/submit/drop-box/submit/'
        self.ena_service = get_env('ENA_SERVICE')
        self.ena_sample_retrieval = self.ena_service[:-len(
            'submit/')] + "samples/"  # https://devwww.ebi.ac.uk/ena/submit/drop-box/samples/" \

    def add_arguments(self, parser):
        parser.add_argument('samples', type=str)
        parser.add_argument('-barcoding', action='store_true')

    # A command must define handle()
    def handle(self, *args, **options):
        updates_to_make = options['samples'].split(",")
        barcoding = options['barcoding']
        print(updates_to_make)
        d_updates = {}
        for couple in updates_to_make:
            sample = couple.split(":")[0].strip()
            scientific_name = couple.split(":")[1].strip()
            d_updates[sample] = scientific_name
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
            # retrieve new taxonomy information
            scientific_name = d_updates[sample["biosampleAccession"]]
            taxonomyinfo = self.query_taxonomy(scientific_name)
            taxonomy = taxonomyinfo['LineageEx']
            taxon = taxonomyinfo['TaxId']
            scien_name = taxonomyinfo['ScientificName']
            self.update_sampletaxonomy(
                sample['_id'], taxonomy, taxon, scien_name, barcoding)
            if sample.get("sampleDerivedFrom", ""):
                source_biosample = sample.get("sampleDerivedFrom")
            else:
                source_biosample = sample.get("sampleSameAs")
            self.update_specsampletaxonomy(source_biosample, taxon, barcoding)

    def query_taxonomy(self, scientific_name):
        handle = Entrez.esearch(db="Taxonomy", term=scientific_name)
        records = Entrez.read(handle)
        if not records['IdList']:
            print("invalid scientific name %s" % (scientific_name))
            flag = False
        taxon_id = records['IdList'][0]

        handle = Entrez.efetch(db="Taxonomy", id=taxon_id, retmode="xml")
        records = Entrez.read(handle)
        return records[0]

    def update_sampletaxonomy(self, sample, taxonomy, taxon, name, barcoding):
        # update db record
        out = dict()
        for item in taxonomy:
            if item['Rank'] in self.rankdict:
                out[self.rankdict[item['Rank']]] = item['ScientificName']
        out["COMMON_NAME"] = ""
        out["TAXON_REMARKS"] = ""
        out["INFRASPECIFIC_EPITHET"] = ""
        out["TAXON_ID"] = taxon
        out["SCIENTIFIC_NAME"] = name

        oldsample = da.Sample().get_record(sample)
        # for tax_field in self.TAXONOMY_FIELDS:
        #     oldvalue = oldsample["species_list"][0].get(tax_field, "")
        #     newvalue = out[tax_field]
        #     if oldvalue != newvalue:
        #         if barcoding:
        #             da.Sample().record_barcoding_update(tax_field, oldvalue, newvalue, sample)
        #         else:
        #             da.Sample().record_manual_update(tax_field, oldvalue, newvalue, sample)
        da.Sample().update_field("species_list.0", out, sample)

        # query public name (skip this for now)

        # update ENA record
        updatedrecord = da.Sample().get_record(sample)
        # todo retrieve sample from xml
        # retrieve submitted XML for sample
        curl_cmd = "curl -u " + self.user_token + \
                   ':' + self.pass_word + " " + self.ena_sample_retrieval \
                   + updatedrecord['biosampleAccession']
        registered_sample = subprocess.check_output(curl_cmd, shell=True)

        self.update_samplexml(
            registered_sample, out['TAXON_ID'], updatedrecord['biosampleAccession'])

    def update_specsampletaxonomy(self, accession, taxon, barcoding):
        # update db record
        source = da.Source().get_by_field("biosampleAccession", accession)
        assert len(source) == 1
        # if barcoding:
        #     da.Source().record_barcoding_update(
        #         "TAXON_ID", source[0]["TAXON_ID"], taxon, source[0]['_id'])
        # else:
        #     da.Source().record_manual_update(
        #         "TAXON_ID", source[0]["TAXON_ID"], taxon, source[0]['_id'])
        da.Source().update_field("TAXON_ID", taxon, source[0]['_id'])
        # update ENA record
        updatedrecord = da.Source().get_record(source[0]['_id'])
        # retrieve submitted XML for source
        curl_cmd = "curl -u " + self.user_token + \
                   ':' + self.pass_word + " " + self.ena_sample_retrieval \
                   + updatedrecord['biosampleAccession']
        registered_specimen = subprocess.check_output(curl_cmd, shell=True)

        self.update_samplexml(
            registered_specimen, updatedrecord['TAXON_ID'], updatedrecord['biosampleAccession'])

    def modify_sample(self, accession):
        curl_cmd = 'curl -u ' + self.user_token + ':' + self.pass_word \
                   + ' -F "SUBMISSION=@modifysubmission.xml' \
                   + '" -F "SAMPLE=@' \
                   + accession + ".xml" \
                   + '" "' + self.ena_service \
                   + '"'
        try:
            receipt = subprocess.check_output(curl_cmd, shell=True)
            print(receipt)
        except Exception as e:
            message = 'API call error ' + "Submitting xml to ENA via CURL. CURL command is: " + curl_cmd.replace(
                self.pass_word, "xxxxxx")
            Logger().exception(e)
            return False

        os.remove(accession + ".xml")

    def update_samplexml(self, registered_sample, new_taxon, accession):
        # only thing to update in ENA is taxon ID
        doc = ET.fromstring(registered_sample)
        tree = ET.ElementTree(doc)
        name_block = tree.find('SAMPLE').find('SAMPLE_NAME')
        taxon_block = tree.find('SAMPLE').find('SAMPLE_NAME').find('TAXON_ID')
        taxon_block.text = new_taxon
        scname_block = tree.find('SAMPLE').find(
            'SAMPLE_NAME').find('SCIENTIFIC_NAME')
        scname_block.text = " "
        comname_block = tree.find('SAMPLE').find(
            'SAMPLE_NAME').find('COMMON_NAME')
        if comname_block and comname_block.text:
            comname_block.text = " "

        ET.dump(tree)
        tree.write(open(accession + ".xml", 'w'), encoding='unicode')

        self.modify_sample(accession)
