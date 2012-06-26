""" This server is meant to be run within a virtual environment:
        
        % . venv/bin/activate
        % python serve.py
        
    Packages installed into this virtual environment:
        pip install numpy scipy sqlalchemy flask flask-openid
    
"""

from optparse import OptionParser
from ptf_web import app

if __name__ == "__main__":
    parser = OptionParser("Run APW's PTF website")
    parser.add_option("-d", "--debug", dest="debug", action="store_true", default=False,
                      help="Print debug messages, be chatty!")
    
    (options, args) = parser.parse_args()
    
    app.run(debug=options.debug, host="0.0.0.0")