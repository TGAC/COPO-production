import json
import subprocess
import sys
import time

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, expect

from common.utils.helpers import get_env

# EDP profile form values agreed for the Sapio test instance. The JIRA ticket
# number is deliberately not here: it becomes the Sapio ProjectName, so each
# run makes its own (see edp_jira_ticket_number()) to find its project in
# Sapio unambiguously.
EDP_PROFILE_FIELDS = {
    'sample_type': 'Tissue',
    'library_type': 'Illumina premade library',
    'container_type': 'Plate',
    'no_of_samples': 1,
    'budget_user': 'copo-playwright-test-user',
    # An invalid email address is used for the `customer_emails` field in the EDP profile
    # instead of the project team's development/test email address to avoid sending 
    # actual emails during tests.
    # Emails sent to addresses ending with `.invalid` can never be delivered.
    'customer_emails': 'copo-playwright@example.invalid',
}


def edp_jira_ticket_number():
    return f'copo-playwright-test-{int(time.time())}'


def run_django_shell(code):
    result = subprocess.run(
        [sys.executable, 'manage.py', 'shell', '-c', code],
        cwd='/copo',
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def delete_profile_by_title(title):
    # Profile.validate_and_delete() is a hard delete that deliberately
    # *refuses* to delete (returns False, no exception) if any sample,
    # submission, or datafile document still references the profile --
    # exactly the state every submission test leaves behind (a saved
    # sample, and for the full journeys a real ENA submission too). That's
    # sensible production behaviour (don't orphan tracked submission data),
    # but test cleanup needs to actually clear the profile, so clear the
    # referencing collections first via the same handle_dict the DAL itself
    # uses, then let validate_and_delete's guard pass cleanly.
    #
    # enaFileTransfer matters here too, even though validate_and_delete()
    # doesn't check it: EnaFileTransfer.get_pending_transfers() only claims
    # ONE pending record globally (across every profile) per 10s beat tick
    # (a deliberate throttle -- common/dal/copo_da.py), in unspecified Mongo
    # order. Confirmed live: leaving 4 leftover pending records per aborted
    # run meant later runs' real file transfers queued behind a growing
    # backlog of dead ones and took minutes longer than they should have.
    #
    # validate_and_delete() also runs the profile type's post-delete hook,
    # which for an EDP profile deletes its Sapio project -- so this cleans up
    # Sapio too, provided the SAPIO_* settings reach this container (see
    # run_playwright_tests.sh).
    run_django_shell(
        'from common.dal.profile_da import Profile\n'
        'from common.dal.copo_base_da import handle_dict\n'
        f"profile_ids = [str(r['_id']) for r in Profile().get_all_records() if r.get('title') == {title!r}]\n"
        'for pid in profile_ids:\n'
        "    for collection in ('sample', 'submission', 'datafile', 'singlecell', 'enaFileTransfer'):\n"
        "        handle_dict[collection].delete_many({'profile_id': pid})\n"
        '    Profile().validate_and_delete(pid)\n'
    )


def poll_sample_accession(profile_id, timeout=1200, interval=10):
    # process_pending_sample_submission (Celery beat, every 10s) is what
    # actually calls real ENA -- there's no websocket/event this test can
    # wait on directly, so poll the DB the same way the table's own redraw
    # does under the hood. Real EBI latency is unknown up front, hence the
    # generous timeout rather than trusting a short default.
    # manage.py shell -c prints an import banner (+ blank separator line)
    # before running this code, and a bare .strip().splitlines()[-N:] on the
    # combined stdout is fragile: printing the final field as an empty
    # string (the common case for 'error') makes its trailing blank line
    # get silently swallowed by strip(), shifting every field left by one.
    # A single delimited marker line sidesteps that entirely.
    code = (
        'from common.dal.sample_da import Sample\n'
        f"samples = Sample(profile_id={profile_id!r}).execute_query({{'profile_id': {profile_id!r}}})\n"
        's = samples[0] if samples else {}\n'
        "print('POLL_RESULT:' + '|'.join([s.get('status', ''), s.get('biosampleAccession', ''), s.get('error', '')]))\n"
    )
    deadline = time.time() + timeout
    status = ''
    while time.time() < deadline:
        marker_line = next(
            (line for line in run_django_shell(code).splitlines() if line.startswith('POLL_RESULT:')),
            'POLL_RESULT:||',
        )
        status, accession, error = marker_line[len('POLL_RESULT:'):].split('|')
        if status == 'accepted' and accession:
            return accession
        if status == 'rejected' or error:
            raise AssertionError(f'Sample submission to ENA failed: status={status!r} error={error!r}')
        time.sleep(interval)
    raise AssertionError(f'Timed out waiting for a real BioSample accession (last status={status!r})')


def read_sapio_project(project_id, project_fields=(), sample_fields=()):
    # Reads directly from Sapio and not from COPO's copy in Mongo database, 
    # so that a test can confirm what actually was recorded/saved in the LIMS. 
    # Uses the adapter's sample loader so 'samples under this 
    # project' means exactly what COPO means by it when submitting.
    #
    # Returns {'exists': bool, 'project': {field: value}, 'samples': [{field: value}, ...]}.
    code = (
        'import json\n'
        'from src.apps.ei_edp.utils.lims.sapio.adapter import SapioAdapter\n'
        'from src.apps.ei_edp.utils.lims.sapio.datamanager import Sapio\n'
        f'project_id = {project_id!r}\n'
        'records = Sapio().dataRecordManager.query_data_records(\n'
        "    data_type_name='Project', data_field_name='C_ProjectIdentifier', value_list=[project_id]\n"
        ').result_list\n'
        "result = {'exists': bool(records), 'project': {}, 'samples': []}\n"
        'if records:\n'
        f"    result['project'] = {{f: records[0].get_field_value(f) for f in {list(project_fields)!r}}}\n"
        "    result['samples'] = [\n"
        f'        {{f: s.get_field_value(f) for f in {list(sample_fields)!r}}}\n'
        '        for s in SapioAdapter()._load_project_samples(project_id)\n'
        '    ]\n'
        "print('SAPIO_RESULT:' + json.dumps(result, default=str))\n"
    )
    marker_line = next(
        line for line in run_django_shell(code).splitlines() if line.startswith('SAPIO_RESULT:')
    )
    return json.loads(marker_line[len('SAPIO_RESULT:'):])


def _open_new_profile_form(page, profile_type):
    page.goto('/copo')
    # Tour first: its overlay can sit on top of (and block clicking into)
    # the cookie/GDPR modals on a completely fresh page load.
    dismiss_tour_if_present(page)
    dismiss_onboarding_modals(page)
    # ...and again after: when a startup modal *is* open, the tour holds off
    # until it closes (waitForInitialModals() in tour-handler.js) and only
    # then starts — after the first check above has already given up. Left
    # in place, its overlay intercepts the '+' click below.
    dismiss_tour_if_present(page)

    # The main '+' button creates a profile of whatever type is currently
    # selected in this dropdown — select it before opening the dialog,
    # rather than inside it.
    page.select_option('#profileType', profile_type)
    page.click('.new-component-template')


def _close_profile_form_if_open(page):
    # Whether the dialog auto-closes after a successful save appears to be
    # genuinely non-deterministic (same code path passes reliably elsewhere,
    # fails here) rather than a fixed delay we can just wait out — so don't
    # trust it. Force it closed the same way dismiss_tour_if_present() forces
    # the tour overlay closed: direct DOM removal, not a native close
    # mechanism. Safe here since the profile is already confirmed created
    # (profile_card visible, above) before we touch the dialog at all.
    if page.locator('.modal.in').count():
        page.evaluate(
            "document.querySelectorAll('.modal.in').forEach(el => { el.classList.remove('in'); el.remove(); }); "
            "document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());"
        )

    dismiss_tour_if_present(page)


def create_biodata_profile(page, title, description):
    # Both title and description must be at least 20 characters — the app
    # rejects a short title client-side with 'Profile title must be at
    # least 20 characters.' (found the hard way; same rule for description).
    _open_new_profile_form(page, 'biodata')

    page.fill('#copo\\.profile\\.title', title)
    page.fill('#copo\\.profile\\.description', description)
    page.click('#btnFormSave')

    profile_card = page.locator('.panel-heading', has_text=title)
    # Confirmed via a failed run's trace (2026-08-21): the create POST to
    # /copo/copo_forms/ had already returned 200 and the profile row existed
    # in Mongo well before this assertion gave up at the default 5s timeout --
    # the save itself isn't slow or flaky, only the client-side re-render of
    # the new card sometimes lags behind it. Give that render more room.
    expect(profile_card).to_be_visible(timeout=15000)

    _close_profile_form_if_open(page)
    return profile_card


def create_edp_profile(
    page,
    title,
    description,
    *,
    sample_type,
    library_type,
    container_type,
    no_of_samples,
    jira_ticket_number,
    budget_user,
    customer_emails,
):
    # Saving an EDP profile is not local-only: post_save_edp_profile()
    # creates a Sapio project (plus its samples and plates) and stores the
    # project's identifier back on the profile, and the 'Sample type'
    # dropdown's options are themselves loaded from Sapio when the form
    # opens. Every caller therefore needs the Sapio test instance reachable.
    #
    # Returns (profile_card, profile_id, sapio_project_id).
    _open_new_profile_form(page, 'ei_edp')

    page.fill('#copo\\.profile\\.title', title)
    page.fill('#copo\\.profile\\.description', description)
    page.select_option('#copo\\.profile\\.sample_type', sample_type)
    page.select_option('#copo\\.profile\\.library_type', library_type)
    # <option> values are lower-case ('plate'/'tube'); select by the visible
    # label so callers can pass what the user sees.
    page.select_option('#copo\\.profile\\.container_type', label=container_type)
    page.fill('#copo\\.profile\\.no_of_samples', str(no_of_samples))
    page.fill('#copo\\.profile\\.jira_ticket_number', jira_ticket_number)
    page.fill('#copo\\.profile\\.budget_user', budget_user)
    page.fill('#copo\\.profile\\.customer_emails', customer_emails)

    # Check the save's response rather than only the card appearing: a
    # Sapio sync failure still saves the COPO profile (and renders its card)
    # but reports a non-success status here.
    with page.expect_response(
        lambda r: 'copo_forms' in r.url and r.request.method == 'POST', timeout=120000
    ) as response_info:
        page.click('#btnFormSave')
    feedback = response_info.value.json().get('action_feedback', {})
    assert feedback.get('status') == 'success', f'EDP profile save failed: {feedback}'

    profile_card = page.locator('.panel-heading', has_text=title)
    # The Sapio sync happens inside the save request, and the card's
    # re-render has been seen to take well past create_biodata_profile()'s
    # 15s budget (one exploratory run never showed it within 60s at all,
    # the next showed it within 8s).
    expect(profile_card).to_be_visible(timeout=60000)

    _close_profile_form_if_open(page)

    # The card's title <span> carries the profile id; the Sapio project id
    # sits in the card's hidden 'View more details' popover content, so
    # read it with text_content() rather than waiting for it to be visible.
    profile_id = profile_card.locator('.row-title span').first.get_attribute('id')
    sapio_project_id = (page.locator(f'#sapio_project_id_{profile_id}').text_content() or '').strip()
    return profile_card, profile_id, sapio_project_id


def delete_profile(page, title):
    profile_card = page.locator('.panel-heading', has_text=title)
    # Opens a popover with Edit/Delete actions for this specific card.
    profile_card.locator('.profile-ellipsis').click()
    page.click('#deleteProfileBtn')

    # The confirm button's id is a randomly generated UUID each time — the
    # 'dialog_confirm' class is the stable part.
    page.click('button.dialog_confirm')

    # A profile with actual sample/component data (as opposed to an empty
    # one) appears to take longer to delete server-side — default 5s wasn't
    # enough for that case in practice.
    expect(page.locator('.panel-heading', has_text=title)).not_to_be_visible(timeout=20000)


def upload_manifest(page, file_path):
    # Both the sample and single-cell manifest upload dialogs bind their
    # #file input's 'change' listener inside the same click handler that
    # kicks off an async $.load(url) to fetch the dialog's content —
    # the .find('#file').on('change', ...) line runs synchronously right
    # after, before that content (including the real #file element) has
    # arrived. So the listener never actually attaches, confirmed live via
    # jQuery._data(el, 'events') showing no 'change' handler even seconds
    # after opening the dialog and setting files. This isn't a test
    # flakiness workaround — it's a real bug in the app's JS that
    # set_input_files' native change event can never work around, no
    # matter how long the test waits. Call the app's upload_spreadsheet()
    # function directly instead, bypassing the broken event wiring — same
    # function a working 'change' event would have called.
    page.locator('.modal.in #file').set_input_files(file_path)
    page.evaluate("upload_spreadsheet(document.querySelector('.modal.in #file').files[0])")


def fill_and_submit_login_form(page, username, password):
    page.goto('/accounts/login/')
    page.fill('#id_login', username)
    page.fill('#id_password', password)
    page.click('button[type=submit]')


def dismiss_tour_if_present(page):
    # The app auto-starts a Shepherd.js guided tour (e.g. 'Getting started'
    # right after navigating to /copo, 'Profile components' after creating
    # a profile) whose overlay intercepts clicks on the real page underneath
    # until dismissed. Neither Escape nor clicking the tour's 'End tour'
    # text reliably closes every tour variant across different pages (tried
    # both, both flaked) — force-remove the overlay elements directly
    # instead. Safe here since dismissing an unrelated onboarding tour isn't
    # something any test is actually verifying.
    #
    # wait_for(state='visible') rather than an instant count() check: the
    # tour fades in via animation that isn't guaranteed to have finished
    # yet, so an instant check can race it and see 'not present' just
    # before it appears.
    try:
        page.locator('.shepherd-modal-is-visible').wait_for(state='visible', timeout=3000)
    except PlaywrightTimeoutError:
        pass
    else:
        page.evaluate(
            "document.querySelectorAll('.shepherd-element, .shepherd-modal-overlay-container')"
            '.forEach(el => el.remove())'
        )


def dismiss_onboarding_modals(page):
    # Neither modal is guaranteed to appear (cookie consent is per-browser-
    # context; the GDPR/email modal only shows when the user's email is
    # blank), so both are handled defensively rather than assumed. Needed
    # even for storage_state-authenticated pages: cookies/localStorage from
    # the cached session don't guarantee the cookie modal was dismissed for
    # every fresh context built from it.
    #
    # Using wait_for(state='visible') rather than an instantaneous
    # is_visible() check: the modals fade in via a JS-triggered animation
    # that isn't guaranteed to have finished by the time networkidle fires,
    # so an instant check can race the animation and see 'not visible' just
    # before it appears. The short timeout + catch just means 'never showed
    # up' — this only observes, so it's safe to call even when a modal
    # (like the GDPR form below) shouldn't be submitted without filling it in
    # first.
    page.wait_for_load_state('networkidle')

    try:
        page.locator('#acceptCookies').wait_for(state='visible', timeout=3000)
    except PlaywrightTimeoutError:
        pass
    else:
        page.click('#acceptCookies')

    try:
        page.locator('#submit').wait_for(state='visible', timeout=3000)
    except PlaywrightTimeoutError:
        pass
    else:
        page.fill('#emaddres', 'browser-test-user@example.invalid')
        page.check('#gdpr_check')
        page.click('#submit')
        page.wait_for_load_state('networkidle')
