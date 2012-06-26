from flask import Flask, session, g, render_template
from flaskext.openid import OpenID

#from ptf_web import utils

# Define application and configuration script
app = Flask(__name__)
app.config.from_object("wwwconfig")

# Initialize OpenID utilities
from ptf_web.openid_auth import DatabaseOpenIDStore
oid = OpenID(app, store_factory=DatabaseOpenIDStore)

# Custom 404 page -- should be at: templates/404.html
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

# APW: Where does User come from???
@app.before_request
def load_current_user():
    g.user = User.query.filter_by(openid=session['openid']).first() \
        if 'openid' in session else None

@app.teardown_request
def remove_db_session(exception):
    db_session.remove()

from ptf_web.views import general
app.register_blueprint(general.mod)
from ptf_web.views import candidates
app.register_blueprint(candidates.mod)

# This needs to be down here..
from ptf_web.database import User, db_session

#app.jinja_env.filters['datetimeformat'] = utils.format_datetime
#app.jinja_env.filters['timedeltaformat'] = utils.format_timedelta
app.jinja_env.filters['displayopenid'] = utils.display_openid