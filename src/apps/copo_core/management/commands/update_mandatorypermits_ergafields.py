from django.core.management import BaseCommand
import common.dal.copo_da as da


# The class must be named Command, and subclass BaseCommand
class Command(BaseCommand):
    help = "update pilot ERGA samples to rename *MANDATORY fields" \
        "with *REQUIRED to comply with version 2.4 updates, keeping old fields too"

    def __init__(self):
        self.TO_UPDATE_FIELDS = {"ETHICS_PERMITS_MANDATORY": "ETHICS_PERMITS_REQUIRED", "SAMPLING_PERMITS_MANDATORY":
                                 "SAMPLING_PERMITS_REQUIRED",
                                 "NAGOYA_PERMITS_MANDATORY": "NAGOYA_PERMITS_REQUIRED"}

    # A command must define handle()
    def handle(self, *args, **options):
        samples_to_update = da.Sample().get_by_project_and_field(
            "ERGA", "manifest_version", ["pilot"])
        for sample in samples_to_update:
            print(sample.get("_id", ""))
            for field in self.TO_UPDATE_FIELDS:
                da.Sample().update_field(
                    self.TO_UPDATE_FIELDS[field], sample.get(field), sample['_id'])
