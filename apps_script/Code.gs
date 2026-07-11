/**
 * Division Health Card — Form upload handler.
 *
 * Bound to the intake Google Form (see docs/FORM_STRUCTURE.md — the exact
 * question titles below MUST match that Form exactly, or getResponse()
 * lookups here return nothing). On each submission:
 *   1. Rejects anything from an email not in ALLOWED_EMAILS (the personal
 *      Gmail account this Form lives on can't natively restrict who can
 *      respond the way a Workspace domain could — this is the enforcement
 *      instead; see docs/APPS_SCRIPT_SETUP.md).
 *   2. Copies the uploaded file to DHCUploads/<YYYY-MM>/<canonical name>,
 *      overwriting any previous file for that section+month. The original
 *      upload stays in the Form's own attachments folder as the audit
 *      trail (the Form's response sheet + that folder are never touched
 *      by this script) — see the module docstring in pipeline/drive.py
 *      for how the pipeline reads DHCUploads.
 *   3. Fires a GitHub repository_dispatch (type: data-upload) so the
 *      Data Pipeline workflow picks it up within seconds.
 *
 * No reminder emails, no other side effects — deliberately minimal.
 *
 * SETUP: see docs/APPS_SCRIPT_SETUP.md for the installable trigger and
 * Script Properties (GITHUB_PAT) this depends on. Neither is optional —
 * this script does nothing useful until both are done.
 */

// ── Configuration — keep in sync with pipeline_config.yaml by hand ─────────
// (Apps Script can't read the repo's YAML directly without extra plumbing;
// these three maps mirror pipeline_config.yaml's section keys, labels, and
// canonical_filename values. If you add/rename a section there, update
// here too — and regenerate the Form's "Section" dropdown to match.)

var ALLOWED_EMAILS = [
  // Replace with the actual ~5 office-staff Google account emails that
  // are allowed to submit this Form. Anything else is silently rejected
  // (logged, not processed) — see handleSubmit_() below.
  'branch1@example.com',
  'branch2@example.com',
];

var GITHUB_REPO = 'performancepapco/Division_Health_Report';

var SECTION_LABEL_TO_KEY = {
  'ECR — Revenue & Expenditure': 'ecr',
  'POSB — Accounts Opened/Closed': 'posb',
  'PLI — Policy Distribution': 'pli',
  'RPLI — Policy Distribution': 'rpli',
  'Booking — Product-wise': 'booking_productwise',
  'Booking — Book-type-wise (daily)': 'booking_booktypewise',
};

var SECTION_CANONICAL_FILENAME = {
  ecr: 'ECR.xlsx',
  posb: 'POSB.xlsx',
  pli: 'PLI.xlsx',
  rpli: 'RPLI.xlsx',
  booking_productwise: 'Booking_Productwise.csv',
  booking_booktypewise: 'Booking_BookTypewise.csv',
};

// 'April 2026' -> '2026-04', one fiscal year (Apr-26..Mar-27) — matches
// MONTH_ORDER in index.html. Extend when a new fiscal year starts.
var MONTH_LABEL_TO_ISO = {
  'April 2026': '2026-04', 'May 2026': '2026-05', 'June 2026': '2026-06',
  'July 2026': '2026-07', 'August 2026': '2026-08', 'September 2026': '2026-09',
  'October 2026': '2026-10', 'November 2026': '2026-11', 'December 2026': '2026-12',
  'January 2027': '2027-01', 'February 2027': '2027-02', 'March 2027': '2027-03',
};

var DHCUPLOADS_FOLDER_NAME = 'DHCUploads';

// Exact question titles from the Form — must match docs/FORM_STRUCTURE.md.
var Q_SECTION = 'Section';
var Q_MONTH = 'Reporting Month';
var Q_FILE = 'Upload your file';


/**
 * Installable trigger entry point — see docs/APPS_SCRIPT_SETUP.md for how
 * to wire this to the Form's "On form submit" event. Kept as a thin
 * wrapper around handleSubmit_() so errors are always logged with
 * context, never silently swallowed by an uncaught exception.
 */
function onFormSubmit(e) {
  try {
    handleSubmit_(e);
  } catch (err) {
    Logger.log('ERROR in onFormSubmit: ' + err + '\n' + (err.stack || ''));
  }
}


function handleSubmit_(e) {
  var email = e.response.getRespondentEmail();
  if (!email || ALLOWED_EMAILS.indexOf(email) === -1) {
    Logger.log('Rejected submission from unauthorized email: ' + (email || '(none collected)'));
    return;
  }

  var fields = readFields_(e.response);
  if (!fields.sectionLabel || !fields.monthLabel || !fields.fileId) {
    Logger.log('Rejected submission with missing field(s): ' + JSON.stringify(fields));
    return;
  }

  var sectionKey = SECTION_LABEL_TO_KEY[fields.sectionLabel];
  var monthIso = MONTH_LABEL_TO_ISO[fields.monthLabel];
  var canonicalName = SECTION_CANONICAL_FILENAME[sectionKey];

  if (!sectionKey || !monthIso || !canonicalName) {
    Logger.log('Rejected submission with unrecognized section/month: section="' +
      fields.sectionLabel + '" month="' + fields.monthLabel + '"');
    return;
  }

  var monthFolder = getOrCreateMonthFolder_(monthIso);
  copyIntoCanonicalPath_(fields.fileId, monthFolder, canonicalName);

  Logger.log('Accepted: section=' + sectionKey + ' month=' + monthIso + ' from=' + email);
  triggerGithubDispatch_(sectionKey, monthIso, email);
}


function readFields_(response) {
  var sectionLabel = null, monthLabel = null, fileId = null;
  response.getItemResponses().forEach(function (ir) {
    var title = ir.getItem().getTitle();
    if (title === Q_SECTION) {
      sectionLabel = ir.getResponse();
    } else if (title === Q_MONTH) {
      monthLabel = ir.getResponse();
    } else if (title === Q_FILE) {
      var ids = ir.getResponse(); // file-upload questions return an array of file IDs
      fileId = ids && ids.length ? ids[0] : null;
    }
  });
  return { sectionLabel: sectionLabel, monthLabel: monthLabel, fileId: fileId };
}


function getOrCreateMonthFolder_(monthIso) {
  var root = getOrCreateFolder_(DriveApp.getRootFolder(), DHCUPLOADS_FOLDER_NAME);
  return getOrCreateFolder_(root, monthIso);
}


function getOrCreateFolder_(parent, name) {
  var it = parent.getFoldersByName(name);
  if (it.hasNext()) return it.next();
  return parent.createFolder(name);
}


/**
 * Copies (not moves) the uploaded file to <monthFolder>/<canonicalName>,
 * replacing any file already there with that exact name — "latest
 * submission for a section+month overwrites the previous file" per spec.
 * Copying rather than moving means the original stays in the Form's own
 * attachments folder untouched, so the Form's response sheet remains a
 * complete audit trail even after this script renames/relocates things.
 */
function copyIntoCanonicalPath_(fileId, monthFolder, canonicalName) {
  var existing = monthFolder.getFilesByName(canonicalName);
  while (existing.hasNext()) {
    existing.next().setTrashed(true);
  }
  var uploaded = DriveApp.getFileById(fileId);
  uploaded.makeCopy(canonicalName, monthFolder);
}


function triggerGithubDispatch_(sectionKey, monthIso, uploaderEmail) {
  var token = PropertiesService.getScriptProperties().getProperty('GITHUB_PAT');
  if (!token) {
    Logger.log('ERROR: GITHUB_PAT is not set in Script Properties — see docs/APPS_SCRIPT_SETUP.md. ' +
      'File was copied into DHCUploads but the pipeline was NOT notified; ' +
      'it will still pick this up on tomorrow\'s daily cron run.');
    return;
  }

  var url = 'https://api.github.com/repos/' + GITHUB_REPO + '/dispatches';
  var payload = {
    event_type: 'data-upload',
    client_payload: {
      section: sectionKey,
      month: monthIso,
      uploader_email: uploaderEmail,
    },
  };
  var options = {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'Authorization': 'Bearer ' + token,
      'Accept': 'application/vnd.github+json',
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  };

  var resp = UrlFetchApp.fetch(url, options);
  var code = resp.getResponseCode();
  if (code >= 200 && code < 300) {
    Logger.log('GitHub dispatch sent OK (HTTP ' + code + ')');
  } else {
    Logger.log('GitHub dispatch FAILED (HTTP ' + code + '): ' + resp.getContentText() +
      ' — file was still copied into DHCUploads; the daily cron run will pick it up.');
  }
}
