#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

from flask import Flask, request
from flask_cors import CORS

from kw_extraction_via_rake_nltk_and_text_rank import calculate_keywords

DEBUG = True
app = Flask(__name__)
app.config.from_object(__name__)
cors = CORS(app, resources={r"/*": {"origins": "*"}})

def to_unicode(text):
    if type(text) == unicode:
        return text
    return text.decode("utf-8")

@app.route("/keyword-extraction", methods=['POST'])
def keyword_extraction():

    query = to_unicode(request.get_data())
    response = app.response_class(
        response=json.dumps(calculate_keywords(query)),
        status=200,
        mimetype='application/json'
    )
    return response

if __name__ == "__main__":
    app.run(port=5003, host="0.0.0.0", threaded=True)
