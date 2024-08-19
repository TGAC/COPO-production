let contactCOPODialogCount = 1;

function get_profile_type() {
  return $('#profile_type').find(':selected').val();
}

$(document).ready(function () {
  //****************************** Event handlers block *************************//
  const component = 'profile';
  const copoProfileIndexURL = '/copo/';
  const copoAcceptRejectURL = '/copo/dtol_submission/accept_reject_sample';
  const copoSamplesURL = '/copo/copo_sample/';
  const copoENAReadManifestValidateURL = '/copo/copo_read/';
  const copoENAAssemblyURL = '/copo/copo_assembly/';
  const copoENAAnnotationURL = '/copo/copo_seq_annotation/';
  const copoVisualsURL = '/copo/copo_visualize/';
  const tableLoader = $('<div class="copo-i-loader"></div>');
  const componentMeta = get_component_meta(component);
  const tableID = componentMeta.tableID;

  let page = 1;
  let block_request = false;
  let end_pagination = false;
  let grid_count = $('#grid-count');
  let grid_total = $('#grid-total');

  // Create an object to store the arguments to
  // be passed to the function
  const obj = {
    tableLoader: tableLoader,
    copoProfileIndexURL: copoProfileIndexURL,
    page: page,
    end_pagination: end_pagination,
    block_request: block_request,
    tableID: tableID,
    copoVisualsURL: copoVisualsURL,
    csrftoken: csrftoken,
    component: component,
    copoSamplesURL: copoSamplesURL,
    copoENAReadManifestValidateURL: copoENAReadManifestValidateURL,
    copoENAAssemblyURL: copoENAAssemblyURL,
    copoENAAnnotationURL: copoENAAnnotationURL,
    grid_count: grid_count,
  };

  csrftoken = $.cookie('csrftoken');

  // Store the title displayed when a user hovers the ellipsis/profile options icon
  $(document).data('profileOptionsTitle', $('.row-ellipsis').attr('title'));

  // Add new profile button
  $(document).on('click', '.new-component-template', function () {
    var args_dict = { profile_type: get_profile_type() };
    initiate_form_call(component, args_dict);
  });

  $(document).on('click', '#accept_reject_shortcut', function () {
    document.location = copoAcceptRejectURL;
  });

  // Show web page buttons according to the group that the users are associated with
  if (groups.length != 0) {
    for (let g in groups) {
      // Display 'Accept/reject' button for sample managers
      if (groups[g].includes('sample_managers')) {
        $('#accept_reject_shortcut').show();
      }
    }
  }

  // Display empty profile message for potential first time users
  set_empty_component_message(profiles_total);

  // No profile records exist
  if (profiles_visible_length === 0) {
    $('#bottom-panel').hide();
    $('.profiles-legend').hide();
    $('.other-projects-accessions-filter-checkboxes').hide();
    return false;
  }

  initialise_popover();

  // Profile records exist
  // Initialise the popover 'View profile options' for each profile record
  /*
  let popover = $('#ellipsisID[data-toggle="popover"]')
    .popover({
      sanitize: false,
    })
    .click(function (e) {
      $(this).popover('toggle');
      $('#ellipsisID[data-toggle="popover"]').not(this).popover('hide');
      e.stopPropagation();
    })
    .on('show.bs.popover', function (e) {
      $('.row-ellipsis').attr('title', ''); // Hide 'View profile options' title from appearing in the popover on hover
 
      // Set content of the popover
      const $content = $('<div></div>');
      const $editButton = $(
        '<button id="editProfileBtn" class="btn btn-sm btn-success" title="Edit record"><i class="fa fa-pencil-square-o"></i>&nbsp;Edit</button>'
      );
      const $deleteButton = $(
        '<button id="deleteProfileBtn" class="btn btn-sm btn-danger" title="Delete record"><i class="fa fa-trash-can"></i>&nbsp;Delete</button>'
      );

      $deleteButton.css('margin-left', '15px');
      $content.append($editButton);
      $content.append($deleteButton);

      component_def["profile"]["recordActions"].forEach((item) => { 
        var action = record_action_button_def[item]
        const $button = $('<button id="'+ action["action"]  + '" class="btn btn-sm btn-primary" title="' + action["title"] + '"><i class="' + action["icon_class"] +' "></i>' +  action["label"] +'</button>');
        $button.css('margin-top', '10px');
        $content.append($button)
      });

      // Apply the content to the popover
      popover.attr('data-content', $content.html());
    })
    //.on('shown.bs.popover', function (e) {
    //  $('.row-ellipsis').attr('title', ''); // Hide 'View profile options' title from appearing in the popover on hover
    //});
    */
  $('#sortProfilesBtn')[0].selectedIndex = 0; // Set first option of sort menu

  grid_count.text(profiles_visible_length); // Number of profile records visible
  grid_total.text(profiles_total); //  Total number of profile records for the user

  let div_grid = $('div.grid');

  appendRecordComponents(div_grid);
  filter_action_menu();
  update_counts(copoVisualsURL, csrftoken, component);

  set_profile_grid_heading(div_grid); // Set profile grid heading

  showMoreProfileInfoPopover(div_grid); // Initialise 'show more' information popover for profile records

  $('#sortProfilesBtn').on('change', function () {
    const option_selected = this.value;
    sort_profile_records(option_selected);
  });

  // Add an event listener/bind the close button of the 'COPO contact dialog'
  $('#contactCOPODialogBtnID').bind('click', function () {
    contactCOPODialogCount++;
  });

  // Trigger refresh of the table div to reflect the changes made
  $('#copo-sidebar-info #page_alert_panel').on(
    'refreshtable2',
    function (event) {
      // Check if any alert messages are visible
      if ($('#copo-sidebar-info #page_alert_panel').children().length > 0) {
        populate_profiles_records(obj);
      }
    }
  );

  $(document).data('sortByDescendingOrder', true);

  $(document).on('click', '.expanding_menu > div', function (e) {
    const el = $(e.currentTarget);
    el.closest('.grid').removeClass('grid-selected');
    el.closest('.panel-heading')
      .next('.grid-panel-body')
      .removeClass('grid-panel-body-selected');
  });

  $(document).on('click', '.item a', function (e) {
    let url;
    const el = $(e.currentTarget);
    if (el.hasClass('action')) {
      const action_type = el.data('action_type');
      let id = el.closest('.expanding_menu').attr('id');
      id = id.split('_')[1];

      /*if (action_type === "dtol" || action_type === "erga") {
                url = copoSamplesURL + id + "/view"
                document.location = url
            } else */ if (action_type === 'release_study') {
        result = confirm('Are you sure to release the study?');
        if (result) {
          url = '/copo/copo_profile/' + id + '/release_study';
          $.ajax({
            url: url,
          })
            .done(function (data) {
              $('#study_status_' + id).html('PUBLIC');
              $('#study_release_date_' + id).html(data['study_release_date']);
              el.hide();
              /*
                        el.attr('aria-disabled', true).attr("role","link").css("pointer-events", "none").css("color", "grey")
                        alert("Study released successfully")
                        */
            })
            .fail(function (data) {
              alert(data.responseText);
            });
        }
      } /* else if (action_type === "assembly") {
                url = copoENAAssemblyURL + id + "/view"
            } else if (action_type === "annotation") {
                url = copoENAAnnotationURL + id + "/view"
            }*/ else {
        url = '/copo/copo_' + action_type + '/' + id + '/view';
        document.location = url;
      }
    }
  });

  // Toggle the visibility of the button to
  // sort in ascending order or descending order
  $(document).on('click', '#sortIconID', function (e) {
    let option = $('#sortProfilesBtn').val();

    $(this).toggleClass('sort-down fa fa-sort-down');
    $(this).toggleClass('sort-up fa fa-sort-up');

    if ($('i.sort-down').length) {
      $(document).data('sortByDescendingOrder', true);
      sort_profile_records(option);
    } else {
      $(document).data('sortByDescendingOrder', false);
      sort_profile_records(option);
    }

    e.preventDefault();
  });

  // Hide the profile options popover, display 'View profile options' on hover of the profile
  // options ellipsis icon and unhighlight focus on desired profile grid
  $(document).on('click', `#${tableID}`, function () {
    $('#ellipsisID[data-toggle="popover"]').popover('hide');
    $('.row-ellipsis').attr('title', $(document).data('profileOptionsTitle'));
  });

  $(document).on('click', '.copo-main', function () {
    $('#ellipsisID[data-toggle="popover"]').popover('hide');
    $('.row-ellipsis').attr('title', $(document).data('profileOptionsTitle'));
  });

  $(document).on('click', '.copo-sidebar', function () {
    $('#ellipsisID[data-toggle="popover"]').popover('hide');
    $('.row-ellipsis').attr('title', $(document).data('profileOptionsTitle'));
  });

  $(document).on('click', '#editProfileBtn', function (e) {
    let profile_id = $(e.currentTarget).closest('.ellipsisDiv').attr('id');
    let profile_type = $(e.currentTarget)
      .closest('.copo-records-panel')
      .attr('profile_type');
    if (profile_type == undefined) {
      profile_type = $(e.currentTarget)
        .closest('.copo-records-panel')
        .attr('shared_profile_type');
    }
    editProfileRecord(profile_id, profile_type);
  });

  $(document).on('click', '#deleteProfileBtn', function (e) {
    let profile_id = $(e.currentTarget).closest('.ellipsisDiv').attr('id');
    deleteProfileRecord(profile_id);
  });

  $(document).on('click', '#profileOptionsPopoverCloseBtn', function () {
    $('#ellipsisID[data-toggle="popover"]').popover('hide');
  });

  $(document).on('click', '#showMoreProfileInfoCloseBtn', function () {
    $('#showMoreProfileInfoBtn[rel="popover"]').popover('hide');
  });

  // Trigger infinite scroll once user scrolls downwards to display more profile records that exist
  $(window).scroll(function () {
    const margin = $(document).height() - $(window).height() - 200;

    // Scroll downwards
    if (
      $(window).scrollTop() > margin &&
      end_pagination === false &&
      block_request === false
    ) {
      block_request = true;
      page += 1;

      $('#component_table_loader').append(tableLoader); // Show loading .gif

      populate_profiles_records(obj);
    }
  });

  // Show a button which once a user hovers, it'll indicate that the
  // user can scroll downwards to view more profile records that were created
  let navigateToBottomOfPageBtn = $('#navigateToBottom');

  grid_count.text() < grid_total.text() && $(window).scrollTop() < 100
    ? navigateToBottomOfPageBtn.addClass('show')
    : navigateToBottomOfPageBtn.removeClass('show');

  // Navigate to the top of the web page on button clicked
  let navigateToTopOfPageBtn = $('#navigateToTop');

  $(window).on('scroll', function () {
    if ($(window).scrollTop() > 100) {
      // Hide the 'scroll down' button
      if (navigateToBottomOfPageBtn.hasClass('show'))
        navigateToBottomOfPageBtn.removeClass('show');
      // Show 'scroll up' button
      navigateToTopOfPageBtn.addClass('show');
    } else {
      navigateToTopOfPageBtn.removeClass('show');
    }
  });

  navigateToTopOfPageBtn.on('click', function (e) {
    e.preventDefault();
    $('html, body').animate(
      {
        scrollTop: 0,
      },
      '300'
    );
  });

  // On web page reload/refresh, sort profile records by default sort option and method
  window.onload = () => {
    let option = $('#sortProfilesBtn').val();
    sort_profile_records(option);
  };

  // Programmatically scroll down the web page a little if a user decides to
  // click the button which indicates on hover to scroll down to view more profiles
  navigateToBottomOfPageBtn.click(function () {
    $('html, body').animate(
      {
        scrollTop: document.body.scrollHeight + 30,
      },
      'slow'
    );
    navigateToBottomOfPageBtn.removeClass('show'); // Hide 'scroll down' button
  });
}); // End document ready

//****************************** Functions block ******************************//

function initialise_popover() {
  // Profile records exist
  // Initialise the popover 'View profile options' for each profile record

  let popover = $('#ellipsisID[data-toggle="popover"]')
    .popover({
      sanitize: false,
    })
    .click(function (e) {
      $(this).popover('toggle');
      $('#ellipsisID[data-toggle="popover"]').not(this).popover('hide');
      e.stopPropagation();
    })
    .on('show.bs.popover', function (e) {
      $('.row-ellipsis').attr('title', ''); // Hide 'View profile options' title from appearing in the popover on hover

      // Set content of the popover
      const $content = $('<div></div>');
      const $editButton = $(
        '<button id="editProfileBtn" class="btn btn-sm btn-success" title="Edit record"><i class="fa fa-pencil-square-o"></i>&nbsp;Edit</button>'
      );
      const $deleteButton = $(
        '<button id="deleteProfileBtn" class="btn btn-sm btn-danger" title="Delete record"><i class="fa fa-trash-can"></i>&nbsp;Delete</button>'
      );

      $deleteButton.css('margin-left', '15px');
      $content.append($editButton);
      $content.append($deleteButton);

      component_def['profile']['recordActions'].forEach((item) => {
        var action = record_action_button_def[item];
        const $button = $(
          '<button id="' +
            item +
            '" class="btn btn-sm btn-primary" title="' +
            action['title'] +
            '"><i class="' +
            action['icon_class'] +
            ' "></i>' +
            action['label'] +
            '</button>'
        );
        $button.css('margin-top', '10px');
        $content.append($button);
      });

      // Apply the content to the popover
      popover.attr('data-content', $content.html());
    });
  //.on('shown.bs.popover', function (e) {
  //  $('.row-ellipsis').attr('title', ''); // Hide 'View profile options' title from appearing in the popover on hover
  //});
}

function populate_profiles_records(obj) {
  tableLoader = obj.tableLoader;
  copoProfileIndexURL = obj.copoProfileIndexURL;
  page = obj.page;
  end_pagination = obj.end_pagination;
  block_request = obj.block_request;
  tableID = obj.tableID;
  copoVisualsURL = obj.copoVisualsURL;
  csrftoken = obj.csrftoken;
  component = obj.component;
  copoSamplesURL = obj.copoSamplesURL;
  copoENAReadManifestValidateURL = obj.copoENAReadManifestValidateURL;
  copoENAAssemblyURL = obj.copoENAAssemblyURL;
  copoENAAnnotationURL = obj.copoENAAnnotationURL;
  grid_count = obj.grid_count;

  $.ajax({
    type: 'GET',
    url: copoProfileIndexURL,
    data: {
      page: page,
    },
    success: function (data) {
      if (data.end_pagination === true) {
        end_pagination = true;
      } else {
        block_request = false;
      }

      // Check if div has content, if yes, empty the div
      if ($(`#${tableID}`).children().length > 0) {
        $(`#${tableID}`).empty();
      }

      let content = $(data.content);
      appendRecordComponents(content); // Adds 'Actions' and 'Components' buttons

      // Appends the html template from the 'copo_profile_record.html' to the 'copo_profiels_table' div
      $(`#${tableID}`).append(content);

      // Initialise functions for the profile grids beyond the 8 records that are shown by default
      refresh_tool_tips(); // Refreshes/reloads/reinitialises all popover and dropdown functions
      initialise_loaded_records(
        copoVisualsURL,
        csrftoken,
        component,
        tableID,
        copoSamplesURL,
        copoENAReadManifestValidateURL,
        copoENAAssemblyURL,
        copoENAAnnotationURL
      ); // Initialise functions for the profile grids beyond the 8 records that are shown by default

      set_profile_grid_heading(content); // Set profile grid heading
      showMoreProfileInfoPopover(content); // Initialise 'show more' information popover for profile records

      grid_count.text($('.grid').length); // Increment the number of profile records displayed
      tableLoader.remove(); // Remove loading .gif
    },
    error: function () {
      alert("Couldn't retrieve profiles!");
    },
  });
}

function appendRecordComponents(grids) {
  // loop through each grid
  grids.each(function () {
    let record_id = $(this).closest('.grid').find('.row-title span').attr('id');
    let profile_type =
      $(this)
        .closest('.grid')
        .find('.copo-records-panel')
        .attr('profile_type') === ''
        ? $(this)
            .closest('.grid')
            .find('.copo-records-panel')
            .attr('shared_profile_type')
        : $(this)
            .closest('.grid')
            .find('.copo-records-panel')
            .attr('profile_type');

    if (profile_type) {
      profile_type = profile_type.toLowerCase().trim();
    }
    // Add component buttons to the menu for each profile record
    let menu = $(this).closest('.grid').find('#expanding_menu');
    let component_buttons;
    $(menu).attr('id', 'menu_' + record_id);
    component_buttons = append_component_buttons(record_id, profile_type);
    $(menu).find('.comp').append(component_buttons);
  });
}

function editProfileRecord(profileRecordID, profileType) {
  const component = 'profile';
  let csrftoken = $.cookie('csrftoken');

  $('#ellipsisID[data-toggle="popover"]').popover('hide'); // Hides the popover

  $.ajax({
    url: copoFormsURL,
    type: 'POST',
    headers: { 'X-CSRFToken': csrftoken },
    data: {
      task: 'form',
      component: component,
      target_id: profileRecordID,
      profile_type: profileType,
    },
    success: function (data) {
      json2HtmlForm(data);
    },
    error: function () {
      alert("Couldn't build profile form!");
    },
  });
}

function deleteProfileRecord(profileRecordID) {
  const component = 'profile';
  const copoDeleteProfile = '/copo/copo_profile/delete';
  let csrftoken = $.cookie('csrftoken');

  $('#ellipsisID[data-toggle="popover"]').popover('hide'); // Hides the popover

  // Show a modal dialog to confirm if a user would like to delete the profile
  BootstrapDialog.show({
    title: 'Delete Profile',
    message:
      '<b>Are you sure that you would like this profile to be deleted?</b>' +
      '</br></br>You<strong> would not</strong> be able to retrieve the profile after it has been deleted.',
    cssClass: 'copo-modal1',
    closable: false,
    animate: true,
    type: BootstrapDialog.TYPE_WARNING,
    buttons: [
      {
        label: 'Cancel',
        cssClass: 'tiny ui basic button',
        action: function (dialogRef) {
          dialogRef.close();
        },
      },
      {
        label: 'Confirm',
        cssClass: 'tiny ui basic button dialog_confirm',
        action: function (dialogRef) {
          $.ajax({
            url: copoDeleteProfile,
            type: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            data: {
              task: 'validate_and_delete',
              component: component,
              target_id: profileRecordID,
            },
          })
            .done(function () {
              // Show a feedback message to the user
              const action_feedback = {
                message: 'Profile deleted!',
                status: 'success',
              };

              do_crud_action_feedback(action_feedback);

              // Hide the deleted profile record from the web page
              document
                .getElementById(profileRecordID)
                .closest('.copo-records-panel').style.display = 'none';

              // Close any other dialog that might be opened still
              $.each(BootstrapDialog.dialogs, function (id, dialog) {
                dialog.close();
              });

              // Add an event listener that will reload a particular div to
              // reflect the changes made after a record is deleted
              var event = jQuery.Event('refreshtable2');
              $('#copo-sidebar-info #page_alert_panel').trigger(event);
            })
            .fail(function (data_response) {
              email = $('#email').val();
              const message =
                "Profile couldn't be removed. Only profiles that have no datafiles or" +
                ' samples associated can be deleted.';
              let $content = '<div>';

              $content +=
                '<div style="margin-bottom: 10px; padding-bottom: 15px; font-weight: bold">' +
                message +
                '</div>';
              $content += '<p style="margin-top:10px">Please contact ';
              $content +=
                '<a style="text-decoration: underline;" href="mailto:' +
                email +
                '">' +
                email +
                '</a> ';
              $content += 'if you would like this profile to be deleted.</p>';
              $content += '</div>';

              BootstrapDialog.show({
                title: 'Profile deletion - error',
                message: $content,
                cssClass: 'copo-modal1',
                closable: true,
                animate: true,
                type: BootstrapDialog.TYPE_DANGER,
              });
            });
        },
      },
    ],
  });
}

function sort_profile_records(option) {
  // Determine the query selector
  let selector = (element) =>
    new Date(
      element.querySelector('.date_createdDiv').getAttribute('date_created')
    ).getTime(); // 'date_created' selector
  let isValueNumeric = false;

  switch (option) {
    case 'date_created':
      selector = (element) =>
        new Date(
          element.querySelector('.date_createdDiv').getAttribute('date_created')
        ).getTime();
      isValueNumeric = true;
      break;
    case 'title':
      // Remove parentheses if present from title
      selector = (element) =>
        element
          .querySelector('.row-title span')
          .innerText.replace(/\s*\(.*?\)\s*/g, '');
      break;
    case 'type':
      selector = (element) =>
        element
          .querySelector('.copo-records-panel')
          .getAttribute('profile_type');
      break;
    default:
      isValueNumeric = true;
      selector = (element) =>
        new Date(
          element.querySelector('.date_createdDiv').getAttribute('date_created')
        ).getTime(); // 'date_created' selector
  }

  // Choose the order method
  const descendingOrder = $(document).data('sortByDescendingOrder');
  const isNumeric = isValueNumeric;

  // Select all (profile grid) elements
  const elements = [...document.querySelectorAll('.grid')];

  // Find parent node
  const parentElement = elements[0].parentNode;

  // Sort the elements
  const collator = new Intl.Collator(undefined, {
    numeric: isNumeric,
    sensitivity: 'base',
  });

  elements
    .sort((elementA, elementB) => {
      const [firstElement, secondElement] = descendingOrder
        ? [elementB, elementA]
        : [elementA, elementB];
      const textOfFirstElement = selector(firstElement);
      const textOfSecondElement = selector(secondElement);
      return collator.compare(textOfFirstElement, textOfSecondElement);
    })
    .forEach((element) => parentElement.appendChild(element));
}

function do_render_profile_counts(data) {
  if (data.profiles_counts) {
    const stats = data.profiles_counts;

    for (let i = 0; i < stats.length; ++i) {
      const stats_id = stats[i].profile_id + '_';
      if (stats[i].counts) {
        for (let k in stats[i].counts) {
          if (stats[i].counts.hasOwnProperty(k)) {
            const count_id = stats_id + k;
            $('#' + count_id).html(stats[i].counts[k]);
          }
        }
      }
    }
  }
}

function display_profiles_legend(legend_data) {
  $.each(legend_data, function (index, element) {
    let acronym = element.profileTypeAcronym;
    let type = acronym === 'Shared' ? acronym : element.profileType;
    let colour = element.profileTypeColour;

    // Create profile type legend item
    let $legendItem = '<li class="profiles-legend-group-item">';
    $legendItem +=
      '<i class= "fa fa-info-circle profiles-legend-info-icon" title= "' +
      type +
      '"> </i>';
    $legendItem +=
      '<span class="fa fa-circle profiles-legend-circle" style="color:' +
      colour +
      '"></span>';
    $legendItem += acronym;
    $legendItem += '</li>';

    $('.profiles-legend').find('.profiles-legend-group').append($legendItem);
  });
}

function set_copo_sidebar_info_padding() {
  if ($('#page_alert_panel').text().trim() === '') {
    $('.copo-sidebar-tabs')
      .find('#profilesLegendDivID')
      .css('padding-top', '100px');
  } else {
    $('#profilesLegendDivID').css('padding-top', '0');
  }
}

function update_counts(copoVisualsURL, csrftoken, component) {
  $.ajax({
    url: copoVisualsURL,
    type: 'POST',
    headers: {
      'X-CSRFToken': csrftoken,
    },
    data: {
      task: 'profiles_counts',
      component: component,
    },
    success: function (data) {
      do_render_profile_counts(data);
    },
    error: function () {
      alert("Couldn't retrieve profiles information!");
    },
  });
}

function append_component_buttons(record_id, profile_type) {
  //components row
  const components = get_profile_components(profile_type);
  const componentsDIV = $('<div/>', {
    class: 'item',
  });

  components.forEach(function (item) {
    // skip 'profile' entry metadata
    // skip 'accessions_dashboard' entry metadata
    if (
      item.component === 'profile' ||
      item.component === 'accessions_dashboard'
    ) {
      return false;
    }
    /*
    if (
      !item.hasOwnProperty('profile_component') ||
      (profile_type === 'genomics' &&
        !item.profile_component.includes('stand-alone')) ||
      (profile_type !== 'genomics' &&
        item.profile_component.includes('stand-alone'))
    ) {
      return false;
    }
    */

    let component_link = '#';
    if (item.url != undefined)
      component_link = item.url.replace('999', record_id);

    // Create button html
    let pcomponent_count_div = $('<div></div>');

    let pcomponent_name_div = $('<div></div>')
      .attr('class', `tiny ui button pcomponent-color ${item.color}`)
      .append('<i class="pcomponent-icon ' + item.iconClass + '"></i>')
      .append(
        '<span class="pcomponent-name" style="padding-left: 3px;">' +
          item.title +
          '</span>'
      );

    // Add border radius to all components in the 'Components' menu
    // i.e. Do not show the count for all components in the 'Components' menu
    pcomponent_name_div.css('border-radius', '.28571429rem');

    let buttonHTML = $('<a></a>')
      .attr('title', 'Navigate to ' + item.title)
      .attr('href', component_link)
      .attr('class', 'tiny ui labeled button pcomponent-button')
      .attr('tabindex', '0')
      .css('margin', '3px 15px 3px 3px') // Set the component buttons to the same width
      .append(pcomponent_name_div);

    componentsDIV.append(buttonHTML);
  });

  return componentsDIV;
}

function filter_action_menu() {
  $('.copo-records-panel').each(function (idx, el) {
    let t = $(el).attr('profile_type');
    let shared_t = $(el).attr('shared_profile_type');
    let s = $(el).attr('study_status');
    study_status = '';

    if (s != undefined) {
      study_status = s.toUpperCase();
    }

    if (shared_t && !t) {
      t = shared_t;
      //if($(el).attr("profile_type")) $(el).removeAttr("profile_type")
    }

    if (t && !shared_t) {
      //if($(el).attr("shared_profile_type")) $(el).removeAttr("shared_profile_type")
    }

    $(el).find('a[profile_component]').hide();
    $(el)
      .find('a[profile_component=' + t + ']')
      .show();

    /*
    if (t.includes('ERGA')) {
      $(el).find("a[profile_component ='stand-alone']").hide();
      $(el).find("a[profile_component ='dtol']").hide();
    } else if (t.includes('DTOL') || t.includes('ASG')) {
      $(el).find("a[profile_component ='stand-alone']").hide();
      $(el).find("a[profile_component ='erga']").hide();
    } else if (t.includes('Stand-alone')) {
      $(el).find("a[profile_component ='erga']").hide();
      $(el).find("a[profile_component ='dtol']").hide();
    }
    */
    if (s == undefined || s != 'PRIVATE') {
      $(el).find("a[data-action_type ='release_study']").hide();
    }
    /*
        else if (s == "PUBLIC") {
            $(el).find("a[data-action_type ='release_study']").attr('aria-disabled', true).attr("role","link").css("pointer-events", "none").css("color", "grey")
        } */
  });
}

// function set_mediaQueries() {
//   // Add responsiveness to profile grids once web page screen size is changed
//   const screenSize_lst = [
//     window.matchMedia('(max-width: 1908px)'),
//     window.matchMedia('(max-width: 1901px)'),
//     window.matchMedia('(max-width: 1893px)'),
//     window.matchMedia('(max-width: 1818px)'),
//     window.matchMedia('(max-width: 1564px)'),
//     window.matchMedia('(max-width: 1703px)'),
//   ];

//   // Attach listener function on state changes
//   $.each(screenSize_lst, function (index, element) {
//     element.addEventListener('change', (e) => {
//       set_associated_types_marginBottom();
//     });
//   });
// }

function set_profile_grid_heading(grids) {
  let profiles_legend_lst = [];

  grids.each(function () {
    $(this)
      .find('.copo-records-panel')
      .each(function (idx, el) {
        const profile_type = $(el).attr('profile_type');
        let colour;
        let acronym;
        let legend_data;
        let current_profile_legendData = $(
          '.profiles-legend-group-item'
        ).text();

        if (profile_type) {
          if ($(el).attr('shared_profile_type') === '')
            $(el).removeAttr('shared_profile_type'); // Remove 'shared_profile_type' attribute

          acronym = profile_type.toUpperCase();
          colour =
            profile_type_def[profile_type.toLowerCase()]['widget_colour']; //'#fb7d0d'
          $(el)
            .find('.panel-heading')
            .find('.row-title span')
            .append('<small>(' + acronym + ')</small>');
          $(el).find('.panel-heading').css('background-color', colour);

          /*
          if (profile_type.includes('DTOLENV')) {
            acronym = 'DTOL-ENV';
            colour = '#fb7d0d';
            $(el)
              .find('.panel-heading')
              .find('.row-title span')
              .append('<small>(DTOL-ENV)</small>');
            $(el).find('.panel-heading').css('background-color', colour);
          } else if (profile_type.includes('DTOL')) {
            acronym = 'DTOL';
            colour = '#16ab39';
            $(el)
              .find('.panel-heading')
              .find('.row-title span')
              .append('<small>(DTOL)</small>');
            $(el).find('.panel-heading').css('background-color', colour);
          } else if (profile_type.includes('ASG')) {
            acronym = 'ASG';
            colour = '#5829bb';
            $(el)
              .find('.panel-heading')
              .find('.row-title span')
              .append('<small>(ASG)</small>');
            $(el).find('.panel-heading').css('background-color', colour);
          } else if (profile_type.includes('ERGA')) {
            acronym = 'ERGA';
            colour = '#E61A8D';
            $(el)
              .find('.panel-heading')
              .find('.row-title span')
              .append('<small>(ERGA)</small>');
            $(el).find('.panel-heading').css('background-color', colour);
          } else if (profile_type.includes('Stand-alone')) {
            acronym = 'Standalone';
            colour = '#009c95';
            $(el)
              .find('.panel-heading')
              .find('.row-title span')
              .append('<small>(Standalone)</small>');
            $(el).find('.panel-heading').css('background-color', colour);
          }
          */
        } else {
          acronym = 'Shared';
          colour = '#f26202';
          $(el)
            .find('.panel-heading')
            .find('.row-title span')
            .append('<small>(Shared With Me)</small>');
          $(el).find('.panel-heading').css('background-color', colour);

          // Remove 'profile_type' attribute if it exists since
          if ($(el).attr('profile_type') === '')
            $(el).removeAttr('profile_type');
        }

        // Add profile type legend data if it is not already in the list/displayed
        legend_data = {
          profileType: profile_type,
          profileTypeAcronym: acronym,
          profileTypeColour: colour,
        };

        if (
          !profiles_legend_lst
            .map((x) => x.profileType)
            .includes(profile_type) &&
          !current_profile_legendData.includes(acronym)
        ) {
          profiles_legend_lst.push(legend_data);
        }
      });
  });

  display_profiles_legend(profiles_legend_lst);
  set_copo_sidebar_info_padding();
}

// function set_associated_types_marginBottom() {
//   // Set the margin bottom once a profile description is displayed on two lines
//   // NB: If line height is 21 or 24, then, profile description is displayed on one line
//   // NB: If line height is 42 or 48 then, profile description is displayed on two lines

//   $('div.profileDescription').each(function () {
//     // Study release status div
//     let studyStatusDiv = $(this).prev().prev().prev();

//     if ($(this).height() === 42 || $(this).height() === 48) {
//       // No associated types
//       if ($(this).hasClass('no_associatedTypes_marginBottom')) {
//         // Has study release details
//         $(this)
//           .removeClass('no_associatedTypes_marginBottom')
//           .addClass('no_associatedTypes_marginBottom_2LineDescriptionText');
//       } else if ($(this).hasClass('no_associatedTypes_marginBottom_release')) {
//         // Does not have study release details
//         $(this)
//           .removeClass('no_associatedTypes_marginBottom_release')
//           .addClass(
//             'no_associatedTypes_marginBottom_2LineDescriptionText_release'
//           );
//       } else {
//         // Associated types
//         let associated_type_div_value = $(this).next().next();
//         if ($(this).hasClass('associatedTypes_marginBottom')) {
//           if (studyStatusDiv.hasClass('studyStatusDiv')) {
//             // Has study release details
//             if (
//               associated_type_div_value.hasClass(
//                 'one_associatedType_marginBottom_release'
//               )
//             ) {
//               associated_type_div_value
//                 .removeClass('one_associatedType_marginBottom_release')
//                 .addClass(
//                   'one_associatedType_marginBottom_2LineDescriptionText_release'
//                 );
//             } else if (
//               associated_type_div_value.hasClass(
//                 'two_associatedTypes_marginBottom_release'
//               )
//             ) {
//               associated_type_div_value
//                 .removeClass('two_associatedTypes_marginBottom_release')
//                 .addClass(
//                   'two_associatedTypes_marginBottom_2LineDescriptionText_release'
//                 );
//             } else if (
//               associated_type_div_value.hasClass(
//                 'three_associatedTypes_marginBottom_release'
//               )
//             ) {
//               associated_type_div_value
//                 .removeClass('three_associatedTypes_marginBottom_release')
//                 .addClass(
//                   'three_associatedTypes_marginBottom_2LineDescriptionText_release'
//                 );
//             } else if (
//               associated_type_div_value.hasClass(
//                 'several_associatedTypes_marginBottom_release'
//               )
//             ) {
//               associated_type_div_value
//                 .removeClass('several_associatedTypes_marginBottom_release')
//                 .addClass(
//                   'several_associatedTypes_marginBottom_2LineDescriptionText_release'
//                 );
//             }
//           } else {
//             // Does not have study release details
//             if (
//               associated_type_div_value.hasClass(
//                 'one_associatedType_marginBottom'
//               )
//             ) {
//               associated_type_div_value
//                 .removeClass('one_associatedType_marginBottom')
//                 .addClass(
//                   'one_associatedType_marginBottom_2LineDescriptionText'
//                 );
//             } else if (
//               associated_type_div_value.hasClass(
//                 'two_associatedTypes_marginBottom'
//               )
//             ) {
//               associated_type_div_value
//                 .removeClass('two_associatedTypes_marginBottom')
//                 .addClass(
//                   'two_associatedTypes_marginBottom_2LineDescriptionText'
//                 );
//             } else if (
//               associated_type_div_value.hasClass(
//                 'three_associatedTypes_marginBottom'
//               )
//             ) {
//               associated_type_div_value
//                 .removeClass('three_associatedTypes_marginBottom')
//                 .addClass(
//                   'three_associatedTypes_marginBottom_2LineDescriptionText'
//                 );
//             } else if (
//               associated_type_div_value.hasClass(
//                 'several_associatedTypes_marginBottom'
//               )
//             ) {
//               associated_type_div_value
//                 .removeClass('several_associatedTypes_marginBottom')
//                 .addClass(
//                   'several_associatedTypes_marginBottom_2LineDescriptionText'
//                 );
//             }
//           }
//         }
//       }
//     }
//   });
// }

function initialise_loaded_records(
  copoVisualsURL,
  csrftoken,
  component,
  tableID,
  copoSamplesURL,
  copoENAReadManifestValidateURL,
  copoENAAssemblyURL
) {
  filter_action_menu();
  update_counts(copoVisualsURL, csrftoken, component);
  /*
    $(".item a").click(function (e) {
        let url;
        const el = $(e.currentTarget);
        if (el.hasClass("action")) {
            const action_type = el.data("action_type");
            let id = el.closest(".expanding_menu").attr("id");
            id = id.split("_")[1]

            if (action_type === "dtol" || action_type === "erga") {
                url = copoSamplesURL + id + "/view"
            }  else {
                url = "/copo/copo_" +  action_type + "/" +  id + "/view"
            }
            document.location = url
        }
    })
    */

  $('.expanding_menu > div').click(function (e) {
    const el = $(e.currentTarget);
    el.closest('.grid').removeClass('grid-selected');
    el.closest('.panel-heading')
      .next('.grid-panel-body')
      .removeClass('grid-panel-body-selected');
  });

  /*
  $('#editProfileBtn').click(function (e) {
    let profile_id = $(e.currentTarget).closest('.ellipsisDiv').attr('id');
    let profile_type = $(e.currentTarget).closest('.copo-records-panel').attr('profile_type');
    editProfileRecord(profile_id, profile_type);
  });

  $('#deleteProfileBtn').click(function (e) {
    let profile_id = $(e.currentTarget).closest('.ellipsisDiv').attr('id');
    deleteProfileRecord(profile_id);
  });
  */
  $('#profileOptionsPopoverCloseBtn').click(function () {
    $('#ellipsisID[data-toggle="popover"]').popover('hide');
  });

  $('#showMoreProfileInfoCloseBtn').click(function () {
    $('#showMoreProfileInfoBtn[rel="popover"]').popover('hide');
  });

  // Initialise the popover 'View profile options' for each profile record
  initialise_popover();
  /*
  let popover = $('#ellipsisID[data-toggle="popover"]')
    .popover({
      sanitize: false,
    })
    .click(function (e) {
      $(this).popover('toggle');
      $('#ellipsisID').not(this).popover('hide');
      e.stopPropagation();
    })
    .on('show.bs.popover', function (e) {
      // Set content of the popover
      const $content = $('<div></div>');
      const $editButton = $(
        '<button id="editProfileBtn" class="btn btn-sm btn-success" title="Edit record"><i class="fa fa-pencil-square-o"></i>&nbsp;Edit</button>'
      );
      const $deleteButton = $(
        '<button id="deleteProfileBtn" class="btn btn-sm btn-danger" title="Delete record"><i class="fa fa-trash-can"></i>&nbsp;Delete</button>'
      );

      $deleteButton.css('margin-left', '15px');
      $content.append($editButton);
      $content.append($deleteButton);

      component_def["profile"]["recordActions"].forEach((item) => { 
        var action = record_action_button_def[item]
        const $button = $('<button id="'+ action["action"]  + '" class="btn btn-sm btn-primary" title="' + action["title"] + '"><i class="' + action["icon_class"] +' "></i>' +  action["label"] +'</button>');
        $button.css('margin-top', '10px');
        $content.append($button)
      });

      // Apply the content to the popover
      popover.attr('data-content', $content.html());
    })
    .on('shown.bs.popover', function (e) {
      $('.row-ellipsis').attr('title', ''); // Hide 'View profile options' title from appearing in the popover on hover
    });
    */
}
/*
function contact_COPO_popup_dialog() {
  email = $("#email").val();
  const message =
    'If you would like to make manifest submissions to an ASG, ERGA or DToL manifest group';
  let $content = '<div>';

  $content +=
    '<div style="margin-bottom: 10px; padding-bottom: 15px; font-weight: bold">' +
    message +
    '</div>';
  $content +=
    '<p style="margin-top:10px">Please contact <a style="text-decoration: underline;" href="mailto:' + email + '">' + email + '</a> in order to be added to the manifest group. We will grant you the permission to select the desired group, create a profile for the group and subsequently upload a manifest to the group.</p>';
  $content += '</div>';

  const dialog = new BootstrapDialog({
    type: BootstrapDialog.TYPE_WARNING,
    title: 'Contact COPO via email',
    message: $content,
    closable: false,
    onshown: function (dialogRef) {
      contactCOPODialogCount++; // Increment the number of times the dialog is shown
    },
    onhide: function (dialogRef) {},
    buttons: [
      {
        id: 'contactCOPODialogBtnID',
        label: 'Okay',
        cssClass: 'btn-custom3',
        hotkey: 13,
        action: function (dialogRef) {
          dialogRef.close(); // Close the 'Contact COPO' dialog
        },
      },
    ],
  });

  dialog.realize();
  dialog.getModalFooter().removeClass('modal-footer');
  dialog.getModalFooter().css({ padding: '15px', 'text-align': 'right' });

  // Show the 'Contact COPO dialog' once
  if (contactCOPODialogCount > 1) {
    contactCOPODialogCount++;
    return false;
  } else {
    dialog.open();
  }
} //end of contact_COPO_popup_dialog  **************
*/
/*
function filter_associatedProfileTypeList_based_on_selectedProfileType(
  profileTypeID
) {
  if (
    !document.getElementById(profileTypeID).value ||
    document.getElementById(profileTypeID).value != 'Stand-alone'
  ) {
    let selected_type = get_acronym(
      document.getElementById(profileTypeID).value
    );
    let multi_select_options = $('.copo-multi-select2');
    let associated_type_option = multi_select_options.find(
      "option[value*='" + selected_type + "']"
    );
    let selected_associated_types = multi_select_options.find(':selected');

    // Check any associated type (s) exists
    if (selected_associated_types.length || associated_type_option.length) {
      // Exclude the selected profile from the associated profile type dropdown menu options
      multi_select_options.select2({
        templateResult: function (option) {
          let option_value = get_acronym(option.text);

          if (option_value === selected_type) {
            return null;
          }
          // Exclude erga associated types from the associated profile type dropdown menu options
          // if "ERGA" is not selected as the profile type
          let erga_associated_types = [
            'BGE',
            'POP_GENOMICS',
            'ERGA_PILOT',
            'ERGA_SATELLITES',
          ];
          if (!selected_type.includes('ERGA')) {
            if (
              erga_associated_types.some((erga_a_type) =>
                option.text.includes(erga_a_type)
              )
            ) {
              return null;
            }
          }
          return option.text;
        },
      });

      // Reinitialise/update the multi-select options
      multi_select_options.trigger('change');
    }
  }
}

function remove_selectedProfileType_from_associatedProfileTypeList(
  profileTypeID
) {
  document
    .getElementById(profileTypeID)
    .addEventListener('change', function () {
      // Perform the following only if selected 'Profile Type' is not "Stand-alone"
      //if (this.value == 'European Reference Genome Atlas (ERGA)') {
      if (this.value == 'erga') {
        $('.row:nth-child(4) > .col-sm-12').show(); // Show 'Associated Profile Type(s)' field
        $('.row:nth-child(5) > .col-sm-12').show(); // Show 'Sequencing Centre(s)' field
        $('.row:nth-child(5) > .col-sm-12')
          .find('select')
          .attr('required', 'required');
        // $('[id*="sequencing_centre"]').parent().parent().hide().show();
        let selected_type = get_acronym(this.value);
        let multi_select_options = $('.copo-multi-select2');
        let associated_type_option = multi_select_options.find(
          "option[value*='" + selected_type + "']"
        );

        // Clear associated type(s) options when profile type is changed
        multi_select_options.val(null).trigger('change');

        if (associated_type_option.length) {
          // Exclude the selected profile from the associated profile type dropdown menu options
          multi_select_options.select2({
            templateResult: function (option) {
              let option_value = option.text //get_acronym(option.text);

              if (option_value === selected_type) {
                return null;
              }
              // Exclude erga associated types from the associated profile type dropdown menu options
              // if "ERGA" is not selected as the profile type
              let erga_associated_types = ['BGE', 'POP_GENOMICS', 'ERGA_PILOT'];
              if (!selected_type.includes('erga')) {
                if (
                  erga_associated_types.some((erga_a_type) =>
                    option.text.includes(erga_a_type)
                  )
                ) {
                  return null;
                }
              }
              return option.text;
            },
          });
          // Reinitialise/update the multi-select options
          multi_select_options.trigger('change');
        }
      } else {
        $('.row:nth-child(4) > .col-sm-12').hide(); // Hide 'Associated Profile Type(s)' field
        $('.row:nth-child(5) > .col-sm-12').hide(); // Hide 'Sequencing Centre(s)' field
        $('.row:nth-child(5) > .col-sm-12')
          .find('select')
          .removeAttr('required');
        // $('[id*="sequencing_centre"]').parent().parent().hide().hide;
      }
    });
}
*/
function showMoreProfileInfoPopover(grids) {
  grids.each(function () {
    let showMoreProfileInfoBtn = $(this)
      .closest('.grid')
      .find('#showMoreProfileInfoBtn[rel="popover"]');

    showMoreProfileInfoBtn
      .popover({
        html: true,
        trigger: 'click',
        sanitize: false,
        title: function () {
          let $showMoreProfileInfoCloseBtn =
            '<i id="showMoreProfileInfoCloseBtn" class="fa fa-times pull-right"></i>';
          return $showMoreProfileInfoCloseBtn;
        },
        content: function (e) {
          return $(this)
            .closest('.grid-panel-body')
            .find('#showMoreProfileInfoContent')
            .children('.popover-content')
            .html();
        },
      })
      .click(function (e) {
        e.preventDefault(); // Prevents one from being automatically redirected to the top of the page
        $(this).popover('toggle');
        $('#showMoreProfileInfoBtn[rel="popover"]').not(this).popover('hide');
        e.stopPropagation();

        // Initialise the tooltip for the associated type info icon
        // if the profile has associated types to display
        if (
          $(this).popover().is(':visible') &&
          $(this).popover().find('.associated_type_info_icon')
        ) {
          $('.associated_type_info_icon').tooltip();
        }

        // Initialise the tooltip for the sequencing centre info icon
        // if the profile has sequencing centres to display
        if (
          $(this).popover().is(':visible') &&
          $(this).popover().find('.sequencing_centre_info_icon')
        ) {
          $('.sequencing_centre_info_icon').tooltip();
        }
      });
  });
}
/*
function get_acronym(txt) {
  // Retrieve the parentheses and the enclosed string from the
  // selected profile type
  const regex = /\(([^()]*)\)/g;
  let select_value;

  if (!regex.test(txt)) {
    select_value = txt; // Get selected value if no parentheses exist
  } else {
    let associated_type_abbreviation_without_parentheses = txt.substring(
      txt.indexOf('(') + 1,
      txt.indexOf(')')
    );

    // Get associated type acronym that is enclosed in parentheses
    // If empty an empty string is returned, set the acronym as the full string
    select_value =
      associated_type_abbreviation_without_parentheses === ''
        ? txt.replace(/\(\s*\)/g, '')
        : associated_type_abbreviation_without_parentheses.trim();
  }

  return select_value;
}
*/
