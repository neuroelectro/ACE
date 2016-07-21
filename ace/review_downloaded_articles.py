

__author__ = 'stripathy'

from ace import database

import sys
db = database.Database('sqlite')

import glob


from ace.scrape import *
import time


def get_article_html_by_pmid(pmid, journal_name, mode='browser'):
    scraper = Scraper('/tmp/articles')
    if mode == 'browser':
        scraper.mode = 'browser'
    else:
        scraper.mode = 'direct'
    scraper.journal = journal_name
    html = scraper.get_html_by_pmid(pmid, retmode='ref')
    return html


def check_misdownloaded_article(file_name, pmid=None, publisher = None):
    # works currently for PLoS and Frontiers
    if pmid:
        #bad_html = False
        sections = db.file_to_sections(file_name, pmid)
        with open(file_name, 'rb') as o:
            html_full_text = o.read()
            #bad_html = check_bad_html(html_full_text)
            only_abstract = only_abstract_avail(html_full_text, publisher)
        if only_abstract:
            print 'No article full text available for %s' % pmid
            return False
        elif sections:
            # i.e., can at least identify publisher from html and get doi
            return False
        # elif check_valid_article_sections(sections):
        #     return False
#         elif not bad_html:
#             return bad_html
        else:
            return True
    else:
        with open(file_name, 'rb') as o:
            html_full_text = o.read()
            return check_bad_html(html_full_text)


def only_abstract_avail(html_full_text, publisher = None):
    soup = BeautifulSoup(html_full_text, 'lxml')
    if publisher == 'Wiley':
        abstract_span = soup.find('span', string="Abstract")
        article_link = soup.find('a', string="Article")
        if abstract_span and not article_link:
            return True
        else:
            return False
    else:
        return False


def check_bad_html(html_full_text, publisher = None):

    soup = BeautifulSoup(html_full_text, 'lxml')
    if publisher == 'Wiley':
        abstract_span = soup.find('span', string="Abstract")
        article_span = soup.find('span', string="Article")

        if abstract_span:
            return False
        elif article_span:
            return False
        else:
            return True
    else:
        return False
    return False
    # works currently for PLoS and Frontiers
    t = soup.find('article')
    if not t:
        return True
    else:
        return False


def check_valid_article_sections(sections):
    if sections and 'methods' in sections and ('references' in sections or 'discussion' in sections):
        valid_sections = True
    else:
        valid_sections = False
    return valid_sections


def download_misdownloaded_articles(path, browser_mode = 'browser'):
    os.chdir(path)
    MIN_WAIT_TIME_BETWEEN_DOWNLOADS = 20 # seconds
    journal_name = re.split('/', path)[-2]
    file_name_list = [f for f in glob.glob("*.html")]
    #file_name_list = file_name_list[5500:6000]
    num_files = len(file_name_list)
    print 'Now checking journal %s ' % journal_name
    for i,file_name in enumerate(file_name_list):
        prog(i, num_files)
        pmid_str = re.search('\d+', file_name).group()
        if check_misdownloaded_article(file_name, pmid_str):
            print "article %s potentially misdownloaded, attempting to redownload " % file_name
            html = get_article_html_by_pmid(pmid_str, journal_name, browser_mode)
            sections = db.file_to_sections(file_name, pmid_str, html= html.encode('utf8'))
            if sections:
            #if sections and 'methods' in sections and ('references' in sections or 'discussion' in sections):
                valid_article = True
            else:
                valid_article = False
#             , metadata_dir=None, source_name=None, get_tables = False, html= None
            if valid_article:
                with open(file_name, 'wb') as f:
                    f.write(html.encode('utf8'))
                time.sleep(MIN_WAIT_TIME_BETWEEN_DOWNLOADS)
            else:
                print "article %s failed redownload, moving on" % file_name
        else:
            print "existing article %s is fine, moving on" % file_name


def prog(num,denom):
    fract = float(num)/denom
    hyphens = int(round(50*fract))
    spaces = int(round(50*(1-fract)))
    sys.stdout.write('\r%.2f%% [%s%s]' % (100*fract,'-'*hyphens,' '*spaces))
    sys.stdout.flush()