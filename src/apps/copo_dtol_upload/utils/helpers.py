import json
from urllib.parse import urljoin
import requests
from common.utils.logger import Logger
from common.schema_versions.lookup.dtol_lookups import API_KEY
from common.lookup.copo_enums import *
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django_tools.middlewares import ThreadLocal
from common.utils import helpers

def get_group_membership_asString():
    r = ThreadLocal.get_current_request()
    gps = r.user.groups.all()
    gps = [str(g) for g in gps]
    return gps


def make_tax_from_sample(s):
    out = dict()
    out["SYMBIONT"] = "symbiont"
    out["TAXON_ID"] = s["TAXON_ID"]
    out["ORDER_OR_GROUP"] = s["ORDER_OR_GROUP"]
    out["FAMILY"] = s["FAMILY"]
    out["GENUS"] = s["GENUS"]
    out["SCIENTIFIC_NAME"] = s["SCIENTIFIC_NAME"]
    out["INFRASPECIFIC_EPITHET"] = s["INFRASPECIFIC_EPITHET"]
    out["CULTURE_OR_STRAIN_ID"] = s["CULTURE_OR_STRAIN_ID"]
    out["COMMON_NAME"] = s["COMMON_NAME"]
    out["TAXON_REMARKS"] = s["TAXON_REMARKS"]
    out["RACK_OR_PLATE_ID"] = s["RACK_OR_PLATE_ID"]
    out["TUBE_OR_WELL_ID"] = s["TUBE_OR_WELL_ID"]
    for el in out:
        out[el] = str(out[el]).strip()
    return out


public_name_service = helpers.get_env('PUBLIC_NAME_SERVICE')
l = Logger()

"""
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
        elif by == "binomial":
            if taxinfo[0]["submittable"] != 'true':
                errors.append("TAXON_ID " + taxon + " is not submittable to ENA")
            if taxinfo[0]["rank"] not in ["species", "subspecies"]:
                errors.append("TAXON_ID " + taxon + " is not a 'species' or 'subspecies' level entity.")
    except Exception as e:
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
"""

"""
def create_barcoding_spreadsheet():
    # get barcoding fields
    s = helpers.json_to_pytype(lk.WIZARD_FILES["sample_details"])

    # to get all elements with version starting with bc
    # fields = jp.match('$.properties[?(@.specifications[*]~".*bc.*" & @.required=="true")].versions[0]', s)

    barcode_fields = jp.match(
        '$.properties[?(@.specifications[*] == "bc" & @.required=="true")].versions['
        '0]',
        s)
    amplicon_fields = jp.match(
        '$.properties[?(@.specifications[*] == "bc_amp" & @.required=="true")].versions['
        '0]',
        s)

    wb = Workbook()
    sheet_id = wb.get_sheet_by_name("Sheet")
    wb.remove_sheet(sheet_id)
    wb.create_sheet("Specimens")
    wb.create_sheet("Amplicons")

    spec = wb.worksheets[0]
    for idx, f in enumerate(barcode_fields):
        spec.cell(row=1, column=idx + 1).value = f

    amp = wb.worksheets[1]
    for idx, f in enumerate(amplicon_fields):
        amp.cell(row=1, column=idx + 1).value = f

    for sheet in wb.worksheets:
        for idx, column in enumerate(sheet.columns):
            cell = sheet.cell(column=idx + 1, row=1)
            sheet.column_dimensions[get_column_letter(idx + 1)].width = len(cell.value) + 5

    return wb
"""

def query_public_name_service(sample_list):
    headers = {"api-key": API_KEY}
    url = urljoin(public_name_service, 'tol-ids')  # public-name
    l.log("name service urls: " + url, type=Logtype.FILE)
    try:
        r = requests.post(url=url, json=sample_list, headers=headers, verify=False)
        if r.status_code == 200:
            resp = json.loads(r.content)
            print(resp)
        else:
            # in the case there is a network issue, just return an empty dict
            resp = {}
            l.error('Name service response status code: ' + str(r.status_code) + ' ' + r.text)
        l.log("name service response: " + str(resp), type=Logtype.FILE)
        return resp
    except Exception as e:
        l.log("PUBLIC NAME SERVER ERROR: " + str(e), type=Logtype.FILE)
        l.exception(e)
        return {}

def notify_frontend(action="message", msg=str(), data={}, html_id="", profile_id="", group_name='dtol_status'):
    """
        function notifies client changes in Sample creation status
        :param profile_id:
        :param action:
        :param msg:
        :return:
    """
    # type points to the object type which will be passed to the socket and is a method defined in consumer.py
    event = {"type": "msg", "action": action, "message": msg, "data": data, "html_id": html_id}
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        group_name,
        event
    )
    return True

