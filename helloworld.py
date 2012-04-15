# Python imports
import cgi
import datetime
import urllib
import webapp2
import logging
import jinja2
import os

jinja_environment = jinja2.Environment(
  loader = jinja2.FileSystemLoader(os.path.dirname(__file__)))

# Google imports
from google.appengine.ext import db
from google.appengine.api import users

# DB:  A single transaction can apply to multiple entities, so long 
# as the entities are descended from a common ancestor. 
# In designing your data model, you should determine which entities you need to be
# able to process in the same transaction. Then, when you create those entities, place
# them in the same entity group by declaring them with a common ancestor.
    
# TODO the tutorial states: the rate at which you can write to the same entity group
# is limited to 1 write to the entity group per second.  WHY?

# guestbook_name is a parameter in the URL; the parent of a Greeting is
# a guestbook: 'Guestbook: name=Foo barbaz'
# The parent is used as a placeholder for transaction and consistency purposes. 
# Objects that share a common ancestor belong to the same entity group. 

# Ancestor Queries, as shown here, are strongly consistent with the High
# Replication datastore. Queries that span entity groups are eventually
# consistent. If we omitted the ancestor from this query there would be a
# slight chance that Greeting that had just been written would not show up
# in a query.
#
# The only supported queries are those whose performance scales with the size
# of the result set (as opposed to the data set). (Better scalability)

    # Sample query for something which uses the Author filter    
#     another_greeting = db.GqlQuery("SELECT * "
#                             "FROM Greeting "
#                             "WHERE ANCESTOR IS :1 "
#                             "AND Author = :2 "
#                             "ORDER BY date DESC LIMIT 10 ",
#                             'joe',
#                             'test@example.com')
#     logging.debug("Another greeting using vars(): %s" % vars(another_greeting))                            


class Greeting(db.Model):
  """Models an individual Guestbook entry with an author, content, and date."""
  author = db.UserProperty()
  content = db.StringProperty(multiline=True)     # can contain newlines
  date = db.DateTimeProperty(auto_now_add=True)   # auto-time on creation unless provided

def guestbook_key(guestbook_name=None):
  """Constructs a datastore key for a Guestbook entity with guestbook_name."""
  return db.Key.from_path('Guestbook', guestbook_name or 'default_guestbook')

class MainPage(webapp2.RequestHandler):
  def get(self):
    guestbook_name=self.request.get('guestbook_name')
    greetings_query = Greeting.all().ancestor(
      guestbook_key(guestbook_name)).order('-date')
    greetings = greetings_query.fetch(10)
  
    if users.get_current_user():
      url = users.create_logout_url(self.request.uri)
      url_linktext = 'Logout'
    else:
      url = users.create_login_url(self.request.uri)
      url_linktext = 'Login'
  
    template_values = {
      'greetings': greetings,
      'url': url,
      'url_linktext': url_linktext,
    }

    template = jinja_environment.get_template('index.html')
    self.response.out.write(template.render(template_values))
  
class Guestbook(webapp2.RequestHandler):
  def post(self):
    # We set the same parent key on the 'Greeting' to ensure each greeting is in
    # the same entity group. Queries across the single entity group will be
    # consistent. However, the write rate to a single entity group should
    # be limited to ~1/second.
    guestbook_name = self.request.get('guestbook_name')
    greeting = Greeting(parent=guestbook_key(guestbook_name))
    
    if users.get_current_user():
      greeting.author = users.get_current_user()

    greeting.content = self.request.get('content')
    greeting.put()
    self.redirect('/?' + urllib.urlencode({'guestbook_name': guestbook_name}))
    
    
##Index(Greeting, author)

app = webapp2.WSGIApplication([('/', MainPage), ('/sign', Guestbook)], debug=True)


'''
Google App Engine supports any framework written in pure Python 
that speaks CGI (and any WSGI-compliant framework using a CGI adaptor),
including Django, CherryPy, Pylons, web.py, and web2py. You can bundle a
framework of your choosing with your application code by copying its code
into your application directory.


The Datastore uses optimistic concurrency to manage transactions. When two or more
application instances try to change the same entity group at the same time (either by
updating existing entities or by creating new ones), the first application to commit
its changes will succeed and all others will fail on commit. These other applications
can then try their transactions again to apply them to the updated data. Note that
because the Datastore works this way, using entity groups limits the number of
concurrent writes you can do to any entity in a given group.


'''
