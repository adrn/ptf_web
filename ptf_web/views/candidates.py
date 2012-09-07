# Standard library
import os
    
from flask import Blueprint, render_template, session, redirect, url_for, \
     request, flash, g, jsonify, abort, send_file
from flaskext.openid import COMMON_PROVIDERS

import numpy as np
import pyfits as pf

from ptf.db.mongodb import update_candidate_status

from ptf_web import oid, app
from ptf_web.utils import requires_login, request_wants_json
from ptf_web.database import db_session, User, light_curve_collection, candidate_status_collection

mod = Blueprint('candidates', __name__)

@mod.route('/json/candidate_list', methods=["GET"])
@requires_login
def candidate_list():
    """ Load candidate light curves from MongoDB """
    
    search = {}
    
    # Default is to sort by CCD, Source ID
    if request.args.has_key("field_id"):
        field_ids = [int(x) for x in request.args.getlist("field_id")]
        search["field_id"] = {"$in" : field_ids}
    
    # Default is to return all, e.g. num=0
    num = request.args.get("num", 0)
    
    # Default is to sort by CCD, Source ID
    if request.args.has_key("sort"):
        sort = [(x,1) for x in request.args.getlist("sort")]
    else:
        sort = [("ccd_id",1), ("source_id",1)]
    
    # Default is to get Field ID, CCD ID, Source ID
    mongo_fields = request.args.get("fields", ["field_id", "ccd_id", "source_id", "delta_chi_squared", "ra", "dec"])
    
    raw_candidates = light_curve_collection.find(search, fields=mongo_fields).limit(int(num)).sort(sort)
    
    candidates = []
    for c in list(raw_candidates):
        #candidates.append([c["field_id"],c["ccd_id"],c["source_id"]])
        
        if not c.has_key("delta_chi_squared"):
            c["delta_chi_squared"] = ""
            
        c_dict = dict([(key,val) for key,val in c.items() if key != "_id"])
        
        raw_status = candidate_status_collection.find_one({"light_curve_id" : c["_id"]})
        if raw_status == None:
            c_dict["status"] = "<font color='#aaaaaa'>none</font>"
        else:
            if raw_status["status"] == "Candidate":
                c_dict["status"] = "<font color='rgba(215, 25, 28, 0.95)'>{}</font>".format(raw_status["status"])
            else:
                c_dict["status"] = raw_status["status"]
                
        candidates.append(c_dict)
    
    return jsonify(aaData=list(candidates))
    
@mod.route('/json/candidate_data', methods=["GET"])
@requires_login
def candidate_data():
    """ Load candidate light curves from MongoDB """
    
    search = {}
    search["field_id"] = int(request.args["field_id"])
    search["ccd_id"] = int(request.args["ccd_id"])
    search["source_id"] = int(request.args["source_id"])
    
    raw_candidate = light_curve_collection.find_one(search)
    candidate = dict([(key,val) for key,val in raw_candidate.items() if key != "_id"])
    
    raw_status = candidate_status_collection.find_one({"light_curve_id" : raw_candidate["_id"]})
    if raw_status == None:
        candidate["status"] = ""
    else:
        candidate["status"] = raw_status["status"]
        
    return jsonify(light_curve=candidate)

@mod.route('/candidates', methods=["GET"])
@requires_login
def index():
    if request.args.has_key("onlyUnknown"):
        only_unknown_checked = "true"
    else:
        only_unknown_checked = "false"
        
    return render_template('candidates/index.html', only_unknown_checked=only_unknown_checked)

@mod.route('/candidates/plot', methods=["GET"])
@requires_login
def plot():
    if not request.args.has_key("source_id") or not request.args.has_key("field_id") or not request.args.has_key("ccd_id"):
        abort(404)
    
    source_id = int(request.args["source_id"])
    field_id = int(request.args["field_id"])
    ccd_id = int(request.args["ccd_id"])
    
    if request.args.has_key("update_status"):
        if request.args["update_status"] == "true":
            try:
                status = request.args["status"].strip()
            except KeyError:
                status = ""
            
            update_candidate_status(field_id, ccd_id, source_id, status, light_curve_collection, candidate_status_collection)
    
    return render_template('candidates/plot.html', field_id=field_id, ccd_id=ccd_id, source_id=source_id)

"""
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