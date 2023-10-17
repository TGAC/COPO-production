from django.core.management import BaseCommand
from src.apps.copo_dtol_submission.utils.Dtol_Submission import populate_source_fields, \
    build_specimen_sample_xml, build_submission_xml, submit_biosample

import common.dal.copo_da as da


# The class must be named Command, and subclass BaseCommand
class Command(BaseCommand):
    # Show this when the user types help
    help = "to force creation of specimen level biosamples" \
           " if it failed and left orphaned samples. Pass samples" \
           "as comma separated"

    def __init__(self):
        super().__init__()

    def add_arguments(self, parser):
        parser.add_argument('samples', type=str)

    # A command must define handle()
    def handle(self, *args, **options):
        sample_list = options['samples'].split(",")
        print(sample_list)
        # retrieve sample from db
        samplesinddb = da.Sample().get_by_biosample_ids(sample_list)
        for sam in samplesinddb:
            # create source
            specimen_obj_fields = {"SPECIMEN_ID": sam["SPECIMEN_ID"],
                                   "TAXON_ID": sam["species_list"][0]["TAXON_ID"],
                                   "sample_type": "dtol_specimen", "profile_id": sam['profile_id']}
            da.Source().save_record(auto_fields={}, **specimen_obj_fields)
            specimen_obj_fields = populate_source_fields(sam)
            sour = da.Source().get_by_specimen(sam["SPECIMEN_ID"])[0]
            da.Source().add_fields(specimen_obj_fields, str(sour['_id']))
            # submit specimen level biosample
            sour = da.Source().get_by_specimen(sam["SPECIMEN_ID"])
            assert len(sour) == 1
            sour = sour[0]
            build_specimen_sample_xml(sour)
            build_submission_xml(str(sour['_id']), release=True)
            accessions = submit_biosample(
                str(sour['_id']), da.Source(), "", type="source")
            print(accessions)
            specimen_accession = da.Source().get_specimen_biosample(sam["SPECIMEN_ID"])[0].get("biosampleAccession",
                                                                                               "")

            # add accessions to source and sample
            if sam['ORGANISM_PART'] == "WHOLE_ORGANISM":
                da.Sample().update_field("sampleSameAs",
                                         specimen_accession, sam['_id'])
            else:
                da.Sample().update_field('sampleDerivedFrom',
                                         specimen_accession, sam['_id'])
