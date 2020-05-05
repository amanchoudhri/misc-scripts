import requests
from ratelimit import limits, sleep_and_retry
import pandas as pd
from urllib.parse import quote
from base64 import b64encode
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

# twitter development account API key and secret
API_KEY = config['APIs']['Twitter Key']
API_SECRET = config['APIs']['Twitter Secret']

# path to the TitleAbstractBodyMatches_drugs.csv file
DRUG_CSV_PATH = ''

# dir to which the output csv files should be downloaded
DOWNLOAD_PATH = ''

def encode(string):
    """URL encode a given string."""
    encoded_string = quote(string, safe = '')
    return encoded_string

class OAuthTokenHandler:
    def __init__(self, api_key, api_secret):
        self.api_key = encode(api_key)
        self.api_secret = encode(api_secret)
        self.token = self.bearer_token()
    
    def bearer_credentials(self):
        """Get the bearer credentials from the globally defined api key and api secret."""
        credentials = ':'.join((self.api_key, self.api_secret))
        cred_bytes = credentials.encode('utf-8')
        encoded_cred_bytes = b64encode(cred_bytes)
        encoded_creds = encoded_cred_bytes.decode('utf-8')

        return encoded_creds

    def request(self, url, data):
        """Make a request to the twitter API at 'url' with body 'data.'
 
        Arguments:
            url {str} -- resource URL to query
            data {dict} -- the data to send with the API request

        Returns:
            response -- the response to the HTTP request
        """
        auth = 'Basic ' + self.bearer_credentials()
        content_type = 'application/x-www-form-urlencoded;charset=UTF-8'
        response = requests.post(url,
            data = data,
            headers = {'Authorization': auth, 'Content-Type': content_type}
        )
        return response
    
    def bearer_token(self):
        """Generate a bearer token."""
        url = 'https://api.twitter.com/oauth2/token'
        data = {'grant_type': 'client_credentials'}
        json = self.request(url, data).json()
        token_type = json['token_type']
        if token_type != 'bearer':
            raise Exception(f'The token type should be "bearer." {token_type} was recieved.')

        return json['access_token']

    def invalidate_token(self, token):
        """Invalidate a given bearer token."""
        url = 'https://api.twitter.com/oauth2/invalidate_token'
        data = {'access_token': token}
        response = self.request(url, data)
        if response.status_code != 200:
            return False
        self.token = self.bearer_token()
        return True
    
    def authorization_headers(self):
        """Create the authorization headers for any API request."""
        auth = 'Bearer ' + self.token
        headers = {'Authorization': auth}
        return headers

FIFTEEN_MINUTES = 900
@sleep_and_retry
@limits(calls = 400, period = FIFTEEN_MINUTES)
def search(query, tokenHandler, num_tweets = 100, language = None):
    """Search twitter for a given query and return a list of the results.

    Arguments:
        query {str} -- drug name to be searched.
        tokenHandler {OAuthTokenHandler} -- handles OAuth protocol.

    Keyword Arguments:
        num_tweets {int} -- number of tweets to be returned for the query. (default: {3})
        lang {str} -- ISO language code for results. If None, return results in all languages. (default: {None})

    Returns:
        [list] -- list of the results for the search query.
    """
    search_url = 'https://api.twitter.com/1.1/search/tweets.json'
    headers = tokenHandler.authorization_headers()
    encoded_query = encode(query)
    params = {
        'q': encoded_query,
        'count': num_tweets,
        'tweet_mode': 'extended'
    }
    if language:
        params['lang'] = language

    response = requests.get(search_url, 
        params = params,
        headers = headers
    )
    statuses = response.json()['statuses']
    return statuses

def extract_data(drug, statuses):
    """Extracts the desired data from a list of twitter responses.

    Arguments:
        drug {str} -- the drug name that corresponds to the statuses.
        statuses {list} -- twitter statuses that were the result of searching for 'drug'.

    Returns:
        [list] -- a list of dictionaries containing the desired data for each tweet.
    """
    tweets = []
    for status in statuses:
        tweet = {
            'drug': drug,
            'tweet_id': status['id'],
            'user_id': status['user']['id'],
            'username': status['user']['screen_name'],
        }

        if status['retweeted'] == True:
            tweet['text'] = status['retweeted_status']['full_text']
        else:
            tweet['text'] = status['full_text']

        tweets.append(tweet)

    return tweets
        
def load_df(csv_path):
    """Generate a pandas.Series of drug names from the csv path."""
    dataframe = pd.read_csv(csv_path)
    drugs = dataframe['word'].unique()
    return drugs

def search_drugs(filename):
    """Search twitter for tweets relating to the drugs in the dataframe.

    Arguments:
        filename {str} -- name of the file to which the dataframe should be downloaded (_____.csv)
    """
    handler = OAuthTokenHandler(API_KEY, API_SECRET)
    drugs = load_df(DRUG_CSV_PATH)
    tweet_dataframe = []
    for drug in drugs:
        try:
            statuses = search(drug, handler)
        except KeyError:
            print('\nError: Rate limit exceeded.\n')
            break
        drug_tweets = extract_data(drug, statuses)
        tweet_dataframe = tweet_dataframe + drug_tweets

    tweet_dataframe = pd.DataFrame(tweet_dataframe)
    tweet_dataframe.to_csv(DOWNLOAD_PATH + filename)

def search_by_keyword(keyword, filename):
    """Search twitter by a specific keyword and save the tweets to a csv file.

    Arguments:
        keyword {str} -- the keyword to search by.
        filename {str} -- name of the file to which the dataframe should be downloaded (_____.csv)
    """
    handler = OAuthTokenHandler(API_KEY, API_SECRET)
    try:
        statuses = search(keyword, handler)
    except KeyError:
        print('\nError: Rate limit exceeded.\n')
        return
    tweets = extract_data(keyword, statuses)
    tweets = pd.DataFrame(tweets)
    tweets.to_csv(DOWNLOAD_PATH + filename)
