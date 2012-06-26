from flask import Blueprint, render_template, session, redirect, url_for, \
     request, flash, g, jsonify, abort
from flaskext.openid import COMMON_PROVIDERS

import numpy as np
import sqlalchemy

from ptf_web import oid
from ptf_web.utils import requires_login, request_wants_json
from ptf_web.database import db_session, User, lc_db_session, LightCurve

mod = Blueprint('candidates', __name__)

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
    
    # TODO: Need to get all candidates here, return to page
    #for ii in range(100):
    #    test_one_candidate = {"matchedSourceID" : np.random.randint(1E6), "field_id" : np.random.randint(1E5), "ccd_id" : np.random.randint(12), "ra" : np.random.random()*360., "dec" : np.random.random()*180.-90, "num_obs" : np.random.randint(200)}
    #    candidates.append(test_one_candidate)
    candidates = []
    for light_curve in lc_db_session.query(LightCurve).all():
         candidates.append(light_curve.to_json())
    
    try:
        candidates = sorted(candidates, key=lambda x: x[sort_key], reverse=reverse)
    except KeyError:
        flash(u"Invalid table sort key.")
    
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
        
    return render_template('candidates/plot.html', light_curve=light_curve)

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