# Standard library
import os
import json
import re
import datetime
    
from flask import Blueprint, render_template, session, redirect, url_for, \
     request, flash, g, jsonify, abort, send_file
from flaskext.openid import COMMON_PROVIDERS

import numpy as np
import pyfits as pf
import pymongo
from bson.objectid import ObjectId
from werkzeug import Response

from ptf.db.mongodb import update_light_curve_document_tags

from ptf_web import oid, app
from ptf_web.utils import requires_login, request_wants_json
from ptf_web.database import db_session, User, light_curve_collection, field_collection, table_state_collection

mod = Blueprint('candidates', __name__)

# Jsonify to deal with mongodb objectid
class MongoJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        elif isinstance(obj, ObjectId):
            return unicode(obj)
        return json.JSONEncoder.default(self, obj)

def jsonify(*args, **kwargs):
    """ jsonify with support for MongoDB ObjectId
    """
    return Response(json.dumps(dict(*args, **kwargs), cls=MongoJsonEncoder), mimetype='application/json')

def str_encode_field_ccd_source(field_id, ccd_id, source_id):
    return "f{}c{}s{}".format(field_id, ccd_id, source_id)

def str_decode_field_ccd_source(string):
    pattr = re.compile("f([0-9]+)c([0-9]+)s([0-9]+)")
    return map(int, pattr.search(string).groups())

@mod.route('/json/candidate_list', methods=["GET"])
@requires_login
def candidate_list():
    """ Load candidate light curves from MongoDB """
    
    search = {}
    
    # Default is to sort by CCD, Source ID
    if request.args.has_key("field_id"):
        field_ids = [int(x) for x in request.args.getlist("field_id")]
        search["field_id"] = {"$in" : field_ids}
    
    #search["indices"] = {"delta_chi_squared" : {"$gt" : 500}}
    #search["field_id"] = {"$in" : [4465]} # HACK
    
    # Default is to return all, e.g. num=0
    num = request.args.get("num", 0)
    
    # Default is to sort by CCD, Source ID
    if request.args.has_key("sort"):
        sort = [(x,pymongo.ASCENDING) for x in request.args.getlist("sort")]
    else:
        sort = [("field_id",pymongo.ASCENDING), ("ccd_id",pymongo.ASCENDING), ("source_id",pymongo.ASCENDING)]
    
    # Default is to get Field ID, CCD ID, Source ID
    mongo_fields = request.args.get("fields", ["field_id", "ccd_id", "source_id", "indices", "ra", "dec", "microlensing_fit", "tags"])
    
    raw_candidates = light_curve_collection.find(search, fields=mongo_fields, sort=sort, limit=int(num))
    
    candidates = []
    for c in list(raw_candidates):
        candidates.append(dict(c))

    return jsonify(aaData=list(candidates))
    
@mod.route('/json/candidate_data', methods=["GET"])
@requires_login
def candidate_data():
    """ Load candidate light curves from MongoDB """
    
    search = {}
    search["field_id"] = int(request.args["field_id"])
    search["ccd_id"] = int(request.args["ccd_id"])
    search["source_id"] = int(request.args["source_id"])
    
    candidate = light_curve_collection.find_one(search)
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
    
    if request.args.has_key("set_tags"):
        if request.args["set_tags"] == "true":
            try:
                tags = [str(x) for x in request.args.getlist("tags")]
            except KeyError:
                tags = []
            
            if request.args.has_key("new_tag"):
                tags.append(str(request.args["new_tag"]))
            
            lc_document = light_curve_collection.find_one({"field_id" : field_id, "ccd_id" : ccd_id, "source_id" : source_id})
            
            tags = [str(tag).strip() for tag in tags if len(tag.strip()) > 0]
            
            if lc_document != None:
                update_light_curve_document_tags(lc_document, tags, light_curve_collection)
    
    lc_document = light_curve_collection.find_one({"field_id" : field_id, "ccd_id" : ccd_id, "source_id" : source_id})
    return render_template('candidates/plot.html', light_curve=lc_document, all_tags=sorted(light_curve_collection.distinct("tags")))

@mod.route('/mongo/save_table_state', methods=["POST"])
@requires_login
def save_table_state():
    """ Save the current state of the table for next / previous buttons """
    
    user_id = g.user.id
    
    json_data = request.json
    
    table_state_list = []
    for ii in range(len(json_data["field_id"])):
        field_id = json_data["field_id"][ii]
        ccd_id = json_data["ccd_id"][ii]
        source_id = json_data["source_id"][ii]
        
        table_state_list.append(str_encode_field_ccd_source(field_id, ccd_id, source_id))
    
    # See if there is currently a state stored for this user
    table_state = table_state_collection.find_one({"user_id" : user_id})
    
    if table_state == None:
        table_state = dict()
        table_state["user_id"] = user_id
        table_state["state"] = table_state_list
        table_state_collection.insert(table_state, safe=True)
    else:
        table_state_collection.update({"user_id" : user_id}, {"$set" : {"state" : table_state_list}})
    
    return ""

@mod.route('/mongo/previous_next_light_curve', methods=["GET"])
@requires_login
def previous_next_light_curve():
    """ Load the current state of the table for next / previous buttons """
    
    if not request.args.has_key("source_id") or not request.args.has_key("field_id") or not request.args.has_key("ccd_id"):
        abort(404)
    
    field_id = int(request.args["field_id"])
    ccd_id = int(request.args["ccd_id"])
    source_id = int(request.args["source_id"])
    
    user_id = g.user.id
    table_state = table_state_collection.find_one({"user_id" : user_id})
    
    if table_state == None:
        return jsonify({})
    else:
        idx = table_state["state"].index(str_encode_field_ccd_source(field_id, ccd_id, source_id))
        if idx > len(table_state["state"])-1:
            next_idx = -1
        else:
            next_idx = idx+1
        
        return jsonify(previous=str_decode_field_ccd_source(table_state["state"][idx-1]), 
                       next=str_decode_field_ccd_source(table_state["state"][next_idx]))
    