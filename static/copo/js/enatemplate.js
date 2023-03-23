var formURL = "";
var csrftoken = "";

$(document).ready(function () {

    var all = $(".ena-form-details").map(function () {
        var elemName = this.id.split("-");
        elemName = elemName[elemName.length-1];
        this.innerHTML = get_element_details(elemName);
    }).get();

    function get_element_details(elemName) {
        return "This is a placeholder for "+elemName+" details."
    }

}); //end of document.ready