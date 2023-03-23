var handle = 0;
var transfer_tokens = {};
var animation_objects = {};

$(document).ready(function () {
    //handle repo upload: sends selected file to the repo via aspera
    $("body").on('click', 'a.repo-upload', function (event) {
        event.preventDefault();
        do_repo_upload(event);
    });


    function do_repo_upload(event) {
        var data_file_id = $($(event.target)).parent().attr("target-id");
        var ena_collection_id = $("#ena_collection_id").val();
        var study_id = $("#study_id").val();

        var csrftoken = $.cookie('csrftoken');

        $.ajax(
            {
                url: "/copo/upload_to_dropbox/",
                type: "POST",
                headers: {'X-CSRFToken': csrftoken},
                data: {
                    'task': 'initiate_transfer',
                    'ena_collection_id': ena_collection_id,
                    'study_id': study_id,
                    'data_file_id': data_file_id
                },
                success: function (data) {
                    //keep track of this transfer token
                    transfer_tokens[data.initiate_data.transfer_token] = data_file_id;

                    //set up progress animation for token, hence target element
                    progress_animation(data.initiate_data.transfer_token);

                    if (handle == 0) {
                        start_process();
                    }

                },
                error: function () {
                    alert("Could not initiate transfer!");
                }
            });
    }

    function transfer_progress() {
        // needless continuing if there are no tokens to serve
        var count = 0;
        $.each(transfer_tokens, function (index, value) {
            count++;
        });

        if (count == 0) {
            terminate_process();
            return false;
        }

        var tokens = JSON.stringify(transfer_tokens);

        var csrftoken = $.cookie('csrftoken');

        $.ajax(
            {
                url: "/copo/upload_to_dropbox/",
                type: "POST",
                headers: {'X-CSRFToken': csrftoken},
                data: {
                    'task': 'transfer_progress',
                    'tokens': tokens
                },
                success: function (data) {
                    progress_display(data.progress_data);
                },
                error: function () {
                    alert('no data returned')
                }
            });
    }

    function progress_animation(transfer_token) {
        var elem = "uploadprog_"+transfer_tokens[transfer_token];

        var circle = new ProgressBar.Circle('#' + elem, {
            color: '#80B280',
            strokeWidth: 5,
            trailWidth: 5,
            easing: 'easeInOut',
            duration: 200,
            text: {
                className: 'progress-circularum-label',
                style: {
                    color: '#163657'
                }
            }
        });

        animation_objects[transfer_token] = circle;
        $('#'+elem).show();
    }

    function start_process() {
        handle = setInterval(transfer_progress, 1000);
    }

    function terminate_process() {
        clearInterval(handle);
        handle = 0;
    }


    function progress_display(progress_data) {
        progress_data.forEach(function (progress) {

            var elem = "uploadprog_"+transfer_tokens[progress.transfer_token];
            var progressPercent = progress.pct_completed;

            if(progress.transfer_status == "success") {
                // doing this here, ...since I am slow with handling the 100% completion mark server-side
                progressPercent = 100;
            }

            animation_objects[progress.transfer_token].animate(progressPercent / 100, function () {
                animation_objects[progress.transfer_token].setText(progressPercent + "%");
            });

            //remove from token if completed or aborted...
            if (progress.transfer_status != "transferring") {
                delete transfer_tokens[progress.transfer_token];
            }
        });
    }

}); //end of document.ready