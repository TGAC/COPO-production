var ols_annotator = {

    // start: function (app) {
    //     app.notify("Hello, world!");
    //
    // },

    getEditorExtension: function getEditorExtension(options) {


        return function editorExtension(editor) {

            this.constructor = function (options) {
                //options.defaultFields = false;
                //Widget.call(this, options);
            }
            editor.addField({
                type: "input",
                label: "Search",
                id: "search_term_text_box",
                load: function (field, annotation) {
                    $(field).find("input").addClass("form-control ui icon input")

                }
            })
            editor.addField({
                type: "select",
                label: "Ontology",
                class: "select",
                load: function (field, annotation) {
                    options = $(document).data("ontologies")
                    $(field).find("select").addClass("form-control")

                    $(field).find("select").append("<option class='annotator_option'>All Ontologies</option>")
                    for (option in options) {
                        var option_html = $("<option/>", {
                            class: 'annotator_option',
                            html: options[option].config.title
                        })
                        $(option_html).data("id", options[option].ontologyId)
                        $(field).find("select").append(option_html)
                    }
                }
            })
            editor.addField({
                type: "div",
                id: "search_results",
                submit: function (field, annotation) {
                    annotation.data = $("#search_results").data("annotation")
                    annotation.file_id = $("#file_id").val()
                }
            })

        };
    }

}

