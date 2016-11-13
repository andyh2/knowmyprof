import requests
import json
import inflect
from collections import Counter, OrderedDict
from itertools import chain, groupby
import logging
import time

logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s') # you need to initialize logging, otherwise you will not see anything from requests
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

UNIVERSITY_QUERY_EXP = "Composite(AA.AfN='{name}')"
INSTRUCTOR_QUERY_EXP = "Composite(AA.AuN='{name}')"
INSTRUCTOR_UNI_QUERY_EXP = "And(Composite(AA.AuN='{name}'),Composite(AA.AfN='{university}'))"
EVALUATE_ENDPONT = 'https://api.projectoxford.ai/academic/v1.0/evaluate'
HISTOGRAM_ENDPOINT  = 'https://api.projectoxford.ai/academic/v1.0/calchistogram'
AUTH_HEADERS = {'Ocp-Apim-Subscription-Key': '5eea2e3f1d08402bb10aae22a8672a1d  '}
ALL_ATTRIBUTES = ['Ti','Y','D','CC','ECC','AA.AuN','AA.AuId','AA.AfN','AA.AfId','F.FN','F.FId','J.JN','J.JId','C.CN','C.CId','RId','W','E']
ATTRIBUTE_NAMES_BY_CODE = {
    'logprob': 'logprob',
    'Ti': 'title',
    'Y': 'year',
    'D': 'date',
    'CC': 'citation_count',
    'ECC': 'estimated_citation_count',
    'AA': 'author',
    'AuN': 'name',
    'AuId': 'id',
    'AfN': 'affiliation_name',
    'AfId': 'affiliation_id',
    'F': 'field',
    'FN': 'name',
    'FId': 'id',
    'J': 'journal',
    'JN': 'name',
    'JId': 'id',
    'conference': 'conference_series',
    'CN': 'name',
    'CId': 'id',
    'RId': 'reference_id',
    'W': 'words',
    'E': 'extended_metadata',
    'DN': 'display_name',
    'S': 'sources',
    'Ty': 'type',
    'U': 'url',
    'VFN': 'venue_full_name',
    'VSN': 'venue_short_name',
    'V': 'volume',
    'I': 'issue',
    'FP': 'first_page',
    'LP': 'last_page',
    'DOI': 'digital_object_identifier'}

def clean_entity(entity):
    """
    Doing what microsoft should do for me
    """
    if not isinstance(entity, dict):
        return entity

    cleaned_entity = dict()

    for code, attribute in entity.items():
        code = ATTRIBUTE_NAMES_BY_CODE.get(code, code)
        if isinstance(attribute, dict):
            attribute = clean_entity(attribute)
        elif isinstance(attribute, list):
            attribute = [clean_entity(attr) for attr in attribute]
        elif code == 'extended_metadata':
            attribute = clean_entity(json.loads(attribute))
        cleaned_entity[code] = attribute

    return cleaned_entity

def query_for_instructor(name, university):
    if university:
        return INSTRUCTOR_UNI_QUERY_EXP.format(name=name, university=university)
    else:
        return INSTRUCTOR_QUERY_EXP.format(name=name)

def entities_for_query(query, count=10):
    params = {
        'expr': query,
        'model': 'latest',
        'count': count,
        'offset': 0,
        'attributes': ALL_ATTRIBUTES
    }

    r = requests.get(EVALUATE_ENDPONT, params=params, headers=AUTH_HEADERS)
    response = json.loads(r.text)
    return [clean_entity(entity)
        for entity in response['entities']]

def clean_histogram(histograms):
    return next(h for h in histograms if h['attribute'] == 'Y')
def histogram_for_query(query, count=50, attributes=ALL_ATTRIBUTES):
    params = {
        'expr': query,
        'model': 'latest',
        'count': count,
        'offset': 0,
        'attributes': attributes
    }
    r = requests.get(HISTOGRAM_ENDPOINT, params=params, headers=AUTH_HEADERS)

    response = json.loads(r.text)
    if 'error' in response:
        raise Exception('Rate limit error')
    return [histogram for histogram in response['histograms']
        if histogram['attribute'] == 'Y']


def histogram_for_uni(name):
    query = UNIVERSITY_QUERY_EXP.format(name=name)
    histograms = histogram_for_query(query, attributes=['Y'])[0]['histogram']
    return sorted([{'year': h['value'], 'publications': h['count']} for h in histograms],
        key=lambda h: h['year'])

affiliation_name_from_res = lambda res: res['author'][0].get('affiliation_name', '')
def group_results_by_uni(results):
    results = sorted(results, key=affiliation_name_from_res)
    grouped_results = [(key, list(res)) for key, res in groupby(results, affiliation_name_from_res)
        if key]

    return OrderedDict(sorted(grouped_results, key=lambda results: max(map(lambda res: res.get('date'), results[1])), reverse=True))

def extract_field_names_in_results(results):
    for res in results:
        if res.get('field'):
            res['field'] = [f['name'] for f in res['field']]
def search_instructor(name, universities):
    results = list()
    for uni in universities:
        query = query_for_instructor(name, uni)
        results += sorted(entities_for_query(query, count=1000),
            key=lambda entity: entity['date'],
            reverse=True)

    extract_field_names_in_results(results)
    grouped_results = group_results_by_uni(results)
    for uni, results in grouped_results.items():
        grouped_results[uni] = {'results': results, 'top_fields': top_fields(results)}
    return grouped_results

def search_university(name):
    results = list()
    for uni in universities:
        query = UNIVERSITY_QUERY_EXP.format(uni)
        results += sorted(entities_for_query(query, count=1000),
            key=lambda entity: entity['date'],
            reverse=True)
    extract_field_names_in_results(results)
    return results

def instructor_histogram_by_university(results_by_uni):
    histograms_by_university = dict()
    for uni, results in results_by_uni.items():
        years = list(map(lambda res: res['year'], results['results']))
        counter = Counter(years) # histogram is year by count
        histogram_samples = [{'year': year, 'publications': count}
            for year, count in counter.items()]
        histogram_samples = [next((s for s in histogram_samples if s['year'] == year), {'year': year, 'publications': 0})
            for year in range(min(years), max(years) + 1)]

        histograms_by_university[uni] = sorted(histogram_samples, key=lambda s: s['year'])

    return histograms_by_university

def get_overall_histogram(histogram_by_university):
    return list(chain(*[results for uni, results in histogram_by_university.items()]))

def year_count(overall_histogram):
    years = [h['year'] for h in overall_histogram]
    return max(years) - min(years)

def publication_count(overall_histogram):
    return sum([h['publications'] for h in overall_histogram])

def top_fields(entities):
    fields = chain.from_iterable(map(lambda e: e.get('field', []), entities))
    counter = Counter(fields)

    common = [c[0] for c in counter.most_common(3)]
    if common:
        return (', '.join(common[:-1]) + ' and ' + common[-1]).title().replace(' And ', ' and ')
    else:
        return []