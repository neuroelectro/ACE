''' GLOBAL SETTINGS '''

# When True, all Exceptions will be suppressed. When False, Exception 
# messages will be printed out.
SILENT_ERRORS = False


''' DATABASE SETTINGS '''
# Adapter to use--either 'mysql' or 'sqlite'
SQL_ADAPTER = 'mysql'

# SQLite path (when using sqlite adapter)
SQLITE_URI = 'sqlite:///ace.db'

# MySQL configuration
MYSQL_USER = 'ace'
MYSQL_PASSWORD = 'CHANGEME'
MYSQL_DB = 'ace_test'

# When True, any processed articles will be saved to DB, whether or not they 
# contain any extracted activations. When False, only articles from which 
# at least one activation was extracted will be saved. Note that if this is set
# to False, processing will be much slower, since every article not already in
# the DB will be parsed, even if it contains no activations and has been
# previously processed.
SAVE_ARTICLES_WITHOUT_ACTIVATIONS = True

# By default, ACE will ignore any articles that already exist in the DB 
# when processing new HTML files. If OVERWRITE is set to True, ACE will 
# always overwrite existing records. This is useful when the extraction 
# code has improved substantially and you want to re-extract all data, 
# but should otherwise be left off for the sake of efficiency.
OVERWRITE_EXISTING_ROWS = False


''' SOURCE PROCESSING SETTINGS '''

# If True, will exercise greater care when parsing (e.g., when estimating 
# number of columns in table, will check every row in the table and take the 
# max instead of just checking the first row). This is generally desirable,
# but will result in slower processing.
CAREFUL_PARSING = True

# Sometimes tables have rows that can't be processed--usually because of malformed
# HTML or XML (e.g., failure to close a <td> tag). Such problems will always be 
# logged, but if IGNORE_BAD_ROWS is True, the row will be skipped and execution
# will continue gracefully. When False, any errors will be re-raised,
# terminating execution.
IGNORE_BAD_ROWS = True

# Whether or not to ignore tables that appear to be missing a label for at 
# least one column. This doesn't happen much, and in practice most tables with 
# missing labels appear to genuinely have empty columns that are ignored
# anyway, so this should be left off unless problems arise.
EXCLUDE_TABLES_WITH_MISSING_LABELS = False




''' SCRAPING/PARSING SETTINGS '''

#USER_AGENT_STRING = 'Mozilla/5.0 (Windows NT 6.2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1464.0 Safari/537.36'
USER_AGENT_STRING = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'
ADBLOCK_ABS_PATH = '/usr/local/bin/Adblock-Plus_v1.9.4.crx'