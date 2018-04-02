#!/usr/bin/env python3
import os
import uuid
import random
import json
from flask import Flask, render_template, flash, redirect, url_for, request
from flaskext.markdown import Markdown
from flask_uploads import UploadSet, IMAGES, configure_uploads, patch_request_class
import redis

# Admin token
admin_token = str(uuid.uuid4())

# Flask
app = Flask(__name__)
app.jinja_options = { 'trim_blocks': True, 'lstrip_blocks': True }
app.secret_key = str(uuid.uuid4())

# Markdown
Markdown(app)

# Redis
r = redis.Redis(decode_responses=True)

# Uploads
screenshots = UploadSet('screenshots', ('jpg', 'jpeg', 'png', 'bmp'))
app.config['UPLOADED_SCREENSHOTS_DEST'] = os.path.join(app.root_path, 'static/screenshots')
configure_uploads(app, screenshots)
patch_request_class(app, 16 * 1024 * 1024)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST' and 'screenshot' in request.files:
        key = request.form.get('key')
        if not r.exists(key):
            message, success = 'Invalid key.', False
        else:
            try:
                filename = screenshots.save(request.files['screenshot'])
            except:
                message, success = 'Invalid file.', False
            else:
                user = json.loads(r.get(key))
                old_screenshot = user.get('screenshot')
                try:
                    os.remove(screenshots.path(old_screenshot))
                except:
                    pass
                user['screenshot'] = filename
                r.set(key, json.dumps(user))
                message, success = 'Uploaded!', True
        if 'from_form' in request.form:
            flash(message, success)
            return redirect(url_for('vote' if success else 'submit'))
        else:
            return message + '\n'
    else:
        return render_template('submit.html', title='submit')

@app.route('/vote')
def vote():
    if request.method == 'POST' and 'for' in request.form:
        key = request.form.get('key')
        if not r.exists(key):
            message, success = 'Invalid key.', False
        else:
            voted_for = request.get('for')
            user = json.loads(r.get(key))
            user['vote'] = voted_for
            r.set(key, json.dumps(user))
            message, success = 'You voted for %s.' % voted_for, True
        return message + '\n'
    else:
        users = []
        for key in r.keys():
            user = json.loads(r.get(key))
            if os.path.isfile(screenshots.path(user.get('screenshot', ''))):
                users.append({ 'nickname': user['nickname'], 'screenshot': screenshots.url(user['screenshot']) })
        random.shuffle(users)
        return render_template('vote.html', title='vote', users=users)

@app.route('/admin', methods=['POST'])
def admin():
    if request.form.get('token') != admin_token:
        return 'Wrong token.'
    action = request.form.get('action').lower()
    if action in ('add', 'get_key'):
        nickname = request.form.get('nickname')
        if not nickname:
            return 'No nickname specified.'
        if action == 'add':
            key = str(uuid.uuid4())
            r.set(key, json.dumps({ 'nickname': nickname }))
            return '%s successfully added.' % nickname
        elif action == 'get_key':
            for key in r.keys():
                user = json.loads(r.get(key))
                if user['nickname'] == nickname:
                    return key
            return ''

if __name__ == '__main__':
    print('Admin token:', admin_token)
    app.run(debug=True)
