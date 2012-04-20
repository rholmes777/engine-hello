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
    # NOTE: Multiple writes can be done within one transaction, however, and 
    # that can be huge: batch puts or entire transaction counts as 1 write;
    # also can have many millions of entities.  FWIW, it's more like 5-10 in
    # practice, and this limitation allows atomicity and consistency.  Can write
    # to MANY entity groups per second, and you can have MANY entities per group.
    # Entity groups may span many (machine) nodes.
    guestbook_name = self.request.get('guestbook_name')
    greeting = Greeting(parent=guestbook_key(guestbook_name))
    
    if users.get_current_user():
      greeting.author = users.get_current_user()

    greeting.content = self.request.get('content')
    greeting.put()
    self.redirect('/?' + urllib.urlencode({'guestbook_name': guestbook_name}))
    
app = webapp2.WSGIApplication([('/', MainPage), ('/sign', Guestbook)], debug=True)

