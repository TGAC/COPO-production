$(document).ready(function () {
    $(document).on("click", "#auto_annotate_btn", automate)
})


function automate(evt) {
    $("#automate_modal").modal("show").draggable()
    var id = $("#file_id").val()
    // get number of columns
    $.getJSON('/copo/automate_num_cols/', {"file_id": id}, function (data) {
        var row = "<tr id='termrow'>"
        var blankrow = "<tr>"
        var termrow = "<tr>"
        $(data.headers).each(function (idx, el) {
            row = row + "<td id='" + "term_" + idx + "'>" + el + "</td>"
            blankrow = blankrow + '<td id="' + "loader_" + idx + '" style="height: 65px; background-color: white"><div class="ui tiny text centered inline loader">working</div></td>'
            termrow = termrow + '<td id=termrow" style="height: 65px; background-color: white"></td>'
        })
        blankrow = blankrow + "</tr>"
        row = row + "</tr>"
        termrow = termrow + "</tr>"
        $("#automate_modal").find(".modal-body").find(".automation_table").empty()
        $("#automate_modal").find(".modal-body").find(".automation_table").append(blankrow).append(row).append(termrow)
        term_lookup()
    })
}

function term_lookup() {
    var terms = $("#termrow").children()
    $(terms).each(function (idx, el) {
        var term = $(el).html()
        var loader_id = "#loader_" + idx
        $($(loader_id).children()[0]).addClass("active")
        $.ajax({
            url: '/copo/term_lookup/',
            data: {'loader_id':loader_id, "index": idx, "q": term},
            type: 'GET',
            contentType: false,
            dataType: 'json'
        }).done(function (data) {
            let id = data.loader_id
            $(id).hide()
            $($("#termrow").children()[data.index]).html(data.term.label)
            console.log(data)
        })
    })
}

function update_template() {
    return false
}