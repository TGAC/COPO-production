//it has been updated

var dt_options = {
  scrollY: 400,
  scrollX: true,
  bSortClasses: false,
  lengthMenu: [10, 25, 50, 75, 100, 500, 1000, 2000],
  select: {
    style: 'os',
    selector: 'td:first-child',
  },
  rowId: '_id',
  paging: true,
  createdRow: function (row, data, dataIndex) {
    $(row).addClass('sample_table_row');
  },

  columnDefs: [
    {
      className: 'tickbox',
      render: function (data, type, row) {
        var filter = $('#sample_filter').find('.active').find('a').attr('href');
        if (filter == 'pending' || filter == 'rejected') {
          return "<input type='checkbox' class='form-check-input checkbox'/>";
        } else {
          return '';
        }
      },
      targets: 0,
    },
  ],
  fnRowCallback: function (nRow, aData, iDisplayIndex, iDisplayIndexFull) {
    $(nRow)
      .children()
      .each(function (index, td) {
        if (index > 0) {
          if (td.innerText === 'NA') {
            $(td).addClass('na_color');
          } else if (td.innerText === '') {
            $(td).addClass('empty_color');
          }
        }
      });
  },
  processing: true,
  serverSide: true,
  // Reload DataTable on input change.
  search: {
    return: true,
  },
  ajax: {
    url: '/copo/dtol_submission/get_samples_for_profile',
    data: function (d) {
      return {
        profile_id: $('#profile_id').val(),
        filter: $('#sample_filter').find('.active').find('a').attr('href'),
        draw: d.draw,
        order: d.order,
        length: d.length,
        start: d.start,
        search: d.search.value,
      };
    },
    dataSrc: 'data',
  },
};
var sample_table;

$(document).ready(function () {
  // functions defined here are called from both copo_sample_accept_reject and copo_samples, all provide DTOL
  // functionality
  $(document).data('accepted_warning', false);
  $(document).data('isDtolSamplePage', true);
  $('#accept_reject_button').find('button').prop('disabled', true);
  // add field names here which you don't want to appear in the supervisors table
  excluded_fields = ['profile_id', 'biosample_id', '_id'];
  searchable_fields = [''];
  // populate profiles panel on left

  $(document).on('click', '.select-all', function () {
    $('.form-check-input:not(:checked)').each(function (idx, element) {
      $(element).click();
    });
  });
  $(document).on('click', '.select-none', function () {
    $('.form-check-input:checked').each(function (idx, element) {
      $(element).click();
    });
  });

  $(document).on('click', 'tr.sample_table_row', function (e) {
    var cb = $($(e.target).siblings('.tickbox').find('input'));
    cb.click();
  });

  $(document).on('click', '.delete-selected', function (e) {
    var saved_text = $('#dtol_sample_info').text();

    var checked = $('.form-check-input:checked').closest('tr');
    var sample_ids = [];
    $(checked).each(function (it) {
      sample_ids.push($(checked[it]).attr('id'));
    });
    if (sample_ids.length == 0) {
      alert('Please select samples to delete');
      return;
    }

    BootstrapDialog.show({
      title: 'Delete Samples',
      message: 'Are you sure you want to delete?',
      buttons: [
        {
          label: 'Close',
          action: function (dialogItself) {
            dialogItself.close();
          },
        },
        {
          label: 'Delete',
          action: function (dialog) {
            $('#dtol_sample_info').text('Deleting');

            var csrftoken = $.cookie('csrftoken');

            $.ajax({
              headers: { 'X-CSRFToken': csrftoken },
              url: '/copo/dtol_submission/delete_dtol_samples/',
              method: 'POST',
              data: {
                sample_ids: JSON.stringify(sample_ids),
              },
            })
              .done(function (e) {
                $('#profile_titles').find('.selected').click();
                $('#dtol_sample_info').text('Deleted');
                dialog.close();
              })
              .error(function (e) {
                console.error(e);
              });
          },
        },
      ],
    });
  });

  $(document).on('click', '.form-check-input', function (el) {
    if ($('.form-check-input:checked').length) {
      $('#accept_reject_button').find('button').prop('disabled', false);
    } else {
      $('#accept_reject_button').find('button').prop('disabled', true);
    }
    $(el.currentTarget)
      .parent()
      .siblings()
      .addBack()
      .each(function (idx, el) {
        $(el).toggleClass('selected_row');
      });
  });

  $(document).on('click', '#accept_reject_button button', handle_accept_reject);

  // handle clicks on both profiles (.selectable_row), and filter (.hot_tab)
  $(document).on('click', '.selectable_row, .hot_tab', row_select);

  $(document).on('change', '#dtol_type_select', function (e) {
    $.ajax({
      url: '/copo/get_subsample_stages',
      method: 'GET',
      data: {
        stage: $(e.currentTarget).val(),
      },
      dataType: 'json',
    }).done(function (data) {
      $('#accordion').fadeOut(function () {
        $("[id^='section']").find('.collapse').collapse('hide');
        $("[id^='section']").hide();
        $(data).each(function (idx, el) {
          el = el.replace(' ', '_');
          el = 'section_' + el;
          $('#' + el).show();
        });
        $('#accordion').fadeIn(function () {
          $(document)
            .find("[id^='section']:visible:first")
            .find('.collapse')
            .collapse('show');
        });
      });
    });
  });

  $(document).on(
    'keyup',
    '#taxonid',
    delay(function (e) {
      $('#taxonid').addClass('loading-spinner');
      var taxonid = $('#taxonid').val();
      if (taxonid == '') {
        $('#species, #genus, #family, #order, #commonName').val('');
        $('#species, #genus, #family, #order, #commonName').prop(
          'disabled',
          false
        );
        return false;
      }
      $.ajax({
        url: '/copo/resolve_taxon_id',
        method: 'GET',
        data: { taxonid: taxonid },
        dataType: 'json',
      })
        .done(function (data) {
          $('#species, #genus, #family, #order, #commonName').val('');
          $('#species, #genus, #family, #order, #commonName').prop(
            'disabled',
            false
          );
          for (var el in data) {
            var element = data[el];
            $('#' + el).prop('disabled', true);
            $('#' + el).val(element);
          }
          $('.loading-spinner').removeClass('loading-spinner');
        })
        .error(function (error) {
          BootstrapDialog.alert(error.responseText);
        });
    })
  );

  $(document).on(
    'keyup',
    '#species_search',
    delay(function (e) {
      var s = $('#species_search').val();
      $.ajax({
        url: '/copo/search_species',
        method: 'GET',
        data: { s: s },
        dataType: 'json',
      }).done(function (data) {
        var ul = $('ul', {
          class: 'species_results',
        });
        $(data).each(function (d) {
          $(ul).append('<li>', {
            html: d,
          });
        });
        $('#resultsPanel').append(ul);
      });
    })
  );

  $(document).on('click', '#species', function (e) {
    var disabled = $(e.currentTarget).attr('disabled');

    if (typeof disabled == typeof undefined && disabled !== true) {
      BootstrapDialog.show({
        title: 'Search',
        message: $('<div></div>').load(
          '/static/copo/snippets/ncbitaxon_species_search.html'
        ),
      });
    }
  });

  var profile_samples = document.getElementById('profile_samples');
  if (
    profile_samples &&
    profile_samples.getElementsByTagName('thead')[0].children.length == 0
  ) {
    $.ajax({
      url: '/copo/dtol_submission/get_sample_column_names',
      method: 'GET',
      dataType: 'json',
    })
      .error(function (data) {
        console.error('ERROR: ' + data);
      })
      .done(function (data) {
        if (data.length) {
          var header = $('<h4/>', {
            html: 'Samples',
          });
          $('#sample_panel').find('.labelling').empty().append(header);

          var rows = [];
          rows.push({ title: '' });

          let i = 0;
          while (i < data.length) {
            if (!excluded_fields.includes(data[i])) {
              rows.push({ title: data[i], data: data[i] });
            }
            i++;
          }
          if (profile_samples) {
            if ($.fn.DataTable.isDataTable('#profile_samples')) {
              sample_table.clear().destroy();
            }
            dt_options['columns'] = rows;
            dt_options['scrollCollapse'] = true;
            dt_options['scrollX'] = true;
            dt_options['scrollY'] = 1000;
            dt_options['fixedHeader'] = true;
            sample_table = $('#profile_samples').DataTable(dt_options);
          }
        }
      });
  }
  if (profile_samples) {
    update_pending_samples_table();
  }
});
var fadeSpeed = 'fast';

var row;
function row_select(ev) {
  $('#accept_reject_button').find('button').prop('disabled', true);
  // get samples for profile clicked in the left hand panel and populate table on the right

  if ($(ev.currentTarget).is('td') || $(ev.currentTarget).is('tr')) {
    // we have clicked a profile on the left hand list
    $(document).data('selected_row', $(ev.currentTarget));
    row = $(document).data('selected_row');
    $('.selected').removeClass('selected');
    $(row).addClass('selected');
  } else {
    row = $(document).data('selected_row');
  }

  var filter = $('#sample_filter').find('.active').find('a').attr('href');
  var profile_id = $(row).find('td').data('profile_id');
  $('#profile_id').val(profile_id);
  $('#spinner').show();
  sample_table.ajax.reload(function () {
    if (sample_table.data().length == 0) {
      var header = $('<h4/>', {
        html: 'No Samples Found',
      });
      $('#sample_panel').find('.labelling').empty().append(header);
      $('#profile_samples_wrapper').hide();
    } else {
      var header = $('<h4/>', {
        html: 'Samples',
      });
      $('#sample_panel').find('.labelling').empty().append(header);
      $('#profile_samples_wrapper').show();

      // Align table column headings with table body
      sample_table.columns.adjust().draw();
    }
  });

  $('#spinner').fadeOut('fast');
  /*
    $.ajax({
        url: "/copo/update_pending_samples_table",
        data: d,
        method: "GET",
        dataType: "json"
    }).error(function (data) {
        console.error("ERROR: " + data)
    }).done(function (data) {
            sample_table.clear();
            if (data.length) {
                var header = $("<h4/>", {
                    html: "Samples"
                })
                $("#sample_panel").find(".labelling").empty().append(header)

                sample_table.rows.add(data)

            } else {
                var content
                if (data.hasOwnProperty("locked")) {
                    content = $("<h4/>", {
                        html: "View is locked by another User. Try again later."
                    })
                } else {
                    content = $("<h4/>", {
                        html: "No Samples Found"
                    })
                }
                $("#sample_panel").find(".labelling").empty().html(
                    content
                )
                $("#accept_reject_button").find("button").prop("disabled", true)

            }
            sample_table.draw();

            $("#spinner").fadeOut("fast")

        }
    )
    */
}

function delay(fn, ms) {
  let timer = 0;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(fn.bind(this, ...args), ms || 1000);
  };
}

function update_pending_samples_table() {
  // get profiles with samples needing looked at and populate left hand column
  //check whether we are getting my profiles or all profiles
  var which_profiles = $('#sequencing_centre_filter')
    .find('.active')
    .find('a')
    .attr('href');
  //console.log(which_profiles)
  let columnDefs = [];

  if (which_profiles == 'my_profiles') {
    $('#accept_reject_button').show();
    $('#edit-buttons').show();
    columnDefs = [
      {
        targets: [1, 2],
        className: 'dt-center text-center',
      },
      { targets: [0], className: 'profile_title_header_my_profiles' },
    ];
  } else {
    $('#accept_reject_button').hide();
    $('#edit-buttons').hide();

    columnDefs = [
      {
        targets: [1],
        className: 'dt-center text-center',
      },
      { targets: [0], className: 'profile_title_header_all_profiles' },
    ];
  }
  $.ajax({
    url: '/copo/dtol_submission/update_pending_samples_table',
    method: 'GET',
    dataType: 'json',
    data: { profiles: which_profiles },
  })
    .error(function (e) {
      console.error(e);
    })
    .done(function (data) {
      if ($.fn.DataTable.isDataTable('#profile_titles')) {
        $('#profile_titles').DataTable().clear().destroy();
      }

      $(data).each(function (d) {
        let date = new Date(data[d].date_created.$date).toLocaleDateString(
          'en-GB',
          { timeZone: 'UTC' }
        );
        let link = '<td/>';
        if (which_profiles == 'my_profiles') {
          link =
            "<td><a href='/copo/copo_sample/" +
            data[d]._id.$oid +
            "/view'><i class='fa fa-link' aria-hidden='true'></i></a></td>'";
        }
        $('#profile_titles')
          .find('tbody')
          .append(
            "<tr class='selectable_row'><td data-profile_id='" +
              data[d]._id.$oid +
              "'>" +
              data[d].title +
              '</td><td>' +
              date +
              '</td>' +
              link +
              '</tr>'
          );
      });

      $.fn.dataTable.moment('DD/MM/YYYY');
      $('#profile_titles').DataTable({
        responsive: true,
        paging: false,
        dom: '<"top"f>rt<"bottom"lp><"clear">',
        order: [[1, 'desc']],
        columnDefs: columnDefs,
        initComplete: function () {
          var api = this.api();
          if (which_profiles != 'my_profiles') {
            // Hide Office column
            api.column(2).visible(false);
          }
        },
      });
      $($('#profile_titles tr')[1]).click();

      // Adjust the width of the table if it is 'All Profiles'
      if (which_profiles != 'my_profiles') {
        $('#profile_titles').css('width', '100%');
      }
    });
}

function handle_accept_reject(el) {
  $('#spinner').fadeIn(fadeSpeed);
  $('#accept_reject_button').find('button').prop('disabled', true);

  var checked = $('.form-check-input:checked').closest('tr');

  var button = $(el.currentTarget);
  var action;
  if (button.hasClass('positive')) {
    action = 'accept';
  } else {
    action = 'reject';
  }
  var sample_ids = [];
  $(checked).each(function (it) {
    sample_ids.push($(checked[it]).attr('id'));
  });

  $(checked).each(function (idx, row) {
    $(row).fadeOut(fadeSpeed);
    $(row).remove();
  });

  if (action == 'reject') {
    // mark sample object as rejected
    $.ajax({
      url: '/copo/dtol_submission/mark_sample_rejected',
      method: 'GET',
      data: { sample_ids: JSON.stringify(sample_ids) },
    }).done(function () {
      $('#profile_titles').find('.selected').click();
      $('#spinner').fadeOut(fadeSpeed);
    });
  } else if (action == 'accept') {
    if ($(document).data('accepted_warning')) {
      // create or update dtol submission record
      var profile_id = $('#profile_id').val();
      $('#sub_spinner').fadeIn(fadeSpeed);
      $.ajax({
        url: '/copo/dtol_submission/add_sample_to_dtol_submission/',
        method: 'GET',
        data: {
          sample_ids: JSON.stringify(sample_ids),
          profile_id: profile_id,
        },
      }).done(function () {
        $('#profile_titles').find('.selected').click();
        $('#spinner').fadeOut(fadeSpeed);
      });
    } else {
      BootstrapDialog.show({
        title: 'ENA Submission',
        message:
          'By accepting the samples, these will immediately be submitted to ENA. This action is' +
          ' irreversible.',
        cssClass: 'copo-modal1',
        closable: true,
        animate: true,
        type: BootstrapDialog.TYPE_INFO,
        buttons: [
          {
            label: 'Cancel',
            cssClass: 'tiny ui basic' + ' button',
            id: 'code_cancel',
            action: function (dialogRef) {
              dialogRef.close();
            },
          },
          {
            label: 'Ok',
            cssClass: 'tiny ui basic button',
            action: function (dialogRef) {
              dialogRef.close();
              $(document).data('accepted_warning', true);
              // create or update dtol submission record
              var profile_id = $('#profile_id').val();
              $('#sub_spinner').fadeIn(fadeSpeed);
              $.ajax({
                url: '/copo/dtol_submission/add_sample_to_dtol_submission/',
                method: 'GET',
                data: {
                  sample_ids: JSON.stringify(sample_ids),
                  profile_id: profile_id,
                },
              }).done(function () {
                $('#profile_titles').find('.selected').click();
                $('#spinner').fadeOut(fadeSpeed);
              });
            },
          },
        ],
      });
    }
  }
}
