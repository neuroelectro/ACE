# In this example we lift the database object to mine sections of
# interest and return them as a dictionary. 

# Note that due to copyright restrictions, articles can't
# be included in this package, so you'll need to replace PATH_TO_FILES
# with something that works.

import ace
from ace import database

import sys

# Uncomment the next line to seem more information
ace.set_logging_level('info')

# Change this to a valid path to a set of html files.
#PATH_TO_FILES = "/home/mbelmadani/ace/html/*/*"
filename = PATH_TO_FILE 

# "/home/mbelmadani/ace/html/PLoS ONE/
# 21347239.html"

db = database.Database('sqlite')

sections = db.file_to_sections(filename)

for k in sections.keys():
    print "Section:", k, "with", sys.getsizeof(sections[k]), "bytes of data"
