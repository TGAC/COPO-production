from django.core.management import BaseCommand

from common.dal import copo_da as da


# The class must be named Command, and subclass BaseCommand
class Command(BaseCommand):
    # Show this when the user types help
    help = "if samples are stuck on 'processing' state for some reason, set their status back to pending"

    def __init__(self):
        super().__init__()

    def add_arguments(self, parser):
        parser.add_argument('manifest_id', type=str)

    # A command must define handle()
    def handle(self, *args, **options):
        manifest_id = options["manifest_id"]
        fromdb = da.handle_dict["sample"].count_documents({"manifest_id": manifest_id, "status": "processing"})
        print("samples stuck: " + str(fromdb))
        fromdb = da.handle_dict["sample"].update_many({"manifest_id": manifest_id, "status": "processing"},
                                                      {"$set": {"status": "pending"}})
        print("samples unstuck: " + str(fromdb.modified_count))
        print("done")
