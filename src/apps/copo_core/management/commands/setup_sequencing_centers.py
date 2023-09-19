from typing import Any
from django.core.management.base import BaseCommand
from src.apps.copo_core.models import SequencingCenter
from django.contrib.auth.models import User


# The class must be named Command, and subclass BaseCommand
class Command(BaseCommand):
    # Show this when the user types help
    help = "Add sequencing centers to the database, which will be used to direct notifications to the correct email addresses"

    def __init__(self):
        super().__init__()

    def handle(self, *args, **options):
        self.stdout.write("Removing Existing Sequencing Centers")
        SequencingCenter().remove_all_sequencing_centers()
        self.stdout.write("Adding Sequencing Centers")
        earlham = SequencingCenter().create_sequencing_center(name="EARLHAM",
                                                              description="Earlham Institute",
                                                              label="Earlham Institute")
        sanger = SequencingCenter().create_sequencing_center(name="SANGER",
                                                             description="Sanger Institute",
                                                             label="Wellcome Sanger Institute")
        self.stdout.write("Sequencing Centers Added")
        records = SequencingCenter.objects.all()

        for record in records:
            self.stdout.write(record.name)