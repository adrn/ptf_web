""" This server is meant to be run within a virtual environment:
        
        % . venv/bin/activate
        % python serve.py
        
    Packages installed into this virtual environment:
        pip install numpy scipy sqlalchemy flask flask-openid pyfits PIL
        
    TODO:
        - Create a function in candidates that accepts a Source ID and an MJD and returns
            an image (for the plot.html page)
        - Create new table in website.db for storing flags specified on the html form on plot.html
        - Create the html form on plot.html, e.g. variable star, transient, galaxy, etc.
    
"""

from argparse import ArgumentParser
from ptf_web import app

if __name__ == "__main__":
    parser = ArgumentParser("Run APW's PTF website")
    parser.add_argument("-d", "--debug", dest="debug", action="store_true", default=False,
                      help="Print debug messages, be chatty!")
    
    args = parser.parse_args()
    
    app.run(debug=args.debug, host="0.0.0.0", port=5000)
    
