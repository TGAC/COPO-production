function get_upload_box_html(box_id, panel_id){

    var html = '<div class="row">'
                    +'<div class="col-sm-12 col-md-12 col-lg-12">'
                    + '<div class="panel panel-primary">'
                                            + '<div class="panel-heading">'
                                                + '<h3 class="panel-title">Upload</h3>'
                                                    + '<span class="pull-right clickable panel-collapsed"><i class="glyphicon glyphicon-plus"></i></span>'
                                                    + '<input type="hidden" name="panel_id" value="' + panel_id + '">'
                                            + '</div>'
                                            + '<div class="panel-body" style="display: block;">'
                                                + '<div class="row">'
                                                    + '<div class="col-lg-12 col-md-12 col-sm-12">'
                                                        + '<form id="ena_ff" class="form-inline">'
                                                            + '<div class="col-lg-4 col-md-4 col-sm-4">'
                                                            + '<input type="hidden" value="1bjfdDlnVmicd1QULojIs0yzd9TpAJ3a" name="csrfmiddlewaretoken">'
                                                            + '<div class="form-group">'

                                                                + '<label for="select_file_type">File Type</label>'
                                                                + '<select id="select_file_type" name="select_file_type" class="form-control upload_input">'
                                                                    + '<option selected="" value=""></option>'
                                                                    + '<option value="fastq">fastq</option>'
                                                                    + '<option value="bam">bam</option>'
                                                                    + '<option value="sam">sam</option>'
                                                                    + '<option value="cram">cram</option>'
                                                                    + '<option value="PacBio_HDF5">PacBio HDF5</option>'
                                                                    + '<option value="OxfordNanopore_native">Oxford Nanopore'
                                                                        + 'native'
                                                                    + '</option>'
                                                                    + '<option value="srf">srf</option>'
                                                                    + '<option value="sff">sff</option>'
                                                                    + '<option value="CompleteGenomics_native">Complete'
                                                                        + 'Genomics'
                                                                    + '</option>'
                                                                + '</select>'
                                                            + '</div></div>'
                                                            + '<div class="col-lg-4 col-md-4 col-sm-4">'
                                                            + '<div class="form-group">'
                                                                + '<label for="input_library_name">Library Name</label>'
                                                                + '<input type="text" placeholder="Library Name" id="input_library_name" name="input_library_name" class="form-control upload_input">'
                                                            + '</div>'
                                                            + '</div>'
                                                            + '<div class="col-lg-4 col-md-4 col-sm-4">'
                                                            + '<div class="form-group">'
                                                                + '<label for="select_sample_ref">Sample Type</label>'
                                                                + '<select placeholder="Sample Type" type="text" id="select_sample_ref" name="select_sample_ref" class="form-control upload_input"></select>'
                                                            + '</div>'
                                                            +'</div>'
                                                        + '</form>'
                                                    + '</div>'
                                                + '</div>'
                                                + '<div class="row">'
                                                    + '<div class="col-sm-12 col-md-12 col-lg-12">'
                                                        + '<div class="file_type_warning"></div>'
                                                    + '</div>'
                                                + '</div>'
                                                + '<div class="row">'
                                                    + '<div class="col-sm-12 col-md-12 col-lg-12">'
                                                        + '<div class="file_status_label"></div>'

                                                    + '</div>'
                                                + '</div>'
                                                + '<div class="row">'
                                                    + '<div class="col-sm-9 col-md-9 col-lg-9">'

                                                    + '</div>'
                                                    + '<div class="col-sm-3 col-md-3 col-lg-3">'
                                                        + '<form action="/rest/receive_data_file_chunked/" method="POST" id="upload_' + box_id + '" enctype="multipart/form-data">'
                                                            + '<input type="hidden" value="" name="csrfmiddlewaretoken">'
                                                                     + '<span class="btn btn-success fileinput-button vertical-center" id="upload_files_button">'
                                                                        + '<i class="glyphicon glyphicon-plus"></i>'
                                                                        + '<span>Select files...</span>'
                                                                        + '<input type="file" multiple="" onchange="get_chunk_size(event)" id="file_upload" name="file">'
                                                                        + '<input type="hidden" id="upload_id" value="" name="upload_id">'
                                                                        + '<input type="hidden" name="panel_ordering" value="' + box_id + '"/>'
                                                                        + '<input type="hidden" name="exp_id" value=""/>'
                                                                    + '</span>'
                                                        + '</form>'
                                                    + '</div>'

                                                + '</div>'
                                            + '</div>'
                                        + '</div>'
                                    + '</div>'

                                + '</div>';

     return html
 }


 function get_files_table(files){
    str = "<h4>Existing Files for Group</h4>";
    str += "<table id='exp_data_table'>";
    str += "<tr><th>File Name</th><th>Size</th><th>md5</th><th>Delete</th></tr>";
    panel_id = '';
    for(file in files){

        file = files[file];
        console.log(file.panel_id);
        if(file.panel_id != panel_id){
            str += '<tr><td></td><td></td><td></td></tr>'
        }
        //store the data modal id to check if there should be a break in the table next time
        panel_id = file.panel_id;
        str += '<tr><td>' + file.name + '</td>' +
        '<td>' + file.size + '</td>' +
        '<td>' + file.md5 + '</td>' +
        '<td class="delete_cell text-center" data-file_id="' + file.id + '">' +
        '<span class="glyphicon glyphicon-remove-sign"></span></td></tr>'
    }
    str += '</table>';
    return str
 }




function generate_uid(){

    //generate semi-random uid style hash with very low probability of collision
    x = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random()*16|0, v = c == 'x' ? r : (r&0x3|0x8);
    return v.toString(16);
    });
    return x
 }