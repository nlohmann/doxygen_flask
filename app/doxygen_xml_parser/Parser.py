# coding=utf-8

from typing import List, Dict, Union, Any
from lxml import etree as ET
from app.doxygen_xml_parser.Wrappers import MemberDefWrapper, CompoundDefWrapper
import glob
import logging
import configparser
import json
from config import DOXFILE_PATH
import os.path


class Parser(object):
    def __init__(self):
        self.lookup = {}  # type: Dict[str, Union[MemberDefWrapper, CompoundDefWrapper]]
        self.compounddefs = []  # type: List[CompoundDefWrapper]
        self.memberdefs = []  # type: List[MemberDefWrapper]
        self.doxyfile = self.__parse_doxyfile()  # type: Dict[str, Any]
        self.class_members = []  # type: List[Dict]
        self.files = {}  # type: Dict[str,str]

    def late_init(self):
        xml_path = os.path.join(os.path.dirname(DOXFILE_PATH), self.doxyfile['xml_output'], '*.xml')
        xml_files = glob.glob(xml_path)
        for xml_file in xml_files:
            xml_doc = ET.parse(xml_file)
            current_file_compounddefs = [CompoundDefWrapper(element, self.doxyfile)
                                         for element in xml_doc.findall('./compounddef')]
            self.compounddefs += current_file_compounddefs
            for current_file_compounddef in current_file_compounddefs:
                self.memberdefs += [MemberDefWrapper(element, current_file_compounddef, self.doxyfile)
                                    for element in current_file_compounddef.element.findall('.//memberdef')]

        # add entries to lookup table
        for compounddef in self.compounddefs:
            self.lookup[compounddef.element.attrib['id']] = compounddef
        for memberdef in self.memberdefs:
            self.lookup[memberdef.element.attrib['id']] = memberdef

        logging.debug('parsed {files} files, {compounds} compounds, {members} members'.format(
            files=len(xml_files), compounds=len(self.compounddefs), members=len(self.memberdefs)))

        # created class member list
        self.class_members = sorted([{
            'initial': memberdef.name[0].lower(),
            'name': memberdef.name,
            'id': memberdef.element.attrib['id']
        } for memberdef in self.memberdefs], key=lambda x: x['name'].lower())

        # create file index
        self.files = {
            file.element.find('./location').attrib['file']: file.id for file in [x for x in self.compounddefs if x.element.attrib['kind'] == 'file']
        }

    @staticmethod
    def __parse_doxyfile():
        # read Doxyfile to string
        doxyfile_content = open(DOXFILE_PATH).read()

        # add section to allow parsing with configparser
        doxyfile_content = '[DEFAULT]\n' + doxyfile_content

        # parse with configparser
        config = configparser.ConfigParser()
        config.read_string(doxyfile_content)

        # create dictionary with "nice" values
        result = dict()
        for key in config['DEFAULT']:
            try:
                # first step: use JSON parser to cope with strings (remove quotes) and numbers
                result[key] = json.loads(config['DEFAULT'][key])
            except json.JSONDecodeError:
                try:
                    # second step: convert YES/NO to True/False
                    result[key] = {'YES': True, 'NO': False}[config['DEFAULT'][key]]
                except KeyError:
                    # third step: if everything else fails, store as strings
                    result[key] = config['DEFAULT'][key]

        return result
