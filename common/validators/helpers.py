import subprocess
import json
from common.validators.validation_messages import MESSAGES as msg
import datetime
from common.utils.logger import Logger
l = Logger()

def validate_date(date_text):
    try:
        datetime.datetime.strptime(date_text, '%Y-%m-%d')
    except ValueError:
        raise ValueError("Incorrect data format, should be YYYY-MM-DD")
    todayis = datetime.date.today()
    enteredtime = datetime.datetime.strptime(date_text, '%Y-%m-%d').date()
    try:
        assert todayis > enteredtime
    except AssertionError:
        raise AssertionError("Incorrect date entered: date is in the future")

def check_taxon_ena_submittable(taxon, by="id"):
    errors = []
    receipt = None
    taxinfo = None
    curl_cmd = None
    if by == "id":
        curl_cmd = "curl " + "https://www.ebi.ac.uk/ena/taxonomy/rest/tax-id/" + taxon
    elif by == "binomial":
        curl_cmd = "curl " + "https://www.ebi.ac.uk/ena/taxonomy/rest/scientific-name/" + taxon.replace(" ", "%20")
    try:
        receipt = subprocess.check_output(curl_cmd, shell=True)
        print(receipt)
        if receipt.decode("utf-8") == "":
            errors.append(
                "ENA returned no results for Scientific Name " + taxon + ". This could mean that the taxon id is incorrect, or ENA maybe down.")
            return errors
        taxinfo = json.loads(receipt.decode("utf-8"))
        if by == "id":
            if taxinfo["submittable"] != 'true':
                errors.append("TAXON_ID " + taxon + " is not submittable to ENA")
            if taxinfo["rank"] not in ["species", "subspecies"]:
                errors.append("TAXON_ID " + taxon + " is not a 'species' or 'subspecies' level entity.")
            if taxinfo["binomial"] == "false":  
                errors.append(msg['validation_msg_invalid_binomial_name'] % (taxon, taxinfo["scientificName"]))    
        elif by == "binomial":
            if taxinfo[0]["submittable"] != 'true':
                errors.append("TAXON_ID " + taxon + " is not submittable to ENA")
            if taxinfo[0]["rank"] not in ["species", "subspecies"]:
                errors.append("TAXON_ID " + taxon + " is not a 'species' or 'subspecies' level entity.")
            if taxinfo["binomial"] == "false":
                errors.append(msg['validation_msg_invalid_binomial_name'] % (taxon, taxinfo["scientificName"]))    
    except Exception as e:
        l.exception(e)
        if receipt:
            if receipt.decode("utf-8") == "No results.":
                errors.append(
                    "ENA returned no results for Scientific Name " + taxon)
            else:
                try:
                    errors.append(
                        "ENA returned - " + taxinfo.get("error", "no error returned") + " - for TAXON_ID " + taxon)
                except (NameError, AttributeError):
                    errors.append(
                        "ENA returned - " + receipt.decode("utf-8") + " - for TAXON_ID " + taxon)
        else:
            errors.append(msg['validation_msg_not_submittable_taxon'] % (taxon))
    return errors