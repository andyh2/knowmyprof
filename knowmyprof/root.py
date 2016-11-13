from flask import Flask, render_template, request
from . import professor
import inflect

app = Flask(__name__)
app.debug = True
@app.route('/')
def home():
  return render_template('index.html')

@app.route('/university/<name>')
def university(name):
    name = name.replace('-', ' ')
    return render_template('university.html',
        histogram=professor.histogram_for_uni(name),
        university=name.title())

UNIVERSITIES = ['university of california davis', 'university of california berkeley']
@app.route('/search')
def search():
  q = request.args.get('q').lower()
  results_by_uni = professor.search_instructor(q, UNIVERSITIES)
  histogram_by_university = professor.instructor_histogram_by_university(results_by_uni)
  overall_histogram = professor.get_overall_histogram(histogram_by_university)
  year_count = professor.year_count(overall_histogram)
  publication_count = professor.publication_count(overall_histogram)
  return render_template('search.html',
    query=q,
    query_inflected=inflect.engine().plural(q),
    university=UNIVERSITIES[0],
    histogram_by_university=histogram_by_university,
    overall_histogram=overall_histogram,
    year_count=year_count,
    publication_count=publication_count,
    api_results=results_by_uni)

