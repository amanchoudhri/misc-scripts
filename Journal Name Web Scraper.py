import pandas
from urllib.parse import quote
import requests
import xml.etree.ElementTree as ET

METADATA_PATH = '/Users/aman/Downloads/metadata.csv'
apis = [('https://api.crossref.org/works/{}', 'crossref'), ('https://api.medra.org/metadata/{}', 'medra')]
preprint_doi_count = 0
not_found_list = []
invalid_doi_list = []

def get_journal(api, response):
    # inputs the response to an api request (Response) and the api name (str)
    # outputs the journal (str)
    if api == 'crossref':
        try:
            # crossref lists the journal as a list under 'container-title': i.e. ['CNS Oncology']
            journal = response.json()['message']['container-title'][0]
            return journal
        # IndexError thrown when 'container-title' for the article is [], meaning the article is likely preprint
        # see https://www.biorxiv.org/content/10.1101/001727v1 for example
        except IndexError:
            global preprint_doi_count
            preprint_doi_count += 1

    elif api == 'medra':
        # mEDRA returns metadata in XML format
        root = ET.fromstring(response.content)
        # each element is under an xmlns namespace
        namespace = '{http://www.editeur.org/onix/DOIMetadata/2.0}'
        # TitleText is the element under which the journal is stored
        journal = root.find('.//{}TitleText'.format(namespace)).text
        return journal

def get_url(r):
    # inputs Response from a DOI.org API fetch request
    # DOI returns a json file with a two-element list stored under the key 'values'
    # one element points to some 'HS_ADMIN' information, and the other is the desired URL information
    # in rare cases, the order of these two elements is reversed, so list_index checks for that
    list_index = 1 if r.json()['values'][0]['type'] != 'URL' else 0
    article_url = r.json()['values'][list_index]['data']['value']
    return article_url

def doi_to_journal(doi):
    # inputs a doi string, finds and returns journal name using crossref or medra
    for i, (link, api) in enumerate(apis):
        try:
            encoded_doi = quote(doi, safe='')
            response = requests.get(link.format(encoded_doi))

            if response.status_code == 404:
                response.raise_for_status()

            journal = get_journal(api, response)

            return journal

        # 404 from any of the APIs
        except requests.exceptions.HTTPError:
            # if the program has already looked on all other apis, check if it's registered on doi.org
            if i + 1 == len(apis):
                r = requests.get('https://doi.org/api/handles/{}'.format(encoded_doi))
                # DOI.org returns a response code of 100 if the Handle (DOI) is not found
                if r.json()['responseCode'] != 100:
                    # if the DOI points to an article in either biorxiv or medrxiv (which a ton seem to)
                    # increment the count of preprint_dois by 1
                    article_url = get_url(r)
                    if 'rxiv.org' in article_url:
                        global preprint_doi_count
                        preprint_doi_count += 1
                        if 'biorxiv' in article_url: return 'bioRxiv'
                        elif 'medrxiv' in article_url: return 'medRxiv'
                    # a pretty common journal that's not in any of the API registries I've found
                    if 'jthoracdis.com' in article_url:
                        return 'Journal of Thorasic Disease'
                    else:
                        # append the doi and article url of every article not found to not_found_list
                        global not_found_list
                        not_found_list.append((doi, article_url))

                else:
                    global invalid_doi_list
                    invalid_doi_list.append(doi)

metadata = pandas.read_csv(METADATA_PATH)

# select rows from metadata where the journal is null and the doi is not null,
# then take the doi column entry. This is used for doi_to_journal() only.
articles_doi = metadata.loc[(metadata['journal'].isna()) & (metadata['doi'].isna() == False), 'doi']

# There was some strange issue with the .isna() condition and copy/view, so
# this selects the indices of all the articles of interest
rows_to_modify = list(articles_doi.index.values)
metadata.loc[rows_to_modify, 'journal'] = articles_doi.apply(lambda doi: doi_to_journal(doi))

journals_added = len(rows_to_modify) - (len(not_found_list) + len(invalid_doi_list) + preprint_doi_count)
print('{} DOIs searched'.format(len(rows_to_modify)))
print('  -  {} Valid Journal Names NOT Found: {}'.format(len(not_found_list), not_found_list))
print('  -  {} Valid Journal Names Found'.format(journals_added))
print('  -  {} Pre-Print Articles'.format(preprint_doi_count))
print('  -  {} Invalid DOIs: {}'.format(len(invalid_doi_list), invalid_doi_list))

metadata.to_csv(METADATA_PATH)
