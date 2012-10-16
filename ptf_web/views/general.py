import os, re
import cookielib, urllib, urllib2, base64, json

import cStringIO as StringIO
import gzip

import numpy as np
import pyfits as pf
import Image

from flask import Blueprint, render_template, session, redirect, url_for, \
     request, flash, g, jsonify, abort, send_file
from flaskext.openid import COMMON_PROVIDERS

from ptf_web import oid, app,ptf_user,ptf_password
#from ptf_web.search import search as perform_search
from ptf_web.utils import requires_login, request_wants_json
from ptf_web.database import db_session, User, light_curve_collection, field_collection

from ptf.db.mongodb import get_light_curve_from_collection
import apwlib.geometry as g

mod = Blueprint('general', __name__)

@mod.route('/')
def index():
    if request_wants_json():
        return jsonify(releases=[r.to_json() for r in releases])
    return render_template('general/index.html')

@mod.route('/ptfimage')
def ptfimage():
    """ Returns a JPG PTF image """
    if not request.args.has_key("source_id") or not request.args.has_key("field_id") or not request.args.has_key("ccd_id"):
        abort(404)
    
    light_curve = get_light_curve_from_collection(int(request.args["field_id"]), int(request.args["ccd_id"]), int(request.args["source_id"]), light_curve_collection)
    
    try:
        mjd = float(request.args["mjd"])
    except:
        mjd = light_curve.mjd[0]
    
    ra = light_curve.ra
    dec = light_curve.dec
    
    # http://kanaloa.ipac.caltech.edu/ibe/search/ptf/dev/process?POS=12.5432151118,40.1539468896&size=0.005&columns=pfilename&where=obsmjd=55398.33127
    url = "http://kanaloa.ipac.caltech.edu/ibe/search/ptf/dev/process?POS={0},{1}&SIZE={2}&columns=pfilename&where=obsmjd={3:.5f}".format(ra, dec, 10./3600., mjd)
    
    http_request = urllib2.Request(url)
    base64string = base64.encodestring("%s:%s" % (ptf_user, ptf_password)).replace('\n', '')
    http_request.add_header("Authorization", "Basic %s" % base64string)
    file = StringIO.StringIO(urllib2.urlopen(http_request).read())
    filename = np.genfromtxt(file, skiprows=4, usecols=[3], dtype=str)
    
    fits_image_url = os.path.join(app.config['IPAC_DATA_URL'], str(filename))
    
    http_request = urllib2.Request(fits_image_url + "?center={0},{1}&size=50px".format(ra,dec))
    base64string = base64.encodestring('%s:%s' % (ptf_user, ptf_password)).replace('\n', '')
    http_request.add_header("Authorization", "Basic %s" % base64string)
    
    try:
        f = StringIO.StringIO(urllib2.urlopen(http_request).read())
    except urllib2.HTTPError:
        flash("Error downloading image!")
        return 
    
    try:
        gz = gzip.GzipFile(fileobj=f, mode="rb")
        gz.seek(0)
        
        fitsFile = StringIO.StringIO(gz.read())
    except IOError:
        fitsFile = f
    
    fitsFile.seek(0)
    
    hdulist = pf.open(fitsFile, mode="readonly")
    
    image_data = hdulist[0].data
    scaled_image_data = (255*(image_data - image_data.min()) / (image_data.max() - image_data.min())).astype(np.uint8)
    
    image = Image.fromarray(scaled_image_data)
    
    output = StringIO.StringIO()
    image.save(output, format="png")
    #image.save(open("test.png", "w"), format="png")
    
    #contents = output.getvalue()
    #output.close()
    
    output.seek(0)
    
    #print 'Content-Type:image/png\n'
    return send_file(output, mimetype="image/png")

@mod.route('/json/field', methods=["GET"])
def field_data():
    """ Load field information from MongoDB """
    
    search = {}
    search["_id"] = int(request.args["id"])
    field = field_collection.find_one(search)

    return jsonify(field)

"""
@mod.route('/search/')
def search():
    q = request.args.get('q') or ''
    page = request.args.get('page', type=int) or 1
    results = None
    if q:
        results = perform_search(q, page=page)
        if results is None:
            abort(404)
    return render_template('general/search.html', results=results, q=q)
"""

@mod.route('/logout/')
def logout():
    if 'openid' in session:
        flash(u'Logged out.')
        del session['openid']
    return redirect(request.referrer or url_for('general.index'))


@mod.route('/login/', methods=['GET', 'POST'])
@oid.loginhandler
def login():
    """ Does the login via OpenID.  Has to call into `oid.try_login`
        to start the OpenID machinery.
    """
    
    # APW: ENABLE THIS TO ACCEPT ALL OpenID Providers
    #   -> You have to create logos for all of them though!
    #providers = COMMON_PROVIDERS
    providers = {"google" : COMMON_PROVIDERS["google"]}
    
    if g.user is not None:
        return redirect(url_for('general.index'))
    if 'cancel' in request.form:
        flash(u'Cancelled. The OpenID was not changed.')
        return redirect(oid.get_next_url())
    openid = request.values.get('openid')
    if not openid:
        openid = COMMON_PROVIDERS.get(request.args.get('provider'))
    if openid:
        return oid.try_login(openid, ask_for=['email', 'fullname', 'nickname'])
    error = oid.fetch_error()
    if error:
        flash(u'Error: ' + error)
    return render_template('general/login.html', next=oid.get_next_url(), providers=providers)


@mod.route('/first-login/', methods=['GET', 'POST'])
def first_login():
    with open(os.path.join(app.config['BASEDIR'], "allowed_openids")) as f:
        allowed_openids = [x.strip() for x in f.readlines()]
    
    with open(os.path.join(app.config['BASEDIR'], "allowed_emails")) as f:
        allowed_emails = [x.strip() for x in f.readlines()]
    
    if g.user is not None or 'openid' not in session:
        return redirect(url_for('.login'))
    if request.method == 'POST':
        if 'cancel' in request.form:
            del session['openid']
            flash(u'Login was aborted')
            return redirect(url_for('general.login'))
        
        if (session['openid'] not in allowed_openids) and (request.form["email"] not in allowed_emails):
            flash(u"Unauthorized user.")
            del session['openid']
            return redirect(url_for('general.logout'))
        
        db_session.add(User(request.form['name'], session['openid'], request.form["email"]))
        db_session.commit()
        flash(u'Successfully created profile and logged in!')
        return redirect(oid.get_next_url())
    return render_template('general/first_login.html',
                           next=oid.get_next_url(),
                           openid=session['openid'])

@mod.route('/profile/', methods=['GET', 'POST'])
@requires_login
def profile():
    name = g.user.name
    if request.method == 'POST':
        name = request.form['name'].strip()
        if not name:
            flash(u'Error: a name is required')
        else:
            g.user.name = name
            db_session.commit()
            flash(u'User profile updated')
            return redirect(url_for('.index'))
    return render_template('general/profile.html', name=name)

@oid.after_login
def create_or_login(resp):
    with open(os.path.join(app.config['BASEDIR'], "allowed_openids")) as f:
        allowed_openids = [x.strip() for x in f.readlines()]
    
    session['openid'] = resp.identity_url
    
    #if session['openid'] not in allowed_openids:
    #    flash(u"Unauthorized user.")
    #    del session['openid']
    #    return redirect(url_for('general.logout'))
    
    user = g.user or User.query.filter_by(openid=resp.identity_url).first()
    if user is None:
        print "\n\n\n resp email: {} \n\n\n".format(resp.email)
        return redirect(url_for('.first_login', next=oid.get_next_url(),
                                name=resp.fullname or resp.nickname, email=resp.email))
    if user.openid != resp.identity_url:
        user.openid = resp.identity_url
        db_session.commit()
        flash(u'OpenID identity changed')
    else:
        flash(u'Successfully signed in!')
    return redirect(oid.get_next_url())

@mod.route("/search/simbad", methods=["GET", "POST"])
def search_simbad():
    try:
        ra = request.args["ra"]
        dec = request.args["dec"]
    except:
        return "Invalid RA and Dec!"
    
    if float(dec) > 0:
        dec = "+{}".format(dec)
        
    url = "http://simbad.u-strasbg.fr/simbad/sim-coo?output.format=ASCII&Coord=" + ra + dec + "&Radius=1&Radius.unit=arcmin&otypedisp=V"
    try:
        simbadreq = urllib.urlopen(url)
        data = simbadreq.read().split('\n')
        
        if data[0].startswith('!! No astronomical object found'):
            return jsonify({})
        else:
            pattr = re.compile("Coordinates\(ICRS,ep=J2000,eq=2000\): ([0-9]{2}\s[0-9]{2}\s[0-9\.]+)\s+([\-0-9]+ \d\d [0-9\.]+)")
            
            for line in data:
                grps = pattr.search(line)
                if grps != None:
                    ra,dec = grps.groups()
                    break
                    
    except:
        return "Invalid RA and Dec!" # failed to send request
    
    ra = g.RA.fromDegrees(str(ra))
    dec = g.Dec(str(dec))
    
    return jsonify({"ra" : ra.degrees, "dec" : dec.degrees})

@mod.route("/search/sdss", methods=["GET", "POST"])
def search_sdss():
    try:
        ra = request.args["ra"]
        dec = request.args["dec"]
    except:
        return "Invalid RA and Dec!"
    
    username = 'adrian'
    password = 'lateralus0'
    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    login_data = urllib.urlencode({'username' : username, 'password' : password})
    opener.open('http://navtara.caltech.edu/galactic/marshal/login.php', login_data)
    
    url = "http://navtara.caltech.edu/cgi-bin/ptf/galactic/get_sdss.cgi?ra={}&dec={}".format(ra,dec)
    resp = opener.open(url)
    
    return jsonify(json.loads(resp.read()))