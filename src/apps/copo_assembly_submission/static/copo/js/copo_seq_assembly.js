$(document).ready(function () {
  var uid = document.location.href;
  uid = uid.split('/');
  uid = uid[uid.length - 2];
  var wsprotocol = 'ws://';
  var s3socket;

  var dialog = new BootstrapDialog({
    title: 'Add Assembly',
    message: '',
    buttons: [
      {
        id: 'submit_assembly_button',
        label: 'Submit Assembly',
        cssClass: 'btn-primary',
        title: 'Submit Assembly',
        action: function () {
          doPost();
          var $button = this; // 'this' here is a jQuery object that wrapping the <button> DOM element.
          $button.disable();
          $button.spin();
        },
      },
      {
        label: 'Close',
        action: function (dialogItself) {
          dialogItself.close();
        },
      },
    ],
  });

  if (window.location.protocol === 'https:') {
    wsprotocol = 'wss://';
  }
  var wsurl = wsprotocol + window.location.host + '/ws/assembly_status/' + uid;

  s3socket = new WebSocket(wsurl);

  s3socket.onclose = function (e) {
    console.log('s3socket closing ', e);
  };
  s3socket.onopen = function (e) {
    console.log('s3socket opened ', e);
  };
  s3socket.onmessage = function (e) {
    d = JSON.parse(e.data);
    element = element = $('#' + d.html_id);
    if ($('.modal-dialog').is(':visible')) {
      elem = $('.modal-dialog').find('#' + d.html_id);
      if (elem) {
        element = elem;
      }
    }

    if (!d && !$(element).is(':hidden')) {
      $(element).fadeOut('50');
    } else if (d && d.message && $(element).is(':hidden')) {
      $(element).fadeIn('50');
    }
    //$("#" + d.html_id).html(d.message)
    if (d.action === 'info') {
      // show something on the info div
      // check info div is visible
      $(element).removeClass('alert-danger').addClass('alert-info');
      $(element).html(d.message);
      if ('table_data' in d.data) {
        globalDataBuffer = d.data;
        var event = jQuery.Event('refreshtable');
        $('body').trigger(event);
      }
    } else if (d.action === 'error') {
      // check info div is visible
      $(element).removeClass('alert-info').addClass('alert-danger');
      $(element).html(d.message);
      //$("#spinner").fadeOut()
    }
  };
  window.addEventListener('beforeunload', function (event) {
    s3socket.close();
  });

  function submit() {
    var csrftoken = $.cookie('csrftoken');
    var profile_id = $('#profile_id').val();
    var fieldset = $('.modal-dialog').find(
      '#assembly_form input, textarea, select'
    );
    const form = new FormData();
    var count = 0;
    var files = [];
    $(fieldset).each(function (idx, el) {
      if (el.type == 'file') {
        form.append(el.name, el.files[0]);
      } else if ($.isArray($(el).val())) {
        $(el)
          .val()
          .forEach(function (v) {
            form.append(el.name, v);
          });
      } else if ($(el).val()) {
        form.append(el.name, $(el).val());
      }
    });

    id = $('.modal-dialog').find('#id_id');
    if (id != undefined) {
      form.append('assembly_id', $(id).val());
    }

    $('.modal-dialog')
      .find('#assembly_form input, textarea, select')
      .prop('disabled', true);

    var percent = $('.percent');
    form.append('profile_id', profile_id);
    jQuery
      .ajax({
        url: '/copo/copo_assembly/' + profile_id,
        data: form,
        files: files,
        cache: false,
        contentType: false,
        processData: false,
        method: 'POST',
        type: 'POST', // For jQuery < 1.9
        headers: {
          'X-CSRFToken': csrftoken,
        },
        xhr: function () {
          var xhr = jQuery.ajaxSettings.xhr();
          xhr.upload.onprogress = function (evt) {
            var percentVal = Math.round((evt.loaded / evt.total) * 100);
            percent.html(' (uploading...<b>' + percentVal + '%</b>)');
            console.log('progress', percentVal);
          };
          xhr.upload.onload = function () {
            percent.html('');
            console.log('DONE!');
          };
          return xhr;
        },
      })
      .fail(function (data) {
        dialog.enableButtons(true);
        dialog.getButton('submit_assembly_button').stopSpin();
        $('.modal-dialog')
          .find('#assembly_form input, textarea, select')
          .prop('disabled', false);
        $('.modal-dialog').find('#id_study').prop('disabled', true);
        $('.modal-dialog').find('#loading_span').fadeOut();
        BootstrapDialog.show({
          title: 'Error',
          message: 'Error ' + data.responseText,
          type: BootstrapDialog.TYPE_DANGER,
        });
      })
      .done(function (data) {
        $('.modal-dialog').find('#submit_assembly_button').fadeOut();
        $('.modal-dialog').find('#assembly_form').hide();
        $('.modal-dialog').find('#loading_span').hide();

        dialog.close();
        var dict = {
          status: 'success',
          message: data['success'],
        };
        do_crud_action_feedback(dict);
        globalDataBuffer = data;
        if (data.hasOwnProperty('table_data')) {
          //table data
          var event = jQuery.Event('refreshtable');
          $('body').trigger(event);
        }
        console.log(data);
      });
  }

  function doPost() {
    var evt = window.event;
    evt.preventDefault();
    submit();
  }

  //******************************Event Handlers Block*************************//
  var component = 'assembly';
  var copoFormsURL = '/copo/copo_forms/';
  var csrftoken = $.cookie('csrftoken');

  //get component metadata
  var componentMeta = get_component_meta(component);

  load_records(componentMeta); // call to load component records

  //register_resolvers_event(); //register event for publication resolvers

  //instantiate/refresh tooltips
  refresh_tool_tips();

  //trigger refresh of table
  $('body').on('refreshtable', function (event) {
    do_render_component_table(globalDataBuffer, componentMeta);
  });

  //handle task button event
  $('body').on('addbuttonevents', function (event) {
    do_record_task(event);
  });

  //add new component button
  $(document).on('click', '.new-component-template', function (event) {
    url = '/copo/copo_assembly/' + uid;
    handle_add_n_edit(url);
  });

  //details button hover
  /*
    $(document).on("mouseover", ".detail-hover-message", function (event) {
        $(this).prop('title', 'Click to view ' + component + ' details');
    });
    */

  //******************************Functions Block******************************//

  function handle_add_n_edit(url) {
    dialog.realize();
    dialog.setMessage($('<div></div>').load(url));
    dialog.open();
    dialog.setClosable(false);
  }

  function do_record_task(event) {
    var task = event.task.toLowerCase(); //action to be performed e.g., 'Edit', 'Delete'
    var tableID = event.tableID; //get target table

    //retrieve target records and execute task
    var table = $('#' + tableID).DataTable();
    var records = []; //
    $.map(table.rows('.selected').data(), function (item) {
      records.push(item);
    });

    //add task
    if (task == 'add') {
      url = '/copo/copo_assembly/' + uid;
      handle_add_n_edit(url);
    } else if (task == 'edit') {
      url = '/copo/copo_assembly/' + uid + '/' + records[0].record_id;
      handle_add_n_edit(url);
    } else {
      form_generic_task(component, task, records);
    }
    //table.rows().deselect(); //deselect all rows
  }

  $('body').on('posttablerefresh', function (event) {
    table = $('#' + component + '_table').DataTable();
    //var numCols = $('#' + component + '_table thead th').length;
    var numCols = table.columns().nodes().length;
    table.rows().nodes().to$().addClass('highlight_accession');

    for (var i = 0; i < numCols; i++) {
      if ($(table.column(i).header()).text() == 'ACCESSION') {
        var no_accessiion_indexes = table
          .rows()
          .eq(0)
          .filter(function (rowIdx) {
            return table.cell(rowIdx, i).data() === '' ? true : false;
          });
        table
          .rows(no_accessiion_indexes)
          .nodes()
          .to$()
          .addClass('highlight_no_accession');
      }
      if ($(table.column(i).header()).text() == 'ena_file_processing_status') {
        var error = table
          .rows()
          .eq(0)
          .filter(function (rowIdx) {
            file_processing_status = table.cell(rowIdx, i).data()
            if (file_processing_status == "" || file_processing_status.includes('File archived'))
               return false;
            else
               return true;
          });
        table
          .rows(error)
          .nodes()
          .to$()
          .addClass('highlight_error_file_processing_status');
      }      
    }
  });
}); //end document ready
