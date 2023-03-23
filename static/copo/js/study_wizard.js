/**
 * felix.shaw@tgac.ac.uk - 22/09/15.
 */

$(document).ready(function () {
    $('#next_wiz').on('click', next_step);
    $('#prev_wiz').on('click', prev_step);
});

function handle_click(file_id) {

    process_stage(true, false);
    /*
    if ($('#wizard').find('section').length == 0) {

    }
    else {
        $('#filesAssignModal').modal('show')
    }
    */
}

function next_step() {
    //process_stage(false)

    var current_steps = $('#wizard').find('section').length;
    var total_steps;

    try {
        total_steps = $('#wizard').data('num_steps')
    }
    catch (Error) {
        total_steps = 0
    }
    if ($('#wizard').steps('getCurrentIndex') == total_steps - 1 && current_steps == total_steps) {
        // carousel is full and we are at the end
        process_stage(false, true)
    }
    else if (current_steps >= total_steps) {
        // carousel is full but we are not at the end, so save but don't retrieve new stage
        process_stage(false, false)
    }
    else {
        // save and get next stage
        process_stage(true, false)
    }

}

function process_stage(get_new_stage, last_stage) {
    var study_type = $('#study_type').val();
    var study_id = $('#study_id').val();
    var datafile_id = $('#wizard_file_id').val();
    var prev_step_id;
    var prev_question;
    var current_answer = '';
    var current_step;
    var process_stage_url = $('#process_stage_url').val();
    try {
        current_step = $('#wizard').steps('getCurrentStep');
        prev_question = $(current_step).data('step_id');
        if (prev_question == undefined) {
            prev_question = $(current_step.content).find("input, select").attr("id")
        }
    }
    catch (Error) {
        current_step = undefined;
        prev_question = ''
    }

    if (current_step != undefined) {
        current_answer = $('section:visible').find('.input-copo').val()
    }


    data_dict = {
        'datafile_id': datafile_id,
        'study_id': study_id,
        'answer': current_answer,
        'study_type': study_type,
        'prev_question': prev_question
    };

    data_dict.last = last_stage;

    $.ajax({
        type: 'get',
        url: process_stage_url,
        dataType: 'json',
        data: data_dict
    }).done(function (d) {
        $('#wizard').data('num_steps', d.num_steps);
        if (last_stage) {
            $('#wizard').data('num_steps', d.num_steps);
            $('#filesAssignModal').modal('hide')
        }
        else if (d.detail.length > 1) {

            var last_step = '';
            if (get_new_stage) {
                $(d.detail).each(function (key, value) {
                    console.log(key + " " + value);
                    $('#wizard').steps('add', {
                        title: value.title,
                        content: value.element
                    });
                    last_step = value.id
                })
            }

            $('#filesAssignModal').modal('show');
            while ($('#wizard').steps("next"));
            var current_step = $('#wizard').steps('getCurrentStep');
            $(current_step).data('step_id', last_step)
        }
        else {
            if (get_new_stage) {
                if (d.detail.constructor === Array) {
                    $('#wizard').steps('add', {
                        title: d.detail[0].title,
                        content: d.detail[0].element
                    });
                }
                else{
                    $('#wizard').steps('add', {
                        title: d.detail.title,
                        content: d.detail.element
                    });
                }
            }


            var num_steps = $('#wizard').find('section').length;
            while (num_steps > 1 && $('#wizard').steps('next')) {
            }
            var current_step = $('#wizard').steps('getCurrentStep');
            $(current_step).data('step_id', d.detail.id);
            $('.ontology-term').css('color', 'red');
            $('#filesAssignModal').modal('show')
        }
    })
}

function prev_step() {
    $('#wizard').steps('previous')
}
