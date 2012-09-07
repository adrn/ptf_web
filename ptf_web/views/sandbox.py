import os
import glob
import re
    
from flask import Blueprint, render_template, session, redirect, url_for, \
     request, flash, g, jsonify, abort, send_file
from flaskext.openid import COMMON_PROVIDERS

import numpy as np

from ptf_web import oid, app
from ptf_web.utils import requires_login, request_wants_json
#from ptf_web.database import db_session, User, lc_db_session, LightCurve

mod = Blueprint('sandbox', __name__)

@mod.route('/sandbox', methods=["GET"])
def index():
    try:
        csv_data_files = glob.glob(os.path.join(app.config['CSV_PATH'], "*.csv"))
    except OSError:
        csv_data_files = []
        
    csv_data_files = [os.path.basename(x) for x in csv_data_files]
    fields = [int(os.path.splitext(file)[0][5:]) for file in csv_data_files]
    return render_template('sandbox/index.html', fields=fields)

@mod.route('/sandbox/grid_plot', methods=["GET"])
def grid_plot():
    if not request.args.has_key("field_id"):
        abort(404)
        
    return render_template('sandbox/grid_plot.html', field_id=request.args["field_id"])

@mod.route('/sandbox/csv', methods=["GET"])
def csv():
    if not request.args.has_key("field_id"):
        abort(404)
    
    try:
        csv_data_files = os.listdir(app.config['CSV_PATH'])
    except OSError:
        csv_data_files = []
    
    file = "field{:06d}.csv".format(int(request.args["field_id"]))
    
    print file, csv_data_files
    
    if file in csv_data_files:
        f = open(os.path.join(app.config['CSV_PATH'], file))
    else:
        abort(404)
    
    return send_file(f, mimetype="test/csv")

@mod.route('/sandbox/sky_coverage', methods=["GET"])
def sky_coverage():
    return render_template('sandbox/sky_coverage.html')

"""
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
"""