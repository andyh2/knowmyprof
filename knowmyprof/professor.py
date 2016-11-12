import requests
import json
import inflect
from collections import Counter
from itertools import chain, groupby
INSTRUCTOR_QUERY_EXP = "Composite(AA.AuN='{name}')"
INSTRUCTOR_UNI_QUERY_EXP = "And(Composite(AA.AuN='{name}'),Composite(AA.AfN='{university}'))"
EVALUATE_ENDPONT = 'https://api.projectoxford.ai/academic/v1.0/evaluate'
AUTH_HEADERS = {'Ocp-Apim-Subscription-Key': 'a620578e2cf4455b9ba5b5c419bcab26'}
ALL_ATTRIBUTES = ['Y','D','CC','ECC','AA.AuN','AA.AuId','AA.AfN','AA.AfId','F.FN','F.FId','J.JN','J.JId','C.CN','C.CId','RId','W','E']

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

def entities_for_query(name, university):
    query = query_for_instructor(name, university)
    params = {
        'expr': query,
        'model': 'latest',
        'count': 10,
        'offset': 0,
        'attributes': ALL_ATTRIBUTES
    }
    r = requests.get(EVALUATE_ENDPONT, params=params, headers=AUTH_HEADERS)
    print(params)
    response = json.loads(r.text)
    return [clean_entity(entity)
        for entity in response['entities']]

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

affiliation_name_from_res = lambda res: res['author'][0]['affiliation_name']
def group_results_by_uni(results):
    results = sorted(results, key=affiliation_name_from_res)
    return dict([(key, list(res)) for key, res in groupby(results, affiliation_name_from_res)])
def search(query, universities):
    results = list()
    for uni in universities:
        results += sorted(entities_for_query(query, uni),
            key=lambda entity: entity['date'],
            reverse=True)
    for res in results:
        if res.get('field'):
            res['field'] = [f['name'] for f in res['field']]

    grouped_results = group_results_by_uni(results)
    for uni, results in grouped_results.items():
        grouped_results[uni] = {'results': results, 'top_fields': top_fields(results)}
    return grouped_results

def top_fields(entities):
    print(entities[0]['field'])
    fields = chain.from_iterable(map(lambda e: e['field'], entities))
    counter = Counter(fields)

    common = [c[0] for c in counter.most_common(3)]
    if common:
        return (', '.join(common[:-1]) + ' and ' + common[-1]).title().replace(' And ', ' and ')
    else:
        return []