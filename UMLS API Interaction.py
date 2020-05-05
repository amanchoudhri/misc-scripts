import requests
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
API_KEY = config['APIs']['UMLS']

# Get the URL for the Ticket Granting Ticket (TGT)
# Valid for 8 hours. Needed to obtain a Service Ticket
def get_tgt_url():
    params = {'apikey': API_KEY}
    r = requests.post('https://utslogin.nlm.nih.gov/cas/v1/api-key', params).text
    # TGT URLs are enclosed in the following manner in the response text:
    # <form action="{TGT URL}" method="POST">
    link_start = r.find('action="') + len('action="')
    link_end = r.find('" method')
    url = r[link_start:link_end]
    return url

# Get service ticket (ST), which is needed per API request
def get_service_ticket(tgt_url):
    params = {'service': 'http://umlsks.nlm.nih.gov'}
    r = requests.post(tgt_url, params)
    # If the TGT is invalid, get a new one
    if r.status_code == 500:
        url = get_tgt_url()
        return get_service_ticket(url)
    else:
        return r.text

def search(*terms, search_type='words'):
    """search() takes in a list of terms and returns a dict with the top 3
    results (the name of the result and the CUI, which is a UMLS identifier) from each search.
    Format: {'term1': {search_type: [{'name': result1, 'cui':CUI}, {}, ...]}, 'term2': [{}, {}, ...], ...}
    search_type (str):
        - 'words': breaks a search term into its component parts, or words,
                   and retrieves all concepts containing any of those words.

        - 'exact': retrieves only concepts that include a synonym that exactly matches the search term.

        - 'approximate': applies lexical variant generation rules to the search term.
                         generally results in expanded retrieval of concepts
                         ('cold' => cold, chronic obstructive lung disease, COLDs)"""
    if search_type not in ['words', 'exact', 'approximate']:
        print('{} is not a valid search type!'.format(search_type))
        return
    else:
        results = {term: {search_type: []} for term in terms}
        tgt_url = get_tgt_url()
        for term in terms:
            params = {'string': term, 'searchType': search_type, 'ticket': get_service_ticket(tgt_url), 'pageSize': 3}
            r = requests.get('https://uts-ws.nlm.nih.gov/rest/search/current', params).json()
            if r['result']['results'][0]['name'] == 'NO RESULTS' and ' ' not in term:
                approx_search_results, _ = search(term, search_type='approximate')
                results[term]['approximate'] = approx_search_results[term]['approximate']
                del results[term][search_type]
            else:
                for result in r['result']['results']:
                    results[term][search_type].append({'name': result['name'], 'cui': result['ui']})
        return results, search_type

def pretty_print(results, type_called):
    try:
        for term in results:
            # results[term] returns {search_type: [{'name': name, 'cui': CUI}, {}...]}
            # get the search_type key and typecast from dictKeys object to a list, then get the element from the list
            # dictKeys['words'] ==> ['words'] ==> 'words'
            s_type = list(results[term].keys())[0]
            display_str = []
            for result_ in results[term][s_type]:
                display_str.append('{}, {}'.format(result_['name'], result_['cui']))
            # check whether the search type is approx because there were no results
            if s_type == 'approximate' and s_type != type_called:
                print('{}: No results with type {}'.format(term, type_called))
                print('    - Approximate results: {}'.format(' | '.join(display_str)))

            else:
                print('{}: {}'.format(term, ' | '.join(display_str)))
    # pretty_print throws a TypeError if search() receives an invalid search_type
    except TypeError:
        pass

search_results, search_type = search('Interferon-alpha 2A', 'Interferon alpha 2A', 'Interferon-alpha-2A',
                        'IFNalpha2A', 'IFN alpha 2a', 'Hu-IFN- alpha A [2a]', 'IFN-α 2a', 'IFNα 2a',
                        'Peginterferon alfa-2a', 'Pegasys', search_type='words')
pretty_print(search_results, search_type)
