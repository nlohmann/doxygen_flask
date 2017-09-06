# coding=utf-8

from flask import url_for
from lxml import etree as ET


def get_bool(s):
    try:
        return {
            'yes': True,
            'no': False
        }[s]
    except KeyError:
        return None


class CompoundDefWrapper(object):
    def __init__(self, element, doxyfile):
        self.element = element  # type: ET.Element
        self.doxyfile = doxyfile

        self.xml = ET.tostring(self.element, pretty_print=True).decode('UTF-8')
        self.name = self.element.find('./compoundname').text  # type: str
        self.id = self.element.attrib['id']  # type: str


class MemberDefWrapper(object):
    def __init__(self, element, parent, doxyfile):
        self.element = element  # type: ET.Element
        self.parent = parent  # type: CompoundDefWrapper
        self.doxyfile = doxyfile

        self.xml = ET.tostring(self.element, pretty_print=True).decode('UTF-8')
        self.name = self.element.find('./name').text  # type: str
        self.id = self.element.attrib['id']  # type: str

        self.sections = self.__get_sections(el=self.element.find('./detaileddescription'))
        brief_section = self.__get_sections(el=self.element.find('./briefdescription'))
        if 'brief' in brief_section:
            self.sections['brief'] = brief_section['brief']

    @property
    def kind_str(self):
        static = get_bool(self.element.attrib.get('static'))

        if self.type_str is None:
            if self.name[0] == '~':
                return '{prot} destructor'.format(
                    prot=self.element.attrib.get('prot')
                )
            else:
                return '{prot} constructor'.format(
                    prot=self.element.attrib.get('prot')
                )
        else:
            return '{prot} {stat} {kind}'.format(
                prot=self.element.attrib.get('prot'),
                stat='static' if static else 'member',
                kind=self.element.attrib.get('kind')
            )

    @property
    def noexcept_str(self):
        """return the noexcept part of the argstring"""
        argsstring = self.child('argsstring').text
        try:
            splitted = argsstring.split('noexcept')
            return 'noexcept' + splitted[1]
        except (AttributeError, IndexError):
            return ''

    @property
    def function_signature_str(self):
        """return the function signature as HTML"""
        static_str = 'static ' if self.element.attrib.get('static') == 'yes' else ''
        return_type = self.type_str
        params_strings = []

        for p in self.params:
            current = '{type_str} {declname}'.format(type_str=p['type_str'],
                                                     declname=p['declname'])
            if p.get('defval'):
                current += ' = ' + p['defval']

            params_strings.append(current)

        params_str = ', '.join(params_strings)
        const_str = ' const' if self.element.attrib.get('const') == 'yes' else ''
        noexcept_str = self.noexcept_str
        if noexcept_str != '':
            noexcept_str = ' ' + noexcept_str

        return '{static_str}{return_type} <strong>{name}</strong>({params_str}){const_str}{noexcept_str};'.format(
            static_str=static_str,
            return_type=return_type,
            name=self.name,
            params_str=params_str,
            const_str=const_str,
            noexcept_str=noexcept_str
        )

    def child(self, name):
        return self.element.find('./' + name)  # type: ET.Element

    @staticmethod
    def __build_type_str(type_element):
        ref_element = type_element.find('./ref')  # type: ET.Element

        if ref_element is None:
            return type_element.text
        else:
            return '{before_ref}<a href="{uri}">{text}</a>{after_ref}'.format(
                before_ref=type_element.text if type_element.text else '',
                uri=url_for('route_detail', id=ref_element.attrib['refid']),
                text=ref_element.text,
                after_ref=ref_element.tail if ref_element.tail else ''
            )

    @property
    def type_str(self):
        type_element = self.element.find('./type')
        return self.__build_type_str(type_element)

    @property
    def params(self):
        result = []
        for param in self.element.findall('./param'):
            type_str = self.__build_type_str(param.find('./type'))
            declname = param.find('./declname')
            defval = param.find('./defval')
            result.append({
                'type_str': type_str,
                'declname': declname.text if declname is not None else None,
                'defval': defval.text if defval is not None else None
            })

        return result

    @property
    def detaileddescription(self):
        el = self.element.find('./detaileddescription')

        res = ''

        for event, elem in ET.iterwalk(el, events=('start', 'end')):
            if event == 'start':
                attrs = ' '.join(['{key}="{val}"'.format(key=key, val=val) for (key, val) in elem.attrib.iteritems()])
                if attrs != '':
                    attrs = ' ' + attrs

                print('<{tag}{attrs}>'.format(tag=elem.tag, attrs=attrs))

                if elem.tag == 'computeroutput':
                    res += '<code>'

                elif elem.tag == 'simplesect':
                    if elem.attrib.get('kind') == 'return':
                        res += '<h5>Return value</h5>'
                    elif elem.attrib.get('kind') == 'since':
                        res += '<h5>Since</h5>'
                    elif elem.attrib.get('kind') == 'note':
                        res += '<h5>Note</h5>'
                    elif elem.attrib.get('kind') == 'see':
                        res += '<h5>See also</h5>'
                    elif elem.attrib.get('kind') == 'par':
                        res += '<h5>'
                        continue

                    res += '<p>'

                elif elem.tag == 'parameterlist':
                    if elem.attrib.get('kind') == 'param':
                        res += '<h5>Parameters</h5><p>'
                    elif elem.attrib.get('kind') == 'exception':
                        res += '<h5>Exceptions</h5><p>'

                elif elem.tag == 'verbatim':
                    res += '<pre>'

                elif elem.tag == 'programlisting':
                    res += '<pre>'

                elif elem.tag == 'sp':
                    res += ' '

                if elem.text is not None:
                    res += elem.text

            elif event == 'end':
                print('</{tag}>'.format(tag=elem.tag))

                if elem.tag == 'computeroutput':
                    res += '</code>'
                elif elem.tag == 'title':
                    res += '</h5><p>'
                elif elem.tag == 'simplesect':
                    res += '</p>'

                elif elem.tag == 'parameterlist':
                    res += '</p>'

                elif elem.tag == 'verbatim':
                    res += '</pre>'

                elif elem.tag == 'programlisting':
                    res += '</pre>'

                if elem.tail is not None:
                    res += elem.tail

        return res

    def __get_sections(self, el):
        result = {}

        text_buffer = ''
        current_section = None

        for event, elem in ET.iterwalk(el, events=('start', 'end')):
            if event == 'start':
                # take care of sections
                if elem.tag in ['simplesect', 'parameterlist']:
                    # if we have not seen a section before, this was the detailed section
                    if current_section is None:
                        result['detailed'] = text_buffer

                    # remember current section and reset text buffer
                    current_section = elem.attrib['kind']
                    text_buffer = ''

                    # definition list
                    if elem.tag == 'parameterlist':
                        text_buffer += '<dl class="row">'

                # formatting
                elif elem.tag == 'computeroutput':
                    text_buffer += '<code>'
                elif elem.tag == 'programlisting':
                    text_buffer += '<p><pre class="bg-light p-3 border rounded"><code>'
                elif elem.tag == 'sp':
                    text_buffer += ' '
                elif elem.tag == 'verbatim':
                    text_buffer += '<p><pre class="bg-dark text-white p-3 border rounded">'
                elif elem.tag == 'emphasis':
                    text_buffer += '<em>'
                # tables
                elif elem.tag == 'table':
                    text_buffer += '<table class="table table-sm table-striped">'
                elif elem.tag == 'row':
                    text_buffer += '<tr>'
                elif elem.tag == 'entry':
                    if elem.attrib.get('thead') == 'yes':
                        text_buffer += '<th class="table-dark">'
                    else:
                        text_buffer += '<td>'
                # lists
                elif elem.tag == 'itemizedlist':
                    text_buffer += '<ul>'
                elif elem.tag == 'listitem':
                    text_buffer += '<li>'
                elif elem.tag == 'parametername':
                    text_buffer += '<dt class="col-sm-3">'
                elif elem.tag == 'parameterdescription':
                    text_buffer += '<dd class="col-sm-9">'
                # links
                elif elem.tag == 'ref':
                    text_buffer += '<a href="{url}">'.format(url=url_for('route_detail', id=elem.attrib.get('refid')))
                elif elem.tag == 'ulink':
                    text_buffer += '<a href="{url}">'.format(url=elem.attrib.get('url'))
                # images
                elif elem.tag == 'image':
                    url = url_for('route_file', filename='{image_path}/{name}'.format(
                        image_path=self.doxyfile['image_path'],
                        name=elem.attrib.get('name')
                    ))

                    text_buffer += '<p><figure class="figure">\n'
                    text_buffer += '<img src="{url}">\n'.format(url=url)
                    text_buffer += '<figcaption class="figure-caption">'

                # add the text
                if elem.text is not None:
                    text_buffer += elem.text

                # additional case for titles - they are the title for user-defined sections
                if elem.tag == 'title' and current_section == 'par':
                    current_section = elem.text
                    text_buffer = ''

            elif event == 'end':
                # close section
                if elem.tag in ['simplesect', 'parameterlist']:
                    # definition list
                    if elem.tag == 'parameterlist':
                        text_buffer += '</dl>'

                    # add text buffer to sections
                    if current_section not in result:
                        result[current_section] = [text_buffer]
                    else:
                        result[current_section].append(text_buffer)

                # formatting
                elif elem.tag == 'computeroutput':
                    text_buffer += '</code>'
                elif elem.tag == 'programlisting':
                    text_buffer += '</code></pre></p>'
                elif elem.tag == 'verbatim':
                    text_buffer += '</pre></p>'
                elif elem.tag == 'emphasis':
                    text_buffer += '</em>'
                # tables
                elif elem.tag == 'table':
                    text_buffer += '</table>'
                elif elem.tag == 'row':
                    text_buffer += '</tr>'
                elif elem.tag == 'entry':
                    text_buffer += '</td>'
                # lists
                elif elem.tag == 'itemizedlist':
                    text_buffer += '</ul>'
                elif elem.tag == 'listitem':
                    text_buffer += '</li>'
                elif elem.tag == 'parametername':
                    text_buffer += '</dt>'
                elif elem.tag == 'parameterdescription':
                    text_buffer += '</dd>'
                # links
                elif elem.tag == 'ref':
                    text_buffer += '</a>'
                elif elem.tag == 'ulink':
                    text_buffer += '</a>'
                # images
                elif elem.tag == 'image':
                    text_buffer += '</figcaption></figure></p>'

                # add whitespace after paragraph for better spacing
                elif elem.tag == 'para':
                    text_buffer += '\n'

                # add tail text
                if elem.tail is not None:
                    text_buffer += elem.tail

        # if we did not find a section so far, this should be the brief description
        if current_section is None:
            result['brief'] = text_buffer

        return result
