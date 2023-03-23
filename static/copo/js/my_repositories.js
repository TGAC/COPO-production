$(document).ready(function () {
    update_display()
    do_boxes()
    $(document).on("click", ".delete", handle_delete)

    $(document).on('click', '.radio', do_boxes)


    $("#repoForm").validator().on("submit", function (e) {
        if (e.isDefaultPrevented()) {
            // handle the invalid form...
        } else {
            e.preventDefault()
            var name = $('#repoForm').find("#name").val()
            var url = $('#repoForm').find("#url").val()
            var apikey = $('#repoForm').find("#apikey").val()
            var type = $("#radioDiv input[type='radio']:checked").val()
            var username = $('#repoForm').find("#username").val()
            var password = $('#repoForm').find("#password").val()
            var data = {"name": name, "url": url, "apikey": apikey, "type": type, "password": password, "username": username}
            csrftoken = $.cookie('csrftoken');
            $.ajax({
                url: "/copo/add_personal_dataverse/",
                method: "POST",
                data: data,
                headers: {
                    'X-CSRFToken': csrftoken
                },

            }).done(function () {
                $("#add_repo_modal").modal("toggle")
                update_display()
            })
        }
    })
})

function do_boxes() {
    var type = $("#radioDiv input[type='radio']:checked").val()
    enable_authentication_boxes()
    if (type == 'dspace') {
        disable_apikey_box()
    } else {
        disable_username_password_boxes()
    }
}

function enable_authentication_boxes() {
    $('#apikey').val('')
    $('#username').val('')
    $('#password').val('')
    $('#apikey').removeAttr('disabled')
    $('#username').removeAttr('disabled')
    $('#password').removeAttr('disabled')
    $('#apikey').attr("data-validate", "true")
    $('#username').attr("data-validate", "true")
    $('#password').attr("data-validate", "true")
    $('#repoForm').validator('update')
}

function disable_username_password_boxes() {
    $('#username').attr("data-validate", "false")
    $('#username').attr('disabled', 'disabled')
    $('#password').attr('data-validate', "false")
    $('#password').attr('disabled', 'disabled')
    $('#repoForm').validator('update')
    $('#repoForm').validator('validate')
}

function disable_apikey_box() {
    $('#apikey').attr('disabled', 'disabled')
    $("#apikey").attr("data-validate", "false")
    $('#repoForm').validator('update')
    $('#repoForm').validator('validate')
}

function update_display() {
    $.ajax({
        url: "/copo/get_personal_dataverses/",
        method: "GET"
    }).done(function (data) {
        var rows
        data = JSON.parse(data)
        if (data.length == 0) {
            rows = rows + "<tr><td colspan='4'>No Repositories Entered</td>"
            $("#repos_table").find("tbody").html(rows)
        } else {
            $(data).each(function (idx, el) {
                rows = rows + "<tr data-repo-id='" + el.id + "'><td>" + el.name + "</td><td>" + el.type + "</td><td>" + el.url + "</td><td><button style=\"margin-left:20px\" class=\"ui delete red icon button\">\n" +
                    "  <i class=\"trash icon\"></i>\n" +
                    "</button></td>"
            })
            $("#repos_table").find("tbody").html(rows)
        }
    })
}

function handle_delete(e) {
    var id = $(e.currentTarget).closest("tr").data("repo-id")
    csrftoken = $.cookie('csrftoken');
    $.ajax({
        url: "/copo/delete_personal_dataverse/",
        method: "POST",
        data: {"repo_id": id},
        headers: {
            'X-CSRFToken': csrftoken
        },

    }).done(function () {
        update_display()
    })
}
