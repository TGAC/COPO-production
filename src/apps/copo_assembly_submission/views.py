from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from common.dal.copo_da import Submission
from common.utils import helpers 
from django.http import HttpResponse
from .forms import AssemblyForm
from .utils import EnaAssembly   

@login_required()
def ena_assembly(request, profile_id):
    is_error = False
    request.session["profile_id"] = profile_id
    study_accession = ""
    sample_accession = []

    existing_sub = Submission().get_records_by_field("profile_id", profile_id)
    if existing_sub:
        existing_accessions = existing_sub[0].get("accessions", "")
        if existing_accessions:
            study = existing_accessions.get("project", "")
            if study:
                if isinstance(study, dict):
                    study_accession = study.get("accession", "")
                elif isinstance(study, list):
                    study_accession = study[0].get("accession", "")
            else:
                study_accession = ""
            samples = existing_accessions.get("sample", "")
            if samples:
                for sample in samples:
                    if sample.get("sample_accession", ""):
                        sample_accession.append(sample.get("sample_accession", ""))

    if request.method == 'POST':
        # return render(request, "copo/ena_assembly.html", {"profile_id": profile_id, "form": [], "hide_form": False})
        form = AssemblyForm(request.POST, request.FILES, sample_accession=sample_accession)
        if form.is_valid():
            helpers.notify_frontend(data={"profile_id": profile_id},
                            msg="Intitialising Assembly Submission",
                            action="info",
                            html_id="assembly_info")
            # this is a dict
            formdata = form.cleaned_data
            files = request.FILES
            if not files:
                helpers.notify_assembly_status(data={"profile_id": profile_id},
                                msg='At least one assembly file is required',
                                action="error",
                                html_id="assembly_info")
                is_error = True
            else:
                # uploading files to folder in COPO
                helpers.notify_frontend(data={"profile_id": profile_id}, msg="", action="show",
                                html_id="loading_span")
                EnaAssembly.upload_assembly_files(files)
                sub_result = EnaAssembly.validate_assembly(formdata, profile_id)
                if sub_result.get("error", ""):
                    helpers.notify_assembly_status(data={"profile_id": profile_id},
                                    msg=sub_result.get("error", ""),
                                    action="error",
                                    html_id="assembly_info")
                    is_error = True
                    #messages.error(request,sub_result)
                else:
                    helpers.notify_assembly_status(data={"profile_id": profile_id},
                                    msg="The assembly has been created with accession: " + sub_result.get("accession", "Success"),
                                    action="info",
                                    html_id="assembly_info")
                # form = AssemblyForm(study_accession=study_accession, sample_accession=sample_accession)
                #return HttpResponse()
        else:
            helpers.notify_assembly_status(data={"profile_id": profile_id},
                msg=str(form.errors),
                action="error",
                html_id="assembly_info")
            is_error = True
            #messages.error(request, form.errors)
        
    else:
        
        # todo I'm probably out of time to do this, but we need to account -maybe?- for a situation in which we have
        # multiple assemblies submitted as part of the same profile, probably the structure in the database need to
        # change slightly so that it is possible for us to link accession and relative sample
        # eg. accessions: {assembly: {accession:,alias:, SAMPLE}} in copo_da add_assembly_accession
        #
        # pass the accessions as "study_accession" and "sample_ccession" to the form so that they are
        # set authomatically and cannot be changed by the user
        form = AssemblyForm(study_accession=study_accession, sample_accession=sample_accession,
                            #initial={"assemblyname": "jdklsad", "coverage": 1, "program": "jiwjd", "platform": "kkfjoep", "mingaplength": 10,
                            #         "description": "jfksjkdlfs"}
                             )
        return render(request, "copo/ena_assembly.html", {"profile_id": profile_id, "form": form, "hide_form": False})
    if is_error:
        return HttpResponse(content="Validation Error" , status=400)
    return HttpResponse(status=200)