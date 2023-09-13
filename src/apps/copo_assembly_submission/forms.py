from django import forms


class AssemblyForm(forms.Form):

    def __init__(self, *args, sample_accession=None, study_accession=None, assembly=None, ecs_files=None, **kwargs):
        super(AssemblyForm, self).__init__(initial=assembly, *args, **kwargs)

        self.fields['study'].widget.attrs['readonly'] = True
        if study_accession and not assembly:
            self.fields['study'].initial = study_accession
        if sample_accession:
            tuplelist = []
            for x in sample_accession:
                tuplelist.append((x, x))
            self.fields['sample'].choices = tuplelist
            self.fields['sample_text'].widget.attrs['hidden'] = ''
            self.fields['sample_text'].label = ''
        else:
            self.fields['sample'].required = False
            self.fields['sample'].hidden = True
            pass
            # todo this bit does not really work, a drop down menu shows up no matter what (altough empty and optional)
            # so it works but it's an aesthetic problem
            # self.fields['sample'].hidden = True
            # self.fields['sample'].label = ''
            # self.fields['sample'].required = False

        if assembly:
            self.fields["study"].disabled = True
            self.fields["sample"].disabled = True
            self.fields["id"].initial =  str(assembly["_id"])

        files_choices = [("", 'None')]
        if ecs_files:
            files_choices.extend([(x,x) for x in ecs_files])
        
        file_fields = ["fasta", "flatfile", "agp", "chromosome_list", "unlocalised_list"]
        for field in file_fields:
            self.fields[field].initial = None
            self.fields[field].widget.attrs['readonly'] = True  
            self.fields[field].choices = files_choices


    # fields from ENA assembly documentation
    study = forms.CharField(label="STUDY",
                            widget=forms.TextInput(attrs={'placeholder': 'Study accession'}))
    sample = forms.ChoiceField(label="SAMPLE")
    sample_text = forms.CharField(label="SAMPLE", widget=forms.TextInput(attrs={'placeholder': 'Sample accession'}), required=False)
    assemblyname = forms.CharField(label="ASSEMBLYNAME", widget=forms.TextInput(attrs={'placeholder': 'Unique '
                                                                                                      'assembly name,'
                                                                                                      ' user-provided'}))
    assembly_type = forms.ChoiceField(label="ASSEMBLY_TYPE", choices=[('clone', 'clone'), ('isolate', 'isolate')])
    coverage = forms.FloatField(label="COVERAGE", widget=forms.TextInput(attrs={'placeholder': 'The estimated depth of '
                                                                                               'sequencing coverage'}))
    program = forms.CharField(label="PROGRAM", widget=forms.TextInput(attrs={'placeholder': 'The assembly program'}))
    platform = forms.CharField(label="PLATFORM", widget=forms.TextInput(attrs={'placeholder': 'The sequencing '
                                                                                              'platform, '
                                                                                              'or comma-separated '
                                                                                              'list of platforms'}))
    mingaplength = forms.IntegerField(label="MINGAPLENGTH", required=False,
                                      widget=forms.TextInput(
                                          attrs={'placeholder': 'Minimum length of consecutive Ns to '
                                                                'be considered a gap'}))
    moleculetype = forms.ChoiceField(label="MOLECULETYPE", required=False,
                                     choices=[('genomic DNA', 'genomic DNA'), ('genomic RNA', 'genomic RNA'),
                                              ("viral cRNA", "viral cRNA")])
    description = forms.CharField(label="DESCRIPTION", required=False,
                                  widget=forms.Textarea(attrs={'placeholder': 'Free text description of the genome '
                                                                              'assembly'}))
    run_ref = forms.CharField(label="RUN_REF", required=False, widget=forms.TextInput(
        attrs={'placeholder': 'Comma separated list of run accession(s)'}))
    
    fasta = forms.ChoiceField(label="FASTA", required=False )
    flatfile = forms.ChoiceField(label="FLATFILE", required=False )
    agp = forms.ChoiceField(label="AGP", required=False)
    chromosome_list = forms.ChoiceField(label="CHROMOSOME_LIST", required=False)
    unlocalised_list = forms.ChoiceField(label="UNLOCALISED_LIST", required=False)
    #fasta = forms.FileField(label="FASTA", required=False, widget=forms.FileInput(
    #    #attrs={'accept': '.fasta.gz, .fas.gz, .fsa.gz, fna.gz, .fa.gz, .fasta.bz2, .fas.bz2, .fsa.bz2, .fna.bz2, .fa.bz2'}
    #     ))
    id = forms.CharField(label="ID", required=False, widget=forms.HiddenInput)
