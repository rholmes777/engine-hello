# Python imports
import cgi
import datetime
import urllib
import webapp2
import logging

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
    self.response.out.write('<html><body>')
    
    # guestbook_name is a parameter in the URL; the parent of a Greeting is
    # a guestbook: 'Guestbook: name=Foo barbaz'
    # The parent is used as a placeholder for transaction and consistency purposes. 
    # Objects that share a common ancestor belong to the same entity group. 
    guestbook_name = self.request.get('guestbook_name')
    logging.info("********* Guestbook name: %s\n" % guestbook_name)
    
    # Ancestor Queries, as shown here, are strongly consistent with the High
    # Replication datastore. Queries that span entity groups are eventually
    # consistent. If we omitted the ancestor from this query there would be a
    # slight chance that Greeting that had just been written would not show up
    # in a query.
    #
    # The only supported queries are those whose performance scales with the size
    # of the result set (as opposed to the data set). (Better scalability)
    greetings = db.GqlQuery("SELECT * "
                            "FROM Greeting "
                            "WHERE ANCESTOR IS :1 "
                            "ORDER BY date DESC LIMIT 10",
                            guestbook_key(guestbook_name))
    
    for greeting in greetings:
      # Author is email address; in test env, it's often 'test@example.com'
      if greeting.author:
        self.response.out.write('<b>%s</b> wrote: ' % greeting.author.nickname())
      else: 
        self.response.out.write('An anonymous person wrote:')
      self.response.out.write('<blockquote>%s</blockquote>' % cgi.escape(greeting.content))
    
    # Sample query for something which uses the Author filter    
    another_greeting = db.GqlQuery("SELECT * "
                            "FROM Greeting "
                            "WHERE ANCESTOR IS :1 "
                            "AND Author = :2 "
                            "ORDER BY date DESC LIMIT 10 ",
                            'joe',
                            'test@example.com')
    logging.debug("Another greeting using vars(): %s" % vars(another_greeting))                            

    self.response.out.write("""
          <form action="/sign?%s" method="post">
            <div><textarea name="content" rows="3" cols="60"></textarea></div>
            <div><input type="submit" value="Sign Guestbook"></div>
          </form>
          <hr>
          <form>Guestbook name: <input value="%s" name="guestbook_name">
          <input type="submit" value="switch"></form>
        </body>
      </html>""" % (urllib.urlencode({'guestbook_name': guestbook_name}),
                          cgi.escape(guestbook_name)))
    

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
