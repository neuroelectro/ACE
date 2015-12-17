# coding: utf-8
from __future__ import unicode_literals  # use unicode everywhere
import re
import requests
from time import sleep
import config
from bs4 import BeautifulSoup
import logging
import os
from random import random, shuffle
from selenium import webdriver
import selenium.webdriver.support.ui as ui
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options

logger = logging.getLogger(__name__)


def get_url(url, delay=0.0, verbose=False):
    headers = {'User-Agent': config.USER_AGENT_STRING}
    sleep(delay)
    try:
        r = requests.get(url, headers=headers, timeout=5.0)
    except requests.exceptions.RequestException as e:
        sleep(delay * 3)
        r = requests.get(url, headers=headers, timeout=10.0)
    return r.text


def get_pmid_from_doi(doi):
    ''' Query PubMed for the PMID of a paper based on its doi. We need this
    for some Sources that don't contain the PMID anywhere in the artice HTML.
    '''
    data = get_url(
        'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=%s[aid]' % doi)
    pmid = re.search('\<Id\>(\d+)\<\/Id\>', data).group(1)
    return pmid

def pmc_id_to_pmid(pmc_id_list):
    ''' Query PubMedCentral for the PMID of a paper based on its 
    PubMedCentral ID. 
    '''
    if len(pmc_id_list) == 0:
        pmc_id_list = [pmc_id_list]
    # base url for id resolver service, requires 'tool', name of tool; and 'email', name of user's email
    query_base = 'http://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?tool=ACE&email=stripat3@gmail.com&ids=%s&idtype=pmcid'

    list_index = 0
    max_pmcs = 200 # max number of pmcs that can be returned from id resolver service
    num_pmcs = len(pmc_id_list)
    pmid_list = []

    while list_index < num_pmcs: # while loop to loop through input pmc ids
        curr_last_index = min(list_index+max_pmcs,num_pmcs)
        curr_pmc_ids = pmc_id_list[list_index:curr_last_index]
        id_list_str = ','.join(curr_pmc_ids)
        query = query_base % id_list_str
        data = get_url(query, 2)
        soup = BeautifulSoup(data)
        for record in soup.find_all('record'):
            if record.has_attr('pmid'):
                pmid_list.append(record['pmid'])
        list_index = list_index + max_pmcs
    return pmid_list

def get_pubmed_metadata(pmid, parse=True, store=None, save=True):
    ''' Get PubMed metadata for article.
    Args:
        pmid: The article's PubMed ID
        parse: if True, parses the text and returns a dictionary. if False, returns raw text.
        store: optional string path to PubMed metadata files. If passed, first checks the passed
            folder for the corresponding ID, and only queries PubMed if not found.
        save: if store is passed, save is True, and the file does not already exist, 
            will save the result of the new PubMed query to the store.
    '''
    if store is not None:
        md_file = os.path.join(store, pmid)

    if store is not None and os.path.exists(md_file):
        logger.info("Retrieving metadata from file %s..." % os.path.join(store, pmid))
        text = open(md_file).read()
    else:
        logger.info("Retrieving metadata for PubMed article %s..." % str(pmid))
        text = get_url(
            'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=%s&retmode=text&rettype=medline' % pmid)
        if store is not None and save and text is not None:
            if not os.path.exists(store):
                os.makedirs(store)
            open(md_file, 'w').write(text)

    return parse_PMID_text(text) if (parse and text is not None) else text


def parse_PMID_text(text, doi=None):
    ''' Take text-format PubMed metadata and convert it to a dictionary
    with standardized field names. '''
    data = {}
    text = re.sub('\n\s+', ' ', text)
    patt = re.compile(ur'([A-Z]+)\s*-\s+(.*)')
    for m in patt.finditer(text):
        field, val = m.group(1), m.group(2)
        if field in data:
            data[field] += ('; %s' % val)
        else:
            data[field] = val

    # Extra processing
    if doi is None:
        if 'AID' in data and '[doi]' in data['AID']:
            doi = filter(lambda x: 'doi' in x, data['AID'].split('; '))[0].split(' ')[0]
        else:
            doi = ''
    year = data['DP'].split(' ')[0]
    authors = data['AU'].replace(';', ',')
    for field in ['MH', 'AB', 'JT']:
        if field not in data:
            data[field] = ''

    metadata = {
        'authors': authors,
        'citation': data['SO'],
        'comment': data['AB'],
        'doi': doi,
        'keywords': '',
        'mesh': data['MH'],
        'pmid': data['PMID'],
        'title': data['TI'],
        'abstract': data['AB'],
        'journal': data['JT'],
        'year': year
    }
    return metadata


''' Class for journal Scraping. The above free-floating methods should 
probably be refactored into this class eventually. '''
class Scraper:

    def __init__(self, store):

        self.store = store


    def search_pubmed(self, journal, search_db='pubmed', retmax=100000, savelist=None):
        '''Args:
            journal: journal name to search
            retmax: max number of search hits to return
            db: when 'pubmed', executes search using pubmed as search database
                    when 'pmc', executes search using pubmed central - allowing more 
                    fine-grained search capabilities
        '''
        # query = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=(%s[Journal])+AND+(%s[Date+-+Publication])&retmax=%s" % (journal, str(year), str(retmax))
        journal = journal.replace(' ', '+')
        search = '+%s' % self.search if self.search is not None else ''

        # if searching pubmed and not pubmed central, then specify to only find journal articles
        if search_db == 'pubmed':
            article_type = '+journal+article[pt]+'
        else:
            article_type = ''

        query = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=%s&term=("%s"[Journal]%s%s)&retmax=%s' % (search_db, journal, article_type,search, str(retmax))
        logger.info("Query: %s" % query)
        doc = get_url(query)
        if savelist is not None:
            outf = open(savelist, 'w')
            outf.write(doc)
            outf.close()
        return doc


    def get_html(self, url):

        ''' Get HTML of full-text article. Uses either browser automation (if mode == 'browser')
        or just gets the URL directly. '''
        if self.mode == 'browser':

            try:
                options = webdriver.ChromeOptions()
                options.add_extension(config.ADBLOCK_ABS_PATH)
                driver = webdriver.Chrome(chrome_options=options)
            except Exception:
                driver = webdriver.Chrome()

            driver.get(url)

            # Check for URL substitution and get the new one if it's changed
            url = driver.current_url  # After the redirect from PubMed
            html = driver.page_source
            new_url = self.check_for_substitute_url(url, html)

            if url != new_url:
                driver.get(new_url)
                if self.journal.lower() in ['human brain mapping',
                                            'european journal of neuroscience',
                                            'brain and behavior','epilepsia', 'glia', 'j comp neurol',
                                            'eur j neurosci', 'hippocampus', 'j physiol']:
                    sleep(0.5 + random() * 1)
                    try:
                        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'relatedArticles')))
                    except TimeoutException:
                        print "Loading Wiley page took too much time!"

                # Sometimes we get annoying alerts (e.g., Flash animation
                # timeouts), so we dismiss them if present.
                try:
                    alert = driver.switch_to_alert()
                    alert.dismiss()
                except:
                    pass

                html = driver.page_source

            ## Uncomment this next line to scroll to end. Doesn't seem to actually help.
            # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            ## Uncomment next line and insert ID to search for specific element.
            # driver.find_element_by_id('relatedArticles').send_keys('\t')
            # This next line helps minimize the number of blank articles saved from ScienceDirect,
            # which loads content via Ajax requests only after the page is done loading. There is 
            # probably a better way to do this...
            sleep(1.5)
            driver.quit()
            return html

        else:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1464.0 Safari/537.36'}
            r = requests.get(url, headers=headers)
            # For some journals, we can do better than the returned HTML, so get the final URL and 
            # substitute a better one.
            url = self.check_for_substitute_url(r.url, r.text)
            if url != r.url:
                r = requests.get(url, headers=headers)
                # XML content is usually misidentified as ISO-8859-1, so we need to manually set utf-8.
                # Unfortunately this can break other documents. Need to eventually change this to inspect the 
                # encoding attribute of the document header.
                r.encoding = 'utf-8'
            return r.text




    def get_html_by_pmid(self, pmid, retmode='ref'):

        query = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=pubmed&id=%s&cmd=prlinks&retmode=%s" % (pmid, retmode)
        logger.info(query)
        return self.get_html(query)

    def check_for_substitute_url(self, url, html):
        ''' For some journals/publishers, we can get a better document version by modifying the 
        URL passed from PubMed. E.g., we can get XML with embedded tables from PLoS ONE instead of 
        the standard HTML, which displays tables as images. For some journals (e.g., Frontiers),  
        it's easier to get the URL by searching the source, so pass the html in as well. '''

        j = self.journal.lower()
        try:
            if j == 'plos one':
#                 doi_part = re.search('article\/(info.*)', url).group(1)
#                 return 'http://www.plosone.org/article/fetchObjectAttachment.action?uri=%s&representation=XML' % doi_part
#             elif j == 'plos computational biology':
#                 doi_part = re.search('article\/(info.*)', url).group(1)
#                 return 'http://www.ploscompbiol.org/article/fetchObjectAttachment.action?uri=%s&representation=XML' % doi_part
#             elif j == 'plos biology':
#                 doi_part = re.search('article\/(info.*)', url).group(1)
#                 return 'http://www.plosbiology.org/article/fetchObjectAttachment.action?uri=%s&representation=XML' % doi_part
                doi_part = re.search('article\?id\=(.*)', url).group(1)
                return 'http://journals.plos.org/plosone/article/asset?id=%s.XML' % doi_part
            elif j in ['human brain mapping', 'european journal of neuroscience',
                       'brain and behavior', 'epilepsia', 'journal of neuroimaging',
                       'glia', 'hippocampus', 'eur j neurosci', 'j comp neurol', 'j physiol']:
                url_part = url.replace('abstract', 'full').split(';')[0]
                url_part = url_part.replace('.com/', '.com/wol1/')
                return url_part
            elif j == 'journal of cognitive neuroscience':
                return url.replace('doi/abs', 'doi/full')
            elif j.startswith('frontiers in'):
                return re.sub('(full|abstract)\/*$', 'xml\/nlm', url)
            elif 'sciencedirect' in url:
                return url + '?np=y'
            elif 'springer.com' in url:
                return url + '/fulltext.html'
            else:
                return url
        except Exception, e:



            return url


    def retrieve_journal_articles(self, journal, delay=None, mode='browser', search=None,
                                search_db='pubmed',limit=None, overwrite=False, min_pmid=None, 
                                save_metadata=True):

        ''' Try to retrieve all PubMed articles for a single journal that don't 
        already exist in the storage directory.
        Args:
            journal: The name of the journal (as it appears in PubMed).
            delay: Mean delay between requests.
            mode: When 'browser', use selenium to load articles in Chrome. When 
                'direct', attempts to fetch the HTML directly via requests module.
            search: An optional search string to append to the PubMed query.
                Primarily useful for journals that are not specific to neuroimaging.
            search_db: When 'pubmed' uses Pubmed as database for article searching.
                When 'pmc' uses Pubmed Central as search database - allowing 
                more fine-grained article search capabilities
            limit: Optional max number of articles to fetch. Note that only new articles 
                are counted against this limit; e.g., if limit = 100 and 2,000 articles 
                are found in PubMed, retrieval will continue until 100 new articles 
                have been added.
            overwrite: When True, all articles returned from PubMed query will be 
                fetched, irrespective of whether or not they already exist on disk.
            min_pmid: When a PMID is provided, only articles with PMIDs greater than 
                this will be processed. Primarily useful for excluding older articles 
                that aren't available in full-text HTML format.
            save_metadata: When True, retrieves metadata from PubMed and saves it to 
                the pubmed/ folder below the root storage folder.
        '''
        self.journal = journal
        self.delay = delay
        self.mode = mode
        self.search = search
        self.search_db = search_db
        query = self.search_pubmed(journal, search_db)
        soup = BeautifulSoup(query)
        ids = [t.string for t in soup.find_all('id')]
        
        # if search_db is pubmed central, then convert pmc_ids to pmids
        if search_db == 'pmc':
            #pmid_list = [pmc_id_to_pmid(int(pmc_id)) for pmc_id in ids]
            pmid_list = pmc_id_to_pmid(ids)
            ids = pmid_list

        shuffle(ids)
        logger.info("Found %d records.\n" % len(ids))

        # Make directory if it doesn't exist
        journal_path = os.path.join(self.store, 'html', journal)
        if not os.path.exists(journal_path):
            os.makedirs(journal_path)

        articles_found = 0

        for id in ids:

            if min_pmid is not None and int(id) < min_pmid: continue
            if limit is not None and articles_found >= limit: break
            
            logger.info("Processing %s..." % id)
            filename = '%s/%s.html' % (journal_path, id)

            if not overwrite and os.path.isfile(filename): 
                logger.info("\tAlready exists! Skipping...")
                continue

            # Save the HTML, try up to 5 times due to timeouts
            for i in range(0, 5):
                try:
                    doc = self.get_html_by_pmid(id)
                except Exception, e:
                    logger.info("Article id: %s has timed out, attempt number %s" % (id, i + 1))
                    if delay is not None:
                        sleep_time = random() * float(delay*2)
                        sleep(sleep_time)
                else:
                    break
             
            if doc:
                outf = open(filename, 'w')
                # Still having encoding issues with some journals (e.g., 
                # PLoS ONE). Why???
                outf.write(doc.encode('utf-8'))
                outf.close()
                articles_found += 1

                # Insert random delay until next request.
                if delay is not None:
                    sleep_time = random() * float(delay*2)
                    sleep(sleep_time)


