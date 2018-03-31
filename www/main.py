#!/usr/bin/env python3
from flask import Flask, render_template
from flaskext.markdown import Markdown

app = Flask(__name__)
Markdown(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit')
def submit():
    return render_template('submit.html', title='submit')

@app.route('/vote')
def vote():
    return render_template('vote.html', title='vote')

@app.route('/about')
def about():
    return render_template('about.html', title='about')
