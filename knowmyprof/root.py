from flask import Flask, render_template, request
from . import academic_knowledge
import inflect
from .schools import SCHOOLS
app = Flask(__name__)
app.debug = True
@app.route('/')
def home():
  return render_template('index.html', universities=SCHOOLS)

@app.route('/university/<name>')
def university(name):
    name = name.replace('-', ' ')
    return render_template('university.html',
        histogram=academic_knowledge.histogram_for_uni(name),
        university=name.title())

UNIVERSITIES = ['university of california davis', 'university of california berkeley']
@app.route('/search')
def search():
  q = request.args.get('q').lower()
  results_by_uni = academic_knowledge.search_instructor(q, UNIVERSITIES)
  histogram_by_university = academic_knowledge.instructor_histogram_by_university(results_by_uni)
  overall_histogram = academic_knowledge.get_overall_histogram(histogram_by_university)
  year_count = academic_knowledge.year_count(overall_histogram)
  publication_count = academic_knowledge.publication_count(overall_histogram)
  return render_template('search.html',
    query=q,
    query_inflected=inflect.engine().plural(q),
    university=UNIVERSITIES[0],
    histogram_by_university=histogram_by_university,
    overall_histogram=overall_histogram,
    year_count=year_count,
    publication_count=publication_count,
    total_citations=academic_knowledge.total_citations(results_by_uni),
    api_results=results_by_uni)

