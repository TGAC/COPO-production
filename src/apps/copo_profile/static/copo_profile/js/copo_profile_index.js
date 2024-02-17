let contactCOPODialogCount = 1;

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

  csrftoken = $.cookie('csrftoken');

  // Store the title displayed when a user hovers the ellipsis/profile options icon
  $(document).data('profileOptionsTitle', $('.row-ellipsis').attr('title'));

  // Add new profile button
  $(document).on('click', '.new-component-template', function () {
    initiate_form_call(component);
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

  // Profile records exist
  // Initialise the popover 'View profile options' for each profile record
  initialise_ellipsisID_popover();

  $('#sortProfilesBtn')[0].selectedIndex = 0; // Set first option of sort menu

  grid_count.text(profiles_visible_length); // Number of profile records visible
  grid_total.text(profiles_total); //  Total number of profile records for the user

  let div_grid = $('div.grid');

  appendRecordComponents(div_grid);
  filter_action_menu();
  update_counts(copoVisualsURL, csrftoken, component);

  set_profile_grid_heading(div_grid); // Set profile grid heading

  initialise_showMoreProfileInfoPopover(div_grid); // Initialise 'show more' information popover for profile records

  // Initialise dropdowns
  [...document.querySelectorAll('.dropdown-toggle')].map(
    (dropdownToggleEl) => new bootstrap.Dropdown(dropdownToggleEl)
  );

  $('#sortProfilesBtn').on('change', function () {
    const option_selected = this.value;
    sort_profile_records(option_selected);
  });

  // Add an event listener/bind the close button of the 'COPO contact dialog'
  $('#contactCOPODialogBtnID').bind('click', function () {
    contactCOPODialogCount++;
  });

  $(document).data('sortByDescendingOrder', true);

  $(document).on('click', '.expanding_menu > div', function (e) {
    const el = $(e.currentTarget);
    el.closest('.grid').removeClass('grid-selected');
    el.closest('.card-header')
      .next('.grid-card-body')
      .removeClass('grid-card-body-selected');
  });

  $(document).on('click', '.item a', function (e) {
    trigger_menu_dropdown(e);
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
  $(document).on('click', `#${tableID}`, function (e) {
    // hide_ellipsisID_popover(e);
    $('.row-ellipsis').attr('title', $(document).data('profileOptionsTitle'));
  });

  $(document).on('click', '.copo-main', function (e) {
    // bhide_ellipsisID_popover(e);
    $('.row-ellipsis').attr('title', $(document).data('profileOptionsTitle'));
  });

  $(document).on('click', '.copo-sidebar', function (e) {
    // hide_ellipsisID_popover(e);
    $('.row-ellipsis').attr('title', $(document).data('profileOptionsTitle'));
  });

  $(document).on('click', '#editProfileBtn', function (e) {
    let profile_id = $(e.currentTarget).closest('.ellipsisDiv').attr('id');
    editProfileRecord(e, profile_id);
  });

  $(document).on('click', '#deleteProfileBtn', function (e) {
    let profile_id = $(e.currentTarget).closest('.ellipsisDiv').attr('id');
    deleteProfileRecord(e, profile_id);
  });

  $(document).on('click', '#profileOptionsPopoverCloseBtn', function (e) {
    e.stopPropagation();
    hide_ellipsisID_popover(e);
  });

  $(document).on('click', '#showMoreProfileInfoCloseBtn', function (e) {
    e.stopPropagation();
    hide_showMoreProfileInfoCloseBtn_popover(e);
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
          initialise_showMoreProfileInfoPopover(content); // Initialise 'show more' information popover for profile records

          grid_count.text($('.grid').length); // Increment the number of profile records displayed
          tableLoader.remove(); // Remove loading .gif
        },
        error: function () {
          alert("Couldn't retrieve profiles!");
        },
      });
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
function appendRecordComponents(grids) {
  // loop through each grid
  grids.each(function () {
    let record_id = $(this).closest('.grid').find('.row-title span').attr('id');
    let profile_type =
      $(this)
        .closest('.grid')
        .find('.copo-records-card')
        .attr('profile_type') === ''
        ? $(this)
            .closest('.grid')
            .find('.copo-records-card')
            .attr('shared_profile_type')
        : $(this)
            .closest('.grid')
            .find('.copo-records-card')
            .attr('profile_type');

    if (profile_type) {
      profile_type = profile_type.toLowerCase().trim();
    }
    // Add component buttons to the menu for each profile record
    let menu = $(this).closest('.grid').find('#expanding_menu');
    // let component_buttons;
    $(menu).attr('id', 'menu_' + record_id);
    append_component_buttons($(menu).find('.comp'), record_id, profile_type);
    // component_buttons = append_component_buttons(record_id, profile_type);
    // $(menu).find('.comp').append(component_buttons);
  });
}

function editProfileRecord(e, profileRecordID) {
  const component = 'profile';
  let csrftoken = $.cookie('csrftoken');

  // Hides the popover
  hide_ellipsisID_popover(e);

  $.ajax({
    url: copoFormsURL,
    type: 'POST',
    headers: { 'X-CSRFToken': csrftoken },
    data: {
      task: 'form',
      component: component,
      target_id: profileRecordID,
    },
    success: function (data) {
      json2HtmlForm(data);
    },
    error: function () {
      alert("Couldn't build profile form!");
    },
  });
}

function deleteProfileRecord(e, profileRecordID) {
  const component = 'profile';
  const copoDeleteProfile = '/copo/copo_profile/delete';
  let csrftoken = $.cookie('csrftoken');

  hide_ellipsisID_popover(e); // Hides the popover

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
              // Delete the profile
              BootstrapDialog.show({
                title: 'Profile deleted',
                message: 'Profile has been deleted.',
                cssClass: 'copo-modal1',
                closable: true,
                animate: true,
                type: BootstrapDialog.TYPE_INFO,
              });

              // Refresh web page to have change reflected
              setTimeout(function () {
                document
                  .getElementById(profileRecordID)
                  .closest('.copo-records-card').style.display = 'none';

                window.location.reload();
              }, 1000);
            })
            .fail(function (data_response) {
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
                '<a style="text-decoration: underline;" href="mailto:ei.copo@earlham.ac.uk">ei.copo@earlham.ac.uk</a> ';
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
          .querySelector('.copo-records-card')
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
  if ($('#page_alert_card').text().trim() === '') {
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

function append_component_buttons(componentsUL, record_id, profile_type) {
  //components row
  const components = get_profile_components();
  const componentsDIV = $('<li/>', {
    class: 'item',
  });
  // let componentsUL = $('.comp');

  components.forEach(function (item) {
    // skip 'profile' entry metadata
    // skip 'accessions_dashboard' entry metadata
    if (
      item.component === 'profile' ||
      item.component === 'accessions_dashboard'
    ) {
      return false;
    }

    if (
      !item.hasOwnProperty('profile_component') ||
      (profile_type === 'stand-alone' &&
        !item.profile_component.includes('stand-alone')) ||
      (profile_type !== 'stand-alone' &&
        item.profile_component.includes('stand-alone'))
    ) {
      return false;
    }

    let component_link = '#';

    try {
      component_link = $('#' + item.component + '_url')
        .val()
        .replace('999', record_id);
    } catch (err) {
      console.log(err.message);
    }

    // Create button html
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
      .attr('class', 'dropdown-item tiny ui labeled button pcomponent-button')
      .attr('tabindex', '0')
      .css('margin', '3px 15px 3px 3px') // Set the component buttons to the same width
      .append(pcomponent_name_div);

    componentsDIV.append(buttonHTML);
    componentsUL.append(componentsDIV);
  });

  return componentsDIV;
}

function filter_action_menu() {
  $('.copo-records-card').each(function (idx, el) {
    let t = $(el).attr('profile_type');
    let shared_t = $(el).attr('shared_profile_type');
    let s = $(el).attr('study_status');
    study_status = '';

    if (s != undefined) {
      study_status = s.toUpperCase();
    }

    if (shared_t && !t) {
      t = shared_t;
    }

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
    if (s == undefined || s != 'PRIVATE') {
      $(el).find("a[data-action_type ='release_study']").hide();
    }
    /*
        else if (s == "PUBLIC") {
            $(el).find("a[data-action_type ='release_study']").attr('aria-disabled', true).attr("role","link").css("pointer-events", "none").css("color", "grey")
        } */
  });
}

function set_profile_grid_heading(grids) {
  let profiles_legend_lst = [];

  grids.each(function () {
    $(this)
      .find('.copo-records-card')
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

          if (profile_type.includes('DTOL_ENV')) {
            acronym = 'DTOL-ENV';
            colour = '#fb7d0d';
            $(el)
              .find('.card-header')
              .find('.row-title span')
              .append('<small>(DTOL-ENV)</small>');
            $(el).find('.card-header').css('background-color', colour);
          } else if (profile_type.includes('DTOL')) {
            acronym = 'DTOL';
            colour = '#16ab39';
            $(el)
              .find('.card-header')
              .find('.row-title span')
              .append('<small>(DTOL)</small>');
            $(el).find('.card-header').css('background-color', colour);
          } else if (profile_type.includes('ASG')) {
            acronym = 'ASG';
            colour = '#5829bb';
            $(el)
              .find('.card-header')
              .find('.row-title span')
              .append('<small>(ASG)</small>');
            $(el).find('.card-header').css('background-color', colour);
          } else if (profile_type.includes('ERGA')) {
            acronym = 'ERGA';
            colour = '#E61A8D';
            $(el)
              .find('.card-header')
              .find('.row-title span')
              .append('<small>(ERGA)</small>');
            $(el).find('.card-header').css('background-color', colour);
          } else if (profile_type.includes('Stand-alone')) {
            acronym = 'Standalone';
            colour = '#009c95';
            $(el)
              .find('.card-header')
              .find('.row-title span')
              .append('<small>(Standalone)</small>');
            $(el).find('.card-header').css('background-color', colour);
          }
        } else {
          acronym = 'Shared';
          colour = '#f26202';
          $(el)
            .find('.card-header')
            .find('.row-title span')
            .append('<small>(Shared With Me)</small>');
          $(el).find('.card-header').css('background-color', colour);

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

  $('.item a').click(function (e) {
    trigger_menu_dropdown(e);
  });

  $('.expanding_menu > div').click(function (e) {
    const el = $(e.currentTarget);
    el.closest('.grid').removeClass('grid-selected');
    el.closest('.card-header')
      .next('.grid-card-body')
      .removeClass('grid-card-body-selected');
  });

  $('#editProfileBtn').click(function (e) {
    let profile_id = $(e.currentTarget).closest('.ellipsisDiv').attr('id');
    editProfileRecord(e, profile_id);
  });

  $('#deleteProfileBtn').click(function (e) {
    let profile_id = $(e.currentTarget).closest('.ellipsisDiv').attr('id');
    deleteProfileRecord(e, profile_id);
  });

  $('#profileOptionsPopoverCloseBtn').click(function () {
    new bootstrap.Popover.getInstance('#ellipsisID').hide();
  });

  // Initialise the popover 'View profile options' for each profile record
  initialise_ellipsisID_popover();
}

function contact_COPO_popup_dialog() {
  const message =
    'If you would like to make manifest submissions to an ASG, ERGA or DToL manifest group';
  let $content = '<div>';

  $content +=
    '<div style="margin-bottom: 10px; padding-bottom: 15px; font-weight: bold">' +
    message +
    '</div>';
  $content +=
    '<p style="margin-top:10px">Please contact <a style="text-decoration: underline;" href="mailto:ei.copo@earlham.ac.uk">ei.copo@earlham.ac.uk</a> in order to be added to the manifest group. We will grant you the permission to select the desired group, create a profile for the group and subsequently upload a manifest to the group.</p>';
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
      if (this.value == 'European Reference Genome Atlas (ERGA)') {
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
              let option_value = get_acronym(option.text);

              if (option_value === selected_type) {
                return null;
              }
              // Exclude erga associated types from the associated profile type dropdown menu options
              // if "ERGA" is not selected as the profile type
              let erga_associated_types = ['BGE', 'POP_GENOMICS', 'ERGA_PILOT'];
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

function initialise_showMoreProfileInfoPopover(grids) {
  const list = [].slice.call(
    document.querySelectorAll('#showMoreProfileInfoBtn')
  );
  list.map((popoverTriggerEl) => {
    let options = {
      popperConfig: function (defaultBsPopperConfig) {
        return { placement: 'right' };
      },
      html: true,
      sanitize: false,
      trigger: 'click focus',
      title: function () {
        let $showMoreProfileInfoCloseBtn =
          '<i id="showMoreProfileInfoCloseBtn" class="fa fa-times float-end"></i>';
        return $showMoreProfileInfoCloseBtn;
      },
      content: function (e) {
        // Set content of the popover
        return $(e)
          .closest('.grid-card-body')
          .find('#showMoreProfileInfoContent')
          .children('.popover-body')
          .html();
      },
    };

    new bootstrap.Popover(popoverTriggerEl, options);
  });

  // Initialise the tooltip for the associated type info icon
  // if the profile has associated types to display

  const associated_type_popover = bootstrap.Popover.getInstance(
    document.getElementsByClassName('.associated_type_info_icon')
  );

  const is_associated_type_popover_showing =
    associated_type_popover &&
    associated_type_popover.tip &&
    associated_type_popover.tip.classList.contains('show');

  if (is_associated_type_popover_showing) {
    new bootstrap.Tooltip(associated_type_popover, options);
  }

  // Initialise the tooltip for the sequencing centre info icon
  // if the profile has sequencing centres to display
  const sequencing_centre_popover = bootstrap.Popover.getInstance(
    document.getElementsByClassName('.associated_type_info_icon')
  );

  const is_sequencing_centre_popover_showing =
    sequencing_centre_popover &&
    sequencing_centre_popover.tip &&
    sequencing_centre_popover.tip.classList.contains('show');

  if (is_sequencing_centre_popover_showing) {
    new bootstrap.Tooltip(associated_type_popover, options);
  }
}

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

function initialise_ellipsisID_popover() {
  const list = [].slice.call(document.querySelectorAll('#ellipsisID'));

  list.map((popoverTriggerEl) => {
    let options = {
      popperConfig: function (defaultBsPopperConfig) {
        return { placement: 'right' };
      },
      html: true,
      sanitize: false,
      trigger: 'click focus',
      title: function () {
        let $profileOptionsPopoverCloseBtn =
          '<i id="profileOptionsPopoverCloseBtn" class="fa fa-times float-end"></i>';
        return $profileOptionsPopoverCloseBtn;
      },
      content: function (e) {
        // Set content of the popover
        // Hide 'View profile options' title from appearing in the popover on hover
        $('.row-ellipsis').attr('title', '');

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

        // Apply the content to the popover
        return $content.html();
      },
    };

    new bootstrap.Popover(popoverTriggerEl, options);
  });
}

function hide_showMoreProfileInfoCloseBtn_popover(e) {
  if (
    $('.popover').has(e.target).length == 0 ||
    $(e.target).is('#showMoreProfileInfoCloseBtn')
  ) {
    bootstrap.Popover.getInstance('#showMoreProfileInfoBtn').hide();
  }
}

function hide_ellipsisID_popover(e) {
  if (
    $('.popover').has(e.target).length == 0 ||
    $(e.target).is('#profileOptionsPopoverCloseBtn')
  ) {
    bootstrap.Popover.getInstance('#ellipsisID').hide();
  }
}

function trigger_menu_dropdown(e) {
  // Semantic UI dropdown menu is not triggered on click
  // so trigger it programmatically
  let url;
  const el = $(e.currentTarget);
  if (el.hasClass('action')) {
    const action_type = el.data('action_type');
    let id = el.closest('.expanding_menu').attr('id');
    id = id.split('_')[1];

    /*if (action_type === "dtol" || action_type === "erga") {
                url = copoSamplesURL + id + "/view"
                document.location = url
    } else */
    if (action_type === 'release_study') {
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
}
