// FS - 03/10/19
// For javascript relating to pdf annotations

$(document).ready(function () {
    // get latest list of ontologies from OLS
    get_ontologies_data()
    // setup.sh and init Annotator
    var app = new annotator.App();
    app.include(annotator.ui.main, {
        element: document.getElementById("text-area"),
        editorExtensions: [
            // add ols_annotator which contains custom fields for the annotator window
            ols_annotator.getEditorExtension({defaultFields: false}),

        ],
        viewerExtensions: []
    });


    app.include(annotator.storage.http, {
        headers: {'X-CSRFToken': $.cookie('csrftoken')},
        prefix: '/copo'
    });

    var additional = function () {
        return {
            beforeAnnotationCreated: function (ann) {

            },
            annotationCreated: function (ann) {
                refresh_text_annotations()
            },
            annotationUpdated: function (ann) {
                refresh_text_annotations()
            },
            start: function (ann) {
            }
        };
    };
    app.include(annotator.ui.filter.standalone)
    app.include(additional)
    app.start().then(function () {
        var file_id = $("#file_id").val()
        app.annotations.load({"file_id": file_id});

    });

    $(document).on("click", ".annotation_term", scroll_to_element)
    $(document).on("mouseover", ".annotation_term", function () {
            $(this).closest(".panel").addClass("selectedAnnotation")
        }
    )

    function scroll_to_element(e) {
        var annotation_id = $(e.currentTarget).data("data")._id
        var element = document.querySelector('[data-annotation-id="' + annotation_id + '"]');
        $(".annotator-hl-active").removeClass("annotator-hl-active")
        $(element).addClass("annotator-hl-active")
        console.log($(element).position().top + 40)
        $("#text-area").scrollTop($("#text-area").scrollTop() + $(element).position().top - 100)
    }

    function get_ontologies_data() {
        $.ajax({
            url: '/rest/get_ontologies/',
            method: 'GET',
            dataType: 'json'
        }).done(function (d) {
            $(document).data("ontologies", d)
        })
    }
})


