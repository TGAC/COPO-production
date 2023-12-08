MESSAGES = {
    'validation_message_wrong_specimen_taxon_pair': 'Invalid SPECIMEN_ID and TAXON pair: at row <strong>%s</strong>, '
                                                    'SPECIMEN_ID <strong>%s</strong> has already been used for a '
                                                    'specimen with TAXON_ID <strong>%s</strong>',
    'validation_msg_conflicted_permit_filename_values': 'Conflicted data: <strong>%s</strong> in column '
                                                        '<strong>%s</strong> at row <strong>%s</strong>'
                                                        'for SPECIMEN_ID <strong>%s</strong>.',
    'validation_msg_duplicate_rack_or_plate_id': 'Duplicate RACK_OR_PLATE_ID found. Data: '
                                                 '<strong>%s</strong> already exists in COPO',                                                       
    'validation_msg_duplicate_tube_or_well_id': 'Duplicate TUBE_OR_WELL_ID found. Data: '
                                                '<strong>%s</strong> already exists in COPO',
    'validation_msg_duplicate_tube_or_well_id_in_copo': 'Duplicate RACK_OR_PLATE_ID and TUBE_OR_WELL_ID already exist in '
                                                        'COPO: <strong>%s</strong>',
    'validation_msg_duplicate_without_target': 'Duplicate RACK_OR_PLATE_ID and TUBE_OR_WELL_ID <strong>%s</strong> '
                                               'found without TARGET in SYMBIONT field. One of these duplicates '
                                               'must be listed as TARGET',
    'validation_msg_error_decimal_latlong_or_latlong_start_end_all_contains_a_value': 'All fields (<strong>DECIMAL_LATITUDE/DECIMAL_LONGITUDE</strong> '
                                                                                      'and <strong>LATITUDE_START/LATITUDE_END/LONGITUDE_START/LONGITUDE_END</strong>) '
                                                                                      'cannot have a decimal value at '
                                                                                      'row <strong>%s</strong>',
    'validation_msg_error_decimal_latlong_or_latlong_start_end_all_not_collected': 'All fields (<strong>DECIMAL_LATITUDE/DECIMAL_LONGITUDE</strong> '
                                                                                   'and <strong>LATITUDE_START/LATITUDE_END/LONGITUDE_START/LONGITUDE_END</strong>) '
                                                                                   'are <strong>NOT_COLLECTED</strong> '
                                                                                   'at row <strong>%s</strong>',
    'validation_msg_error_decimal_latlong_or_latlong_start_end_missing_decimal_latlong': 'Missing <strong>DECIMAL_LATITUDE/DECIMAL_LONGITUDE</strong> '
                                                                                         'field at row <strong>%s</strong>',
    'validation_msg_error_decimal_latlong_or_latlong_start_end_missing_start_end': 'Missing <strong>LATITUDE_START/LATITUDE_END</strong> '
                                                                                   'field or <strong>LONGITUDE_START/LONGITUDE_END</strong> '
                                                                                   'field at row <strong>%s</strong>',
    'validation_msg_error_decimal_latlong_or_latlong_start_end_missing_value': 'Any of <strong>DECIMAL_LATITUDE/DECIMAL_LONGITUDE</strong> '
                                                                               'field or any <strong>LATITUDE_START/LATITUDE_END/LONGITUDE_START/LONGITUDE_END</strong> '
                                                                               'field cannot be empty at row '
                                                                               '<strong>%s</strong>',
    'validation_msg_error_decimal_latlong_or_latlong_start_end_mixed_value': '<strong>DECIMAL_LATITUDE/DECIMAL_LONGITUDE</strong> '
                                                                             'and <strong>LATITUDE_START/LATITUDE_END/LONGITUDE_START/LONGITUDE_END</strong> '
                                                                             'field cannot contain a decimal value and '
                                                                             'have <strong>NOT_COLLECTED</strong> '
                                                                             'at the same time at row <strong>%s</strong>',
    'validation_msg_error_decimal_latlong_or_latlong_start_end_not_collected_mixed_value': '<strong>NOT_COLLECTED</strong> '
                                                                                           'cannot be the value  for '
                                                                                           'both <strong>DECIMAL_LATITUDE/DECIMAL_LONGITUDE</strong> '
                                                                                           'field and <strong>LATITUDE_START/LATITUDE_END/LONGITUDE_START/LONGITUDE_END</strong> '
                                                                                           'field at row '
                                                                                           '<strong>%s</strong>',
    'validation_msg_error_specimen_regex': 'Invalid data: <strong>%s</strong> in column <strong>%s</strong> at '
                                           'row <strong>%s</strong>. Expected format for %s <strong>%s</strong> '
                                           'is <strong>%s</strong> followed by 7 digits.',
    'validation_msg_error_specimen_regex_dtol': 'Invalid data: <strong>%s</strong> in column <strong>%s</strong> at '
                                                'row <strong>%s</strong>. Expected format for %s <strong>%s</strong> '
                                                'is <strong>%s</strong> followed by <strong>%s</strong>.',
    'validation_msg_future_date': 'Invalid date: <strong>%s</strong> in column <strong>%s</strong> at row '
                                  '<strong>%s</strong>. Date cannot be in the future.',
    'validation_msg_invalid_associated_tol_project': 'Invalid associated profile type for profile, '
                                                     '<strong>%s</strong>. Expected value should include '
                                                     '<strong>Population Genomics (POP_GENOMICS)</strong> and '
                                                     '<strong>Biodiversity Genomics Europe (BGE)</strong> if value of column '
                                                     '<strong>PURPOSE_OF_SPECIMEN</strong> is '
                                                     '<strong>RESEQUENCING</strong>. And vice versa. Please update/edit the '
                                                     'associated profile type for the profile then, reupload the '
                                                     'manifest.',
                                    
    'validation_msg_invalid_binomial_name': "For the TAXON_ID,  <strong>%s</strong>, the scientific name, <strong>%s</strong>, is not a valid binomial name. "
                                            "Please contact <a href='mailto:ena-asg@ebi.ac.uk'>ena-asg@ebi.ac.uk</a> or "
                                            "<a href='mailto:ena-dtol@ebi.ac.uk'>ena-dtol@ebi.ac.uk</a> or "
                                            "<a href='mailto:ena-bge@ebi.ac.uk'>ena-bge@ebi.ac.uk</a> to request assistance for this taxonomy.",
    'validation_msg_invalid_data': 'Invalid data: <strong>%s</strong> in column <strong>%s</strong> at row '
                                   '<strong>%s</strong>. Allowed values are <strong>%s</strong>',
    'validation_msg_invalid_date': 'Invalid date: <strong>%s</strong> in column <strong>%s</strong> at row '
                                   '<strong>%s</strong>. Dates should be in format YYYY-MM-DD',
    'validation_msg_invalid_link': 'Invalid URL: <strong>%s</strong> in column <strong>%s</strong> at row '
                                   '<strong>%s</strong>. The entered value is not a valid URL.',
    'validation_msg_invalid_list': "Invalid data: <strong>%s</strong> in column <strong>%s</strong> at row "
                                   "<strong>%s</strong>. If this is a location, start with the Country, adding more "
                                   "specific details separated with '|'. See list of allowed Country entries at "
                                   "<a href='https://www.ebi.ac.uk/ena/browser/view/ERC000053'>https://www.ebi.ac.uk/ena/browser/view/ERC000053</a>",
    'validation_msg_invalid_permit_filename': 'Invalid data: <strong>%s</strong> in column <strong>%s</strong> at '
                                              'row <strong>%s</strong>. Expected value should be <strong>%s</strong>',
    'validation_msg_invalid_purpose_of_specimen': 'Invalid data: <strong>%s</strong> in column '
                                                  '<strong>PURPOSE_OF_SPECIMEN</strong> at row <strong>%s</strong>. '
                                                  'Expected value should be <strong>RESEQUENCING</strong> '
                                                  'since associated profile types are '
                                                  '<strong>Population Genomics (POP_GENOMICS)</strong> '
                                                  'and <strong>Biodiversity Genomics Europe (BGE)</strong>.',
    'validation_msg_invalid_rank': 'Invalid scientific name or taxon ID: row <strong>%s</strong> - rank of scientific '
                                   'name and taxon id should be species.',
    'validation_msg_invalid_taxon': "TAXON_ID <strong>%s</strong> at row <strong>%s</strong> is invalid. Check "
                                    "SCIENTIFIC_NAME and TAXON_ID match at NCBI <a href='https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi'>here</a> "
                                    "or <a href='https://www.ncbi.nlm.nih.gov/Taxonomy/TaxIdentifier/tax_identifier.cgi'>here</a>. "
                                    "Please refer to the ASG/DTOL/ERGA SOP. Contact "
                                    "<a href='mailto:ena-asg@ebi.ac.uk'>ena-asg@ebi.ac.uk</a> or "
                                    "<a href='mailto:ena-dtol@ebi.ac.uk'>ena-dtol@ebi.ac.uk</a> or "
                                    "<a href='mailto:ena-bge@ebi.ac.uk'>ena-bge@ebi.ac.uk</a> for assistance.",
    'validation_msg_invalid_taxonomy': 'Invalid data: <strong>%s</strong> in column <strong>%s</strong> at row '
                                       '<strong>%s</strong>. Expected value is <strong>%s</strong>',
    'validation_msg_isupdate': '<strong>UPDATE</strong>: <strong>%s</strong> has already been uploaded. COPO will '
                               'perform an update.',
    'validation_msg_missing_data': 'Missing data detected in column <strong>%s</strong> at row <strong>%s</strong>. '
                                   'All required fields must have a value. There must be no empty rows. Values of '
                                   '<strong>%s</strong> are allowed, unless otherwise stated in the SOP.',
    'validation_msg_missing_data_ena_seq': 'Missing data detected in column <strong>%s</strong> at row '
                                           '<strong>%s</strong>. All fields must have a value.',
    'validation_msg_missing_optional_field_value': 'Warning: Missing <strong>%s</strong> at row <strong>%s</strong>. '
                                                   'COPO will substitute with default value, <strong>%s</strong>.',
    'validation_msg_missing_scientific_name': 'Missing data detected in column <strong>%s</strong> at row '
                                              '<strong>%s</strong>. All required fields must have a value. There must '
                                              'be no empty rows.',
    'validation_msg_missing_symbiont': 'Missing data detected in column <strong>%s</strong> at row '
                                       '<strong>%s</strong>. All required fields must have a value. There must be '
                                       'no empty rows. Values of <strong>%s</strong> are allowed.',
    'validation_msg_missing_taxon': 'Missing TAXON_ID at row <strong>%s</strong>. For <strong>%s</strong> TAXON_ID '
                                    'should be <strong>%s</strong>',
    'validation_msg_multiple_permit_filenames_with_same_specimen_id': 'Conflicting data: <strong>%s</strong> in column '
                                                                      '<strong>%s</strong> | column <strong>%s</strong> '
                                                                      'for SPECIMEN_ID <strong>%s</strong>',
    'validation_msg_multiple_targets_with_same_id': 'Multiple Targets found for RACK_OR_PLATE_ID/TUBE_OR_WELL_ID: '
                                                    '<strong>%s</strong>',
    'validation_msg_not_submittable_taxon': "TAXON_ID <strong>%s</strong> is not 'submittable' to ENA. Please see "
                                            "<a href='https://ena-docs.readthedocs.io/en/latest/faq/taxonomy_requests.html#creating-taxon-requests'>here</a> "
                                            "and contact <a href='mailto:ena-asg@ebi.ac.uk'>ena-asg@ebi.ac.uk</a> or "
                                            "<a href='mailto:ena-dtol@ebi.ac.uk'>ena-dtol@ebi.ac.uk</a> or "
                                            "<a href='mailto:ena-bge@ebi.ac.uk'>ena-bge@ebi.ac.uk</a> to request an "
                                            "informal placeholder species name. Please also refer to the ASG/DTOL/ERGA SOP.",
    'validation_msg_original_field_missing': 'Missing data: ORIGINAL_GEOGRAPHIC_LOCATION missing at row '
                                             '<strong>%s</strong>. If ORIGINAL_COLLECTION_DATE is provided, '
                                             'ORIGINAL_GEOGRAPHIC_LOCATION must also be provided.',
    'validation_msg_orphaned_symbiont': 'Symbiont(s) found with TUBE_OR_WELL_ID: <strong>%s</strong> has no associated '
                                        'Target',
    'validation_msg_overwrite_symbionts': '<strong>Warning: COPO will overwrite any <strong>SYMBIONT</strong> field '
                                          'to match the corresponding TARGET, unless otherwise stated in the SOP</br>'
                                          '</strong><strong>%s</strong>. Date cannot be in the future.',
    'validation_msg_paired_file_error': 'Field indicates that files should be paired, 2 filenames and 2 checksums are allowed '
                                        'at row <strong>%s</strong>',
    'validation_msg_rack_tube_both_na': 'NOT_APPLICABLE, NOT_PROVIDED or NOT_COLLECTED value found in both RACK_OR_PLATE_ID '
                                        'and TUBE_OR_WELL_ID at row <strong>%s</strong>.',
    'validation_msg_rack_or_tube_contains_a_slash': 'Slash found in column, <strong>RACK_OR_PLATE_ID</strong>, or column, <strong>TUBE_OR_WELL_ID</strong>. '
                                                    'Expected value should not contain any slashes (i.e. no <strong>/</strong> or <strong>\</strong>).',
    'validation_msg_rack_or_tube_is_na': 'NOT_APPLICABLE, NOT_PROVIDED, NOT_COLLECTED or "NA" value found in column, RACK_OR_PLATE_ID '
                                        'or column, TUBE_OR_WELL_ID at row <strong>%s</strong>.',
    'validation_msg_single_file_error': 'Field indicates that files and checksum should be single, but multiple filenames or checksums were '
                                        'provided at row <strong>%s</strong>',
    'validation_msg_string_in_taxon_id': 'Non numeric TAXON_ID found in row <strong>%s</strong>. Taxon ids must be '
                                         'integer',
    'validation_msg_synonym': 'Invalid scientific name: <strong>%s</strong> at row <strong>%s</strong> is a synonym '
                              'of <strong>%s</strong>. Please provide the official scientific name.',
    'validation_msg_used_whole_organism': "Duplicate SPECIMEN_ID and ORGANISM_PART <strong>'WHOLE ORGANISM'</strong> "
                                          "pair found for specimen: <strong>%s</strong>",
    'validation_msg_warning_barcoding': 'Warning: Overwriting PLATE_ID_FOR_BARCODING, TUBE_OR_WELL_ID_FOR_BARCODING, '
                                        'TISSUE_FOR_BARCODING and BARCODE_PLATE_PRESERVATIVE at row <strong>%s</strong> '
                                        'because TISSUE_REMOVED_FOR_BARCODING is <strong>%s</strong>',
    'validation_msg_warning_na_value_voucher': "Warning: <strong>%s</strong> in column <strong>%s</strong> at row "
                                               "<strong>%s</strong>. ERGA requires to voucher your sample, if you "
                                               "don't, be aware the sequencing may not continue until you have provided "
                                               "<strong>%s</strong>.",
    'validation_msg_warning_racktube_format': "Warning: <strong>%s</strong> in column <strong>%s</strong> at row "
                                              "<strong>%s</strong> does not look like  FluidX format. "
                                              "Please check that this is correct before clicking 'Finish'.",
    'validation_msg_warning_regex_gen': "Warning: <strong>%s</strong> <strong>%s</strong> at row <strong>%s</strong> "
                                        "is not in the expected format. Please check this is correct before clicking 'Finish'.",
    'validation_msg_warning_update_submitted_sample': "Warning: <strong>%s</strong> has been submitted with biosample "
                                                      "accession <strong>%s</strong>. Please check this is correct "
                                                      "before clicking 'Finish'.",
    'validation_warning_field': 'Missing <strong>%s</strong>: row <strong>%s</strong> - <strong>%s</strong> for '
                                '<strong>%s</strong> will be filled with <strong>%s</strong>',
    'validation_warning_synonym': 'Synonym warning: <strong>%s</strong> at row <strong>%s</strong> is a synonym of '
                                  '<strong>%s</strong>. COPO will substitute the official scientific name.'
}
