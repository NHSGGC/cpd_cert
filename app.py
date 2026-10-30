#!/usr/bin/env python3
"""Small local browser interface around the existing CPD modules."""

import html
import json
import shutil
import urllib.parse
import webbrowser
from cgi import FieldStorage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from googleapiclient.discovery import build

from auth import authenticate_google_credentials
from main import process_job
from settings import SCOPES
from transformation import modify_pdf


JOBS_DIR = Path('jobs')
DEFAULTS = {
    'job_id': '', 'job_name': '', 'spreadsheet_id': '',
    'range_name': 'Form Responses 1!A:Z', 'name_col': 'B',
    'gdc_num_col': 'C', 'email_col': 'A', 'name_x': '3.4',
    'name_y': '3.2', 'gdc_x': '3.4', 'gdc_y': '3.5',
    'sender_email': 'secretary.wosbspd@gmail.com',
    'email_subject': 'Your CPD certificate',
    'email_body': 'Please find your CPD certificate attached.',
    'output_filename': '',
}

PAGE = """<!doctype html><html><head><meta charset=utf-8><title>CPD Certificate Sender</title>
<style>body{{font:16px system-ui;max-width:900px;margin:2rem auto;padding:0 1rem}}label{{display:block;margin:.6rem 0;font-weight:600}}input,textarea{{display:block;box-sizing:border-box;width:100%;padding:.5rem}}textarea{{height:8rem}}button,.button{{display:inline-block;background:#175c9c;color:white;border:0;border-radius:4px;padding:.65rem 1rem;text-decoration:none;font-weight:600;cursor:pointer}}button.danger{{background:#a72b2b}}.connect{{padding:1rem;border:2px solid #175c9c;border-radius:6px;background:#f3f8fc;margin:1rem 0 1.5rem}}.connect h2{{margin-top:0}}.editing{{padding:1rem;border:2px solid #9a6410;border-radius:6px;background:#fff8e8;margin:1rem 0}}.editing strong{{font-size:1.1rem}}.jobs{{padding:.8rem;background:#f2f5f7;margin:.5rem 0}}.message{{padding:.8rem;background:#eaf4ff}}.error{{background:#ffecec}}.row{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}form.inline{{display:inline}}@media(max-width:650px){{.row{{grid-template-columns:1fr}}}}</style></head>
<body><h1>CPD Certificate Sender</h1>{message}
<section class=connect><h2>1. Connect Google account</h2><p>Authorize the Google account that reads form responses and sends certificates.</p><form method=post action=/authorize><button>Connect / refresh Google account</button></form></section>
<h2>2. Choose a saved job</h2>{jobs}<h2>3. {heading}</h2>{edit_notice}
<form method=post action=/save enctype=multipart/form-data><input type=hidden name=job_id value='{job_id}'>
<div class=row><label>Job name<input required name=job_name value='{job_name}'></label><label>Template PDF {template_note}<input type=file accept=application/pdf name=template {template_required}></label></div>
<div class=row><label>Spreadsheet ID<input required name=spreadsheet_id value='{spreadsheet_id}'></label><label>Sheet range<input required name=range_name value='{range_name}'></label></div>
<label>Output PDF filename (optional)<input name=output_filename value='{output_filename}' placeholder='Defaults to cpd_job_name.pdf'></label>
<div class=row><label>Name column<input required name=name_col value='{name_col}'></label><label>GDC number column<input required name=gdc_num_col value='{gdc_num_col}'></label><label>Email column<input required name=email_col value='{email_col}'></label><label>Expected sender email<input required type=email name=sender_email value='{sender_email}'></label></div>
<div class=row><label>Name X (inches)<input required type=number step=.05 name=name_x value='{name_x}'></label><label>Name Y (inches)<input required type=number step=.05 name=name_y value='{name_y}'></label><label>GDC X (inches)<input required type=number step=.05 name=gdc_x value='{gdc_x}'></label><label>GDC Y (inches)<input required type=number step=.05 name=gdc_y value='{gdc_y}'></label></div>
<label>Email subject<input required name=email_subject value='{email_subject}'></label><label>Email body<textarea required name=email_body>{email_body}</textarea></label><button>Save job</button></form></body></html>"""


def slug(name):
    cleaned = ''.join(c.lower() if c.isalnum() else '-' for c in name).strip('-')
    return '-'.join(filter(None, cleaned.split('-'))) or 'job'


def load_job(identifier):
    return json.loads((JOBS_DIR / slug(identifier) / 'settings.json').read_text())


def remove_job(identifier):
    job = load_job(identifier)
    shutil.rmtree(JOBS_DIR / slug(job['job_id']))
    return job


def list_jobs():
    JOBS_DIR.mkdir(exist_ok=True)
    return [json.loads(path.read_text()) for path in sorted(JOBS_DIR.glob('*/settings.json'))]


def save_job(values, template=None):
    name = values['job_name'].strip()
    identifier = slug(values.get('job_id') or name)
    directory = JOBS_DIR / identifier
    directory.mkdir(parents=True, exist_ok=True)
    template_path = directory / 'template.pdf'
    if template:
        upload_path = directory / 'template-upload.pdf'
        upload_path.write_bytes(template)
        shutil.move(str(upload_path), str(template_path))
    if not name or not template_path.exists():
        raise ValueError('A job name and template PDF are required.')
    default_output_filename = 'cpd_{}.pdf'.format(identifier.replace('-', '_'))
    output_filename = values.get('output_filename', '').strip() or default_output_filename
    if Path(output_filename).name != output_filename:
        raise ValueError('Output PDF filename must be a filename, not a path.')
    settings = {
        'job_id': identifier, 'job_name': name,
        'spreadsheet_id': values['spreadsheet_id'].strip(),
        'range_name': values['range_name'].strip(),
        'name_col': values['name_col'].strip().upper(),
        'gdc_num_col': values['gdc_num_col'].strip().upper(),
        'email_col': values['email_col'].strip().upper(),
        'input_pdf_path': str(template_path),
        'output_pdf_path': str(directory / output_filename),
        'name_offset_inches': {'x': float(values['name_x']), 'y': float(values['name_y'])},
        'gdc_offset_inches': {'x': float(values['gdc_x']), 'y': float(values['gdc_y'])},
        'sender_email': values['sender_email'].strip().lower(),
        'email_subject': values['email_subject'].strip(),
        'email_body': values['email_body'].strip(),
        'cache_path': str(directory / 'cache.pickle'),
    }
    (directory / 'settings.json').write_text(json.dumps(settings, indent=2) + '\n')
    return settings


def form_values(job=None):
    if not job:
        return dict(DEFAULTS)
    return {
        **job, 'name_x': job['name_offset_inches']['x'],
        'name_y': job['name_offset_inches']['y'],
        'gdc_x': job['gdc_offset_inches']['x'],
        'gdc_y': job['gdc_offset_inches']['y'],
        'output_filename': Path(job['output_pdf_path']).name,
    }


def render(selected=None, message='', error=False):
    blocks = []
    for job in list_jobs():
        identifier = html.escape(job['job_id'], quote=True)
        cache_exists = Path(job['cache_path']).exists()
        blocks.append("<div class=jobs><b>{}</b> — sent cache: {} &nbsp; "
                      "<a class=button href='/?edit={}'>Edit</a> "
                      "<form class=inline method=post action=/test><input type=hidden name=job_id value='{}'><button>Joe Bloggs test</button></form> "
                      "<form class=inline method=post action=/dry-run><input type=hidden name=job_id value='{}'><button>Dry run</button></form> "
                      "<form class=inline method=post action=/send-test><input type=hidden name=job_id value='{}'><button>Send one test to me</button></form> "
                      "<form class=inline method=post action=/run><input type=hidden name=job_id value='{}'><button>Send pending</button></form> "
                      "<form class=inline method=post action=/delete onsubmit=\"return confirm('Remove this job, its template and its sent cache? This cannot be undone.');\"><input type=hidden name=job_id value='{}'><button class=danger>Remove job</button></form></div>".format(
                          html.escape(job['job_name']), 'yes' if cache_exists else 'not started',
                          identifier, identifier, identifier, identifier, identifier, identifier))
    values = {key: html.escape(str(value), quote=True)
              for key, value in form_values(selected).items()}
    values.update({
        'jobs': ''.join(blocks) or '<p>No jobs created.</p>',
        'heading': 'Edit job' if selected else 'Create job',
        'template_note': '(leave blank to keep existing)' if selected else '',
        'template_required': '' if selected else 'required',
        'edit_notice': ("<div class=editing><strong>Editing saved job: {}</strong>"
                        "<p>Saving will update this job. Its existing sent cache will be preserved.</p>"
                        "<a class=button href='/'>Cancel editing / create a new job</a></div>".format(
                            html.escape(selected['job_name']))) if selected else '',
        'message': ("<p class='message{}'>{}</p>".format(' error' if error else '', html.escape(message))) if message else '',
    })
    return PAGE.format(**values).encode()


def credentials_for(job=None):
    creds = authenticate_google_credentials(scopes=SCOPES)
    account = build('gmail', 'v1', credentials=creds).users().getProfile(userId='me').execute()['emailAddress'].lower()
    if job and job['sender_email'] and account != job['sender_email']:
        raise ValueError('Connected as {}, but this job expects {}.'.format(account, job['sender_email']))
    return creds, account


class Handler(BaseHTTPRequestHandler):
    def send_page(self, body, status=200, content_type='text/html; charset=utf-8'):
        self.send_response(status); self.send_header('Content-Type', content_type); self.end_headers(); self.wfile.write(body)

    def redirect(self, message):
        self.send_response(303); self.send_header('Location', '/?message=' + urllib.parse.quote(message)); self.end_headers()

    def fields(self):
        return FieldStorage(fp=self.rfile, headers=self.headers,
                            environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': self.headers.get('Content-Type', '')})

    def do_GET(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        selected = load_job(query['edit'][0]) if query.get('edit') else None
        self.send_page(render(selected, query.get('message', [''])[0]))

    def do_POST(self):
        try:
            form = self.fields()
            if self.path == '/authorize':
                _, account = credentials_for(); self.redirect('Connected as ' + account); return
            identifier = form.getfirst('job_id', '')
            if self.path == '/save':
                values = {key: form.getfirst(key, '') for key in DEFAULTS}
                upload = form['template'] if 'template' in form else None
                template = upload.file.read() if upload is not None and upload.filename else None
                job = save_job(values, template); self.redirect('Saved ' + job['job_name']); return
            job = load_job(identifier)
            if self.path == '/delete':
                job = remove_job(identifier)
                self.redirect('Removed job ' + job['job_name'])
                return
            if self.path == '/test':
                output = str(JOBS_DIR / job['job_id'] / 'joe-bloggs-test.pdf')
                modify_pdf('Joe Bloggs', '12345678', job['input_pdf_path'], output,
                           job['name_offset_inches'], job['gdc_offset_inches'])
                data = Path(output).read_bytes(); self.send_response(200); self.send_header('Content-Type', 'application/pdf'); self.send_header('Content-Disposition', 'attachment; filename=joe-bloggs-test.pdf'); self.end_headers(); self.wfile.write(data); return
            if self.path == '/dry-run':
                creds, _ = credentials_for(job); result = process_job(creds, job, dry_run=True)
                recipients = ', '.join(result['recipients']) or 'none'
                self.redirect('Dry run: {} certificate(s) generated; no emails sent and cache unchanged. Recipients: {}'.format(result['would_send'], recipients)); return
            if self.path == '/send-test':
                creds, account = credentials_for(job)
                result = process_job(creds, job, redirect_to=account, max_sends=1)
                if result['sent']:
                    self.redirect('Test sent to {} for intended recipient {}. Sent cache unchanged.'.format(account, result['recipients'][0]))
                else:
                    self.redirect('No pending recipients were available for a test.')
                return
            if self.path == '/run':
                creds, _ = credentials_for(job); result = process_job(creds, job)
                self.redirect('{} sent; {} already sent.'.format(result['sent'], result['already_sent'])); return
            self.send_page(b'Not found', 404)
        except Exception as error:
            self.send_page(render(message=str(error), error=True), 400)


if __name__ == '__main__':
    server = ThreadingHTTPServer(('127.0.0.1', 8765), Handler)
    print('CPD Certificate Sender: http://127.0.0.1:8765')
    webbrowser.open('http://127.0.0.1:8765')
    server.serve_forever()
