# misc-scripts
A showcase of some of the miscellaneous scripts I've created that are too small for their own repos. From oldest to newest:

  - **hnRNP_K_binding_predictor.ipynb:** Creating a CNN in PyTorch to predict the binding sites of the protein hnRNPK from human DNA sequences alone.
  - **enrich_metadata.py:** looks through the metadata of the [CORD-19 Dataset](https://www.kaggle.com/allen-institute-for-ai/CORD-19-research-challenge), identifies entries without a listed journal name, and uses the DOI information of articles to fill in those entries.
  - **umls_search.py:** queries the [Unified Medical Language System (UMLS) database](https://www.nlm.nih.gov/research/umls/index.html); may be used as a first-pass dictionary approach for a named object recognition pipeline for biological terms in COVID-19 articles.
  - **twitter_search.py:** takes in search parameters either from a user input or from a [CoronaWhy](coronawhy.org)-curated database of drug names found in COVID-19 papers, then saves the resultant tweets to a csv file for use with sentiment analysis and polarity detection. 
