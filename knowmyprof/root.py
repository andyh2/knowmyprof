from flask import Flask, render_template, request
from . import professor
import inflect

app = Flask(__name__)
app.debug = True
@app.route('/')
def home():
  return render_template('index.html')

UNIVERSITIES = ['university of california davis', 'university of california berkeley']
@app.route('/search')
def search():
  q = request.args.get('q')
  api_results = professor.search(q, UNIVERSITIES)

  return render_template('search.html',
    query=q,
    query_inflected=inflect.engine().plural(q),
    university=UNIVERSITIES[0],
    api_results=api_results)

