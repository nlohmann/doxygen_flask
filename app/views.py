# coding=utf-8

import os.path
from config import DOXFILE_PATH
from app import app, cache
from flask import render_template, abort, send_from_directory
from app.doxygen_xml_parser import parser
from app.doxygen_xml_parser.Wrappers import MemberDefWrapper, CompoundDefWrapper


@app.before_first_request
def init():
    parser.late_init()


@app.route('/')
@cache.cached(timeout=60)
def route_index():
    return render_template('index.html',
                           entries=parser.compounddefs,
                           title='Overview',
                           doxyfile=parser.doxyfile)


@app.route('/detail/<id>.html')
@cache.cached(timeout=60)
def route_detail(id):
    try:
        entry = parser.lookup[id]

        if entry.element.tag == 'memberdef':
            member_entry = entry  # type: MemberDefWrapper
            return render_template('detail_memberdef.html',
                                   entry=member_entry,
                                   files=parser.files,
                                   lookup=parser.lookup,
                                   title=member_entry.parent.name + '::' + member_entry.name,
                                   doxyfile=parser.doxyfile)
        else:
            compound_entry = entry  # type: CompoundDefWrapper
            return render_template('detail_compounddef.html',
                                   entry=compound_entry,
                                   title=compound_entry.name,
                                   lookup=parser.lookup,
                                   doxyfile=parser.doxyfile)

    except KeyError:
        abort(404)


@app.route('/file/<path:filename>')
def route_file(filename):
    dp = os.path.abspath(os.path.dirname(DOXFILE_PATH))
    print(dp, filename)
    return send_from_directory(dp, filename)


@app.route('/functions.html')
def route_functions():
    return render_template('functions.html',
                           class_members=parser.class_members,
                           title='Functions',
                           lookup=parser.lookup,
                           doxyfile=parser.doxyfile)
