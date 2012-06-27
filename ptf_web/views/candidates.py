import os
import urllib2, base64
import cStringIO as StringIO
import gzip
    
from flask import Blueprint, render_template, session, redirect, url_for, \
     request, flash, g, jsonify, abort, send_file
from flaskext.openid import COMMON_PROVIDERS

import numpy as np
import sqlalchemy
import pyfits as pf
import Image

from ptf_web import oid, app
from ptf_web.utils import requires_login, request_wants_json
from ptf_web.database import db_session, User, lc_db_session, LightCurve

mod = Blueprint('candidates', __name__)

def get_candidates(sort_key, reverse):
    candidates = []
    for light_curve in lc_db_session.query(LightCurve).all():
         candidates.append(light_curve.to_json())
    
    try:
        candidates = sorted(candidates, key=lambda x: x[sort_key], reverse=reverse)
    except KeyError:
        flash(u"Invalid table sort key.")
    
    return candidates

def get_key(key, sort_key, reverse):
    vals = []
    
    if key == sort_key:
        for light_curve in lc_db_session.query(LightCurve).all():
             vals.append({key : getattr(light_curve, key)})
    else:
        for light_curve in lc_db_session.query(LightCurve).all():
             vals.append({key : getattr(light_curve, key), sort_key : getattr(light_curve, sort_key)})
    
    vals = [x[key] for x in sorted(vals, key=lambda x: x[sort_key], reverse=reverse)]
    
    return vals

@mod.route('/candidates', methods=["GET"])
@requires_login
def index():
    
    try:
        sort_key = request.args["sort_key"]
    except KeyError:
        sort_key = "matchedSourceID"
    
    try:
        rev = request.args["reverse"]
        reverse = True
    except KeyError:
        reverse = False
    
    candidates = get_candidates(sort_key, reverse)
    
    session["sort_key"] = sort_key
    session["reverse"] = reverse
    session.modified = True
    
    return render_template('candidates/index.html', candidates=candidates)

@mod.route('/candidates/plot', methods=["GET"])
@requires_login
def plot():
    if not request.args.has_key("matchedSourceID"):
        abort(404)
    
    try:
        source_id = int(request.args["matchedSourceID"])
    except:
        light_curve = None
        flash(u"Invalid Source ID")
    
    try:
        light_curve = lc_db_session.query(LightCurve).filter(LightCurve.matchedSourceID == int(request.args["matchedSourceID"])).one()
    except sqlalchemy.orm.exc.NoResultFound:
        light_curve = None
        flash(u"Source ID not in database.")
    
    if session.has_key("sort_key"):
        sort_key = session["sort_key"]
    else:
        sort_key = "matchedSourceID"
    
    if session.has_key("reverse"):
        reverse = session["reverse"]
    else:
        reverse = False
        
    source_ids = get_key("matchedSourceID", sort_key, reverse)
    this_index = source_ids.index(source_id)
    
    if this_index == 0:
        previous_id = None
    else:
        previous_id = source_ids[this_index-1]
        
    if this_index == len(source_ids)-1:
        next_id = None
    else:
        next_id = source_ids[this_index+1]
    
    return render_template('candidates/plot.html', light_curve=light_curve, previous_id=previous_id, next_id=next_id)

@mod.route('/candidates/data', methods=["GET"])
@requires_login
def data():
    if not request.args.has_key("matchedSourceID"):
        abort(404)
        
    try:
        source_id = int(request.args["matchedSourceID"])
    except:
        light_curve = None
        flash(u"Invalid Source ID")
    
    try:
        light_curve = lc_db_session.query(LightCurve).filter(LightCurve.matchedSourceID == int(request.args["matchedSourceID"])).one()
    except sqlalchemy.orm.exc.NoResultFound:
        light_curve = None
        flash(u"Source ID not in database.")
    
    lc_dict = light_curve.to_json()
    lc_data = light_curve.data
    lc_dict["mjd"] = list(lc_data["mjd"].astype(float))
    lc_dict["mag"] = list(lc_data["mag"].astype(float))
    lc_dict["error"] = list(lc_data["error"].astype(float))
    
    return jsonify(light_curve=lc_dict)

@mod.route('/candidates/ptfimage', methods=["GET"])
@requires_login
def ptfimage():
    if not request.args.has_key("matchedSourceID"):
        abort(404)
    
    try:
        light_curve = lc_db_session.query(LightCurve).filter(LightCurve.matchedSourceID == int(request.args["matchedSourceID"])).one()
    except sqlalchemy.orm.exc.NoResultFound:
        light_curve = None
        flash(u"Source ID not in database.")
        abort(404)
    
    with open(os.path.join(app.config['BASEDIR'],"ptf_credentials")) as f:
        userline, passwordline = f.readlines()
    
    user = userline.split()[1]
    password = passwordline.split()[1]
    
    try:
        mjd = float(request.args["mjd"])
    except:
        mjd = light_curve.data["mjd"][0]
    
    ra = light_curve.ra
    dec = light_curve.dec
    
    # http://kanaloa.ipac.caltech.edu/ibe/search/ptf/dev/process?POS=12.5432151118,40.1539468896&size=0.005&columns=pfilename&where=obsmjd=55398.33127
    url = "http://kanaloa.ipac.caltech.edu/ibe/search/ptf/dev/process?POS={0},{1}&SIZE={2}&columns=pfilename&where=obsmjd={3:.5f}".format(ra, dec, 10./3600., mjd)
    
    http_request = urllib2.Request(url)
    base64string = base64.encodestring("%s:%s" % (user, password)).replace('\n', '')
    http_request.add_header("Authorization", "Basic %s" % base64string)
    file = StringIO.StringIO(urllib2.urlopen(http_request).read())
    filename = np.genfromtxt(file, skiprows=4, usecols=[3], dtype=str)
    
    fits_image_url = os.path.join(app.config['IPAC_DATA_URL'], str(filename))
    
    http_request = urllib2.Request(fits_image_url + "?center={0},{1}&size=50px".format(ra,dec))
    base64string = base64.encodestring('%s:%s' % (user, password)).replace('\n', '')
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