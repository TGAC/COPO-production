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
        sanger = SequencingCentre().create_sequencing_centre(name="SANGER",
                                                             description="SANGER INSTITUTE",
                                                             label="SANGER INSTITUTE")
        earlham = SequencingCentre().create_sequencing_centre(name="EI",
                                                              description="EARLHAM INSTITUTE",
                                                              label="EARLHAM INSTITUTE")

        SequencingCentre().create_sequencing_centre(name="CNAG",
                                                             description="CENTRO NACIONAL DE ANÁLISIS GENÓMICO ",
                                                             label="CENTRO NACIONAL DE ANÁLISIS GENÓMICO ")

        SequencingCentre().create_sequencing_centre(name="SCILIFE",
                                                             description="SCILIFELAB",
                                                             label="SCILIFELAB")
        
        SequencingCentre().create_sequencing_centre(name="WGGC",
                                                             description="WEST GERMAN GENOME CENTRE",
                                                             label="WEST GERMAN GENOME CENTRE")
        SequencingCentre().create_sequencing_centre(name="NCCT",
                                                             description="NGS COMPETENCE CENTER TÜBINGEN",
                                                             label="NGS COMPETENCE CENTER TÜBINGEN")
        SequencingCentre().create_sequencing_centre(name="FGCZ",
                                                             description="FUNCTIONAL GENOMIC CENTER ZURICH",
                                                             label="FUNCTIONAL GENOMIC CENTER ZURICH")
        SequencingCentre().create_sequencing_centre(name="GENOSCOPE",
                                                             description="GENOSCOPE",
                                                             label="GENOSCOPE")
        SequencingCentre().create_sequencing_centre(name="GTF",
                                                             description="LAUSANNE GENOMIC TECHNOLOGIES FACILITY",
                                                             label="LAUSANNE GENOMIC TECHNOLOGIES FACILITY")
        SequencingCentre().create_sequencing_centre(name="BIDGEN",
                                                             description="DNA SEQUENCING AND GENOMICS LABORATORY, HELSINKI GENOMICS CORE FACILITY",
                                                             label="DNA SEQUENCING AND GENOMICS LABORATORY, HELSINKI GENOMICS CORE FACILITY")
        SequencingCentre().create_sequencing_centre(name="NGS",
                                                             description="NGS BERN",
                                                             label="NGS BERN")
        SequencingCentre().create_sequencing_centre(name="NCS",
                                                             description="NORWEGIAN SEQUENCING CENTRE",
                                                             label="NORWEGIAN SEQUENCING CENTRE")
        SequencingCentre().create_sequencing_centre(name="BARI",
                                                             description="UNIVERSITY OF BARI",
                                                             label="UNIVERSITY OF BARI")
        SequencingCentre().create_sequencing_centre(name="UNIFI",
                                                             description="UNIVERSITY OF FLORENCE",
                                                             label="UNIVERSITY OF FLORENCE")
        SequencingCentre().create_sequencing_centre(name="NSF",
                                                             description="NEUROMICS SUPPORT FACILITY, UANTWERP, VIB",
                                                             label="NEUROMICS SUPPORT FACILITY, UANTWERP, VIB")
        SequencingCentre().create_sequencing_centre(name="SVARDAL",
                                                             description="SVARDAL LAB, ANTWERP",
                                                             label="SVARDAL LAB, ANTWERP")
        SequencingCentre().create_sequencing_centre(name="HANSEN",
                                                             description="HANSEN LAB, DENMARK",
                                                             label="HANSEN LAB, DENMARK")         
        SequencingCentre().create_sequencing_centre(name="LIB",
                                                             description="LEIBNIZ INSTITUTE FOR THE ANALYSIS OF BIODIVERSITY CHANGE, MUSEUM KOENIG, BONN",
                                                             label="LEIBNIZ INSTITUTE FOR THE ANALYSIS OF BIODIVERSITY CHANGE, MUSEUM KOENIG, BONN")        
        SequencingCentre().create_sequencing_centre(name="PARTNER",
                                                             description="INDUSTRY PARTNER",
                                                             label="INDUSTRY PARTNER")        
        SequencingCentre().create_sequencing_centre(name="OTHER",
                                                             description="Other_ERGA_Associated_GAL",
                                                             label="Other_ERGA_Associated_GAL")                                     

        self.stdout.write("Sequencing Centres Added")
        records = SequencingCentre.objects.all()

        for record in records:
            self.stdout.write(record.name)
