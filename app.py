from flask import Flask, render_template
from scrapeNProcess import *

app = Flask(__name__)

@app.route('/')
def home():
    articles = fetch_and_process_articles()
    return render_template('home.html', articles=articles)
