from typing import Any
from django.core.management.base import BaseCommand
from src.apps.copo_core.models import SequencingCentre
from django.contrib.auth.models import User


# The class must be named Command, and subclass BaseCommand
class Command(BaseCommand):
    # Show this when the user types help
    help = "Add sequencing centres to the database, which will be used to direct notifications to the correct email addresses"

    def __init__(self):
        super().__init__()

    def handle(self, *args, **options):
        self.stdout.write("Removing Existing Sequencing Centres")
        SequencingCentre().remove_all_sequencing_centres()
        self.stdout.write("Adding Sequencing Centres")
        earlham = SequencingCentre().create_sequencing_centre(name="EARLHAM",
                                                              description="Earlham Institute",
                                                              label="Earlham Institute")
        sanger = SequencingCentre().create_sequencing_centre(name="SANGER",
                                                             description="Sanger Institute",
                                                             label="Wellcome Sanger Institute")
        self.stdout.write("Sequencing Centres Added")
        records = SequencingCentre.objects.all()

        for record in records:
            self.stdout.write(record.name)
