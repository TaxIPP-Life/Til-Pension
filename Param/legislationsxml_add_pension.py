# -*- coding: utf-8 -*-


# OpenFisca -- A versatile microsimulation software
# By: OpenFisca Team <contact@openfisca.fr>
#
# Copyright (C) 2011, 2012, 2013, 2014 OpenFisca Team
# https://github.com/openfisca
#
# This file is part of OpenFisca.
#
# OpenFisca is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# OpenFisca is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""Handle legislative parameters in XML format (and convert then to JSON)."""


import collections
import logging
import itertools

import datetime
from openfisca_core import conv

from datetime import datetime as dt
#legislation_json_key_by_xml_tag = dict(
#    ASSIETTE = 'base',  # "base" is singular, because a slice has only one base.
#    BAREME = 'scales',
#    CODE = 'parameters',
#    NODE = 'nodes',
#    SEUIL= 'threshold',  # "threshold" is singular, because a slice has only one base.
#    TAUX = 'rate',  # "rate" is singular, because a slice has only one base.
#    TRANCHE = 'slices',
#    VALUE = 'values',
#    )

log = logging.getLogger(__name__)
json_unit_by_xml_json_type = dict(
    age = u'year',
    days = u'day',
    hours = u'hour',
    monetary = u'currency',
    months = u'month',
    )
N_ = lambda message: message
xml_json_formats = (
    'bool',
    'float',
    'integer',
    'percent',
    )


def make_validate_values_xml_json_dates(require_consecutive_dates = False):
    def validate_values_xml_json_dates(values_xml_json, state = None):
        if not values_xml_json:
            return values_xml_json, None
        if state is None:
            state = conv.default_state

        errors = {}
        for index, value_xml_json in enumerate(values_xml_json):
            if value_xml_json['deb'] > value_xml_json['fin']:
                errors[index] = dict(fin = state._(u"Last date must be greater than first date"))

        sorted_values_xml_json = sorted(values_xml_json, key = lambda value_xml_json: value_xml_json['deb'],
            reverse = True)
        next_value_xml_json = sorted_values_xml_json[0]
        for index, value_xml_json in enumerate(itertools.islice(sorted_values_xml_json, 1, None)):
            next_date_str = (datetime.date(*(int(fragment) for fragment in value_xml_json['fin'].split('-'))) + datetime.timedelta(days = 1)).isoformat()
            if require_consecutive_dates and next_date_str < next_value_xml_json['deb']:
                errors.setdefault(index, {})['deb'] = state._(u"Dates of values are not consecutive")
            elif next_date_str > next_value_xml_json['deb']:
                errors.setdefault(index, {})['deb'] = state._(u"Dates of values overlap")
            next_value_xml_json = value_xml_json

        return sorted_values_xml_json, errors or None

    return validate_values_xml_json_dates


def translate_xml_element_to_json_item(xml_element):
    json_element = collections.OrderedDict()
    text = xml_element.text
    if text is not None:
        text = text.strip().strip('#').strip() or None
        if text is not None:
            json_element['text'] = text
    json_element.update(xml_element.attrib)
    for xml_child in xml_element:
        json_child_key, json_child = translate_xml_element_to_json_item(xml_child)
        json_element.setdefault(json_child_key, []).append(json_child)
    tail = xml_element.tail
    if tail is not None:
        tail = tail.strip().strip('#').strip() or None
        if tail is not None:
            json_element['tail'] = tail
    return xml_element.tag, json_element


def transform_node_xml_json_to_json(node_xml_json, root = True):
    comments = []
    node_json = collections.OrderedDict()
    if root:
        node_json['@context'] = u'http://openfisca.fr/contexts/legislation.jsonld'
    node_json['@type'] = 'Node'
    child_json_by_code = {}
    for key, value in node_xml_json.iteritems():
        if key == 'BAREME':
            for child_xml_json in value:
                child_code, child_json = transform_scale_xml_json_to_json(child_xml_json)
                child_json_by_code[child_code] = child_json
        elif key == 'VALBYTRANCHES':
            for child_xml_json in value:
                child_code, child_json = transform_generation_xml_json_to_json(child_xml_json)
                child_json_by_code[child_code] = child_json
        elif key == 'CODE':
            for child_xml_json in value:
                child_code, child_json = transform_parameter_xml_json_to_json(child_xml_json)
                child_json_by_code[child_code] = child_json
        elif key == 'code':
            pass
        elif key == 'NODE':
            for child_xml_json in value:
                child_code, child_json = transform_node_xml_json_to_json(child_xml_json, root = False)
                child_json_by_code[child_code] = child_json
        elif key in ('tail', 'text'):
            comments.append(value)
        else:
            node_json[key] = value
    node_json['children'] = collections.OrderedDict(sorted(child_json_by_code.iteritems()))
    if comments:
        node_json['comment'] = u'\n\n'.join(comments)
    return node_xml_json['code'], node_json


def transform_parameter_xml_json_to_json(parameter_xml_json):
    comments = []
    parameter_json = collections.OrderedDict()
    parameter_json['@type'] = 'Parameter'
    xml_json_value_to_json_transformer = float
    for key, value in parameter_xml_json.iteritems():
        if key in ('code', 'taille'):
            pass
        elif key == 'format':
            parameter_json[key] = dict(
                bool = u'boolean',
                percent = u'rate',
                ).get(value, value)
            if value == 'bool':
                xml_json_value_to_json_transformer = lambda xml_json_value: bool(int(xml_json_value))
            elif value == 'integer':
                xml_json_value_to_json_transformer = int
        elif key in ('tail', 'text'):
            comments.append(value)
        elif key == 'type':
            parameter_json['unit'] = json_unit_by_xml_json_type.get(value, value)
        elif key == 'VALUE':
            parameter_json['values'] = [
                transform_value_xml_json_to_json(item, xml_json_value_to_json_transformer)
                for item in value
                ]
        else:
            parameter_json[key] = value
    if comments:
        parameter_json['comment'] = u'\n\n'.join(comments)
    return parameter_xml_json['code'], parameter_json


def transform_scale_xml_json_to_json(scale_xml_json):
    comments = []
    scale_json = collections.OrderedDict()
    scale_json['@type'] = 'Scale'
    for key, value in scale_xml_json.iteritems():
        if key == 'code':
            pass
        elif key in ('tail', 'text'):
            comments.append(value)
        elif key == 'TRANCHE':
            scale_json['slices'] = [
                transform_slice_xml_json_to_json(item)
                for item in value
                ]
        elif key == 'type':
            scale_json['unit'] = json_unit_by_xml_json_type.get(value, value)
        else:
            scale_json[key] = value
    if comments:
        scale_json['comment'] = u'\n\n'.join(comments)
    return scale_xml_json['code'], scale_json

def transform_generation_xml_json_to_json(scale_xml_json):
    comments = []
    scale_json = collections.OrderedDict()
    scale_json['@type'] = 'Generation'
    for key, value in scale_xml_json.iteritems():
        if key == 'code':
            pass
        elif key in ('tail', 'text'):
            comments.append(value)
        elif key == 'VARCONTROL':
            scale_json['control'] = [
                transform_value_xml_json_to_json(item, str)
                for item in value[0]['CONTROL']
                ]
        elif key == 'TRANCHE':
            scale_json['slices'] = [
                transform_slice2_xml_json_to_json(item)
                for item in value
                ]
        elif key == 'type':
            scale_json['unit'] = json_unit_by_xml_json_type.get(value, value)
        else:
            scale_json[key] = value
    if comments:
        scale_json['comment'] = u'\n\n'.join(comments)
    return scale_xml_json['code'], scale_json


def transform_slice2_xml_json_to_json(slice_xml_json):
    comments = []
    slice_json = collections.OrderedDict()
    for key, value in slice_xml_json.iteritems():
        if key == 'code':
            pass
        elif key == 'SEUIL':
            slice_json['threshold'] = transform_values_holder_xml_json_to_json(value[0], format ='date')
        elif key in ('tail', 'text'):
            comments.append(value)
        elif key == 'VALEUR':
            slice_json['valeur'] = transform_values_holder_xml_json_to_json(value[0])
        else:
            slice_json[key] = value
    if comments:
        slice_json['comment'] = u'\n\n'.join(comments)
    return slice_json


def transform_slice_xml_json_to_json(slice_xml_json):
    comments = []
    slice_json = collections.OrderedDict()
    for key, value in slice_xml_json.iteritems():
        if key == 'ASSIETTE':
            slice_json['base'] = transform_values_holder_xml_json_to_json(value[0])
        elif key == 'code':
            pass
        elif key == 'SEUIL':
            slice_json['threshold'] = transform_values_holder_xml_json_to_json(value[0])
        elif key in ('tail', 'text'):
            comments.append(value)
        elif key == 'TAUX':
            slice_json['rate'] = transform_values_holder_xml_json_to_json(value[0])
        else:
            slice_json[key] = value
    if comments:
        slice_json['comment'] = u'\n\n'.join(comments)
    return slice_json


def transform_value_xml_json_to_json(value_xml_json, xml_json_value_to_json_transformer):
    comments = []
    value_json = collections.OrderedDict()
    for key, value in value_xml_json.iteritems():
        if key in ('code', 'format', 'type'):
            pass
        elif key == 'deb':
            value_json['from'] = value
        elif key == 'fin':
            value_json['to'] = value
        elif key in ('tail', 'text'):
            comments.append(value)
        elif key == 'valeur':
            try:
                if xml_json_value_to_json_transformer == 'date' :
                    value_json['value'] = dt.strptime(value, "%Y-%m-%d").date()
                else :
                    value_json['value'] = xml_json_value_to_json_transformer(value)
            except TypeError:
                log.error(u'Invalid value: {}'.format(value))
                raise
        else:
            value_json[key] = value
    if comments:
        value_json['comment'] = u'\n\n'.join(comments)
    return value_json

def transform_date_xml_json_to_json(value_xml_json):
    comments = []
    value_json = collections.OrderedDict()
    for key, value in value_xml_json.iteritems():
        if key in ('code', 'format', 'type'):
            pass
        elif key == 'deb':
            value_json['from'] = value
        elif key == 'fin':
            value_json['to'] = value
        elif key in ('tail', 'text'):
            comments.append(value)
        elif key == 'valeur':
            try:
                value_json['value'] = dt.strptime(value, "%Y-%m-%d").date()
            except TypeError:
                log.error(u'Invalid value: {}'.format(value))
                raise
        else:
            value_json[key] = value
    if comments:
        value_json['comment'] = u'\n\n'.join(comments)
    return value_json

def transform_values_holder_xml_json_to_json(values_holder_xml_json, format = float):
    return [
            transform_value_xml_json_to_json(item, format)
            for item in values_holder_xml_json['VALUE']
            ]


def validate_node_xml_json(node, state = None):
    if node is None:
        return None, None
    state = conv.add_ancestor_to_state(state, node)
    validated_node, errors = conv.pipe(
        conv.test_isinstance(dict),
        conv.struct(
            dict(
                BAREME = conv.pipe(
                    conv.test_isinstance(list),
                    conv.uniform_sequence(
                        validate_scale_xml_json,
                        drop_none_items = True,
                        ),
                    conv.empty_to_none,
                    ),
                CODE = conv.pipe(
                    conv.test_isinstance(list),
                    conv.uniform_sequence(
                        validate_parameter_xml_json,
                        drop_none_items = True,
                        ),
                    conv.empty_to_none,
                    ),
                code = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_line,
                    conv.not_none,
                    ),
                description = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_line,
                    ),
                NODE = conv.pipe(
                    conv.test_isinstance(list),
                    conv.uniform_sequence(
                        validate_node_xml_json,
                        drop_none_items = True,
                        ),
                    conv.empty_to_none,
                    ),
                tail = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_text,
                    ),
                text = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_text,
                    ),
                ),
            constructor = collections.OrderedDict,
            drop_none_values = 'missing',
            keep_value_order = True,
            ),
        )(node, state = state)
    if errors is None:
        children_groups_key = ('BAREME', 'CODE', 'NODE', 'VALBYTRANCHES')
        if all(
                validated_node.get(key) is None
                for key in children_groups_key
                ):
            error = state._(u"At least one of the following items must be present: {}").format(state._(u', ').join(
                u'"{}"'.format(key)
                for key in children_groups_key
                ))
            errors = dict(
                (key, error)
                for key in children_groups_key
                )
        else:
            errors = {}
        children_code = set()
        for key in children_groups_key:
            for child_index, child in enumerate(validated_node.get(key) or []):
                child_code = child['code']
                if child_code in children_code:
                    errors.setdefault(key, {}).setdefault(child_index, {})['code'] = state._(u"Duplicate value")
                else:
                    children_code.add(child_code)
    conv.remove_ancestor_from_state(state, node)
    return validated_node, errors or None


def validate_parameter_xml_json(parameter, state = None):
    if parameter is None:
        return None, None
    state = conv.add_ancestor_to_state(state, parameter)
    validated_parameter, errors = conv.pipe(
        conv.test_isinstance(dict),
        conv.struct(
            dict(
                code = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_line,
                    conv.not_none,
                    ),
                description = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_line,
                    ),
                format = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.input_to_slug,
                    conv.test_in(xml_json_formats),
                    ),
                tail = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_text,
                    ),
                taille = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.test_in([
                        'moinsde20',
                        'plusde20',
                        ]),
                    ),
                text = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_text,
                    ),
                type = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.input_to_slug,
                    conv.test_in(json_unit_by_xml_json_type),
                    ),
                VALUE = conv.pipe(
                    conv.test_isinstance(list),
                    conv.uniform_sequence(
                        validate_value_xml_json,
                        drop_none_items = True,
                        ),
                    make_validate_values_xml_json_dates(require_consecutive_dates = True),
                    conv.empty_to_none,
                    conv.not_none,
                    ),
                ),
            constructor = collections.OrderedDict,
            drop_none_values = 'missing',
            keep_value_order = True,
            ),
        )(parameter, state = state)
    conv.remove_ancestor_from_state(state, parameter)
    return validated_parameter, errors


def validate_scale_xml_json(scale, state = None):
    if scale is None:
        return None, None
    state = conv.add_ancestor_to_state(state, scale)
    validated_scale, errors = conv.pipe(
        conv.test_isinstance(dict),
        conv.struct(
            dict(
                code = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_line,
                    conv.not_none,
                    ),
                description = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_line,
                    ),
                option = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.input_to_slug,
                    conv.test_in((
                        'contrib',
                        'main-d-oeuvre',
                        'noncontrib',
                        )),
                    ),
                TRANCHE = conv.pipe(
                    conv.test_isinstance(list),
                    conv.uniform_sequence(
                        validate_slice_xml_json,
                        drop_none_items = True,
                        ),
                    validate_slices_xml_json_dates,
                    conv.empty_to_none,
                    conv.not_none,
                    ),
                tail = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_text,
                    ),
                text = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_text,
                    ),
                type = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.input_to_slug,
                    conv.test_in((
                        'monetary',
                        )),
                    ),
                ),
            constructor = collections.OrderedDict,
            drop_none_values = 'missing',
            keep_value_order = True,
            ),
        )(scale, state = state)
    conv.remove_ancestor_from_state(state, scale)
    return validated_scale, errors


def validate_slice_xml_json(slice, state = None):
    if slice is None:
        return None, None
    state = conv.add_ancestor_to_state(state, slice)
    validated_slice, errors = conv.pipe(
        conv.test_isinstance(dict),
        conv.struct(
            dict(
                ASSIETTE = conv.pipe(
                    conv.test_isinstance(list),
                    conv.uniform_sequence(
                        validate_values_holder_xml_json,
                        drop_none_items = True,
                        ),
                    conv.empty_to_none,
                    conv.test(lambda l: len(l) == 1, error = N_(u"List must contain one and only one item")),
                    ),
                code = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_line,
                    ),
                SEUIL = conv.pipe(
                    conv.test_isinstance(list),
                    conv.uniform_sequence(
                        validate_values_holder_xml_json,
                        drop_none_items = True,
                        ),
                    conv.empty_to_none,
                    conv.test(lambda l: len(l) == 1, error = N_(u"List must contain one and only one item")),
                    conv.not_none,
                    ),
                tail = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_text,
                    ),
                TAUX = conv.pipe(
                    conv.test_isinstance(list),
                    conv.uniform_sequence(
                        validate_values_holder_xml_json,
                        drop_none_items = True,
                        ),
                    conv.empty_to_none,
                    conv.test(lambda l: len(l) == 1, error = N_(u"List must contain one and only one item")),
                    conv.not_none,
                    ),
                text = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_text,
                    ),
                ),
            constructor = collections.OrderedDict,
            drop_none_values = 'missing',
            keep_value_order = True,
            ),
        )(slice, state = state)
    conv.remove_ancestor_from_state(state, slice)
    return validated_slice, errors


def validate_slices_xml_json_dates(slices, state = None):
    if not slices:
        return slices, None
    if state is None:
        state = conv.default_state
    errors = {}

    previous_slice = slices[0]
    for slice_index, slice in enumerate(itertools.islice(slices, 1, None), 1):
        for key in ('ASSIETTE', 'SEUIL', 'TAUX'):
            valid_segments = []
            values_holder_xml_json = previous_slice.get(key)
            values_xml_json = values_holder_xml_json[0]['VALUE'] if values_holder_xml_json else []
            for value_xml_json in values_xml_json:
                from_date = datetime.date(*(int(fragment) for fragment in value_xml_json['deb'].split('-')))
                to_date = datetime.date(*(int(fragment) for fragment in value_xml_json['fin'].split('-')))
                if valid_segments and valid_segments[-1][0] == to_date + datetime.timedelta(days = 1):
                    valid_segments[-1] = (from_date, valid_segments[-1][1])
                else:
                    valid_segments.append((from_date, to_date))

            values_holder_xml_json = slice.get(key)
            values_xml_json = values_holder_xml_json[0]['VALUE'] if values_holder_xml_json else []
            for value_index, value_xml_json in enumerate(values_xml_json):
                from_date = datetime.date(*(int(fragment) for fragment in value_xml_json['deb'].split('-')))
                to_date = datetime.date(*(int(fragment) for fragment in value_xml_json['fin'].split('-')))
                for valid_segment in valid_segments:
                    if valid_segment[0] <= from_date and to_date <= valid_segment[1]:
                        break
                else:
                    errors.setdefault(slice_index, {}).setdefault(key, {}).setdefault(0, {}).setdefault('VALUE',
                        {}).setdefault(value_index, {})['deb'] = state._(
                        u"Dates don't belong to valid dates of previous slice")
        previous_slice = slice
    if errors:
        return slices, errors

    for slice_index, slice in enumerate(itertools.islice(slices, 1, None), 1):
        rate_segments = []
        values_holder_xml_json = slice.get('TAUX')
        values_xml_json = values_holder_xml_json[0]['VALUE'] if values_holder_xml_json else []
        for value_xml_json in values_xml_json:
            from_date = datetime.date(*(int(fragment) for fragment in value_xml_json['deb'].split('-')))
            to_date = datetime.date(*(int(fragment) for fragment in value_xml_json['fin'].split('-')))
            if rate_segments and rate_segments[-1][0] == to_date + datetime.timedelta(days = 1):
                rate_segments[-1] = (from_date, rate_segments[-1][1])
            else:
                rate_segments.append((from_date, to_date))

        threshold_segments = []
        values_holder_xml_json = slice.get('SEUIL')
        values_xml_json = values_holder_xml_json[0]['VALUE'] if values_holder_xml_json else []
        for value_xml_json in values_xml_json:
            from_date = datetime.date(*(int(fragment) for fragment in value_xml_json['deb'].split('-')))
            to_date = datetime.date(*(int(fragment) for fragment in value_xml_json['fin'].split('-')))
            if threshold_segments and threshold_segments[-1][0] == to_date + datetime.timedelta(days = 1):
                threshold_segments[-1] = (from_date, threshold_segments[-1][1])
            else:
                threshold_segments.append((from_date, to_date))

        values_holder_xml_json = slice.get('ASSIETTE')
        values_xml_json = values_holder_xml_json[0]['VALUE'] if values_holder_xml_json else []
        for value_index, value_xml_json in enumerate(values_xml_json):
            from_date = datetime.date(*(int(fragment) for fragment in value_xml_json['deb'].split('-')))
            to_date = datetime.date(*(int(fragment) for fragment in value_xml_json['fin'].split('-')))
            for rate_segment in rate_segments:
                if rate_segment[0] <= from_date and to_date <= rate_segment[1]:
                    break
            else:
                errors.setdefault(slice_index, {}).setdefault('ASSIETTE', {}).setdefault(0, {}).setdefault('VALUE',
                    {}).setdefault(value_index, {})['deb'] = state._(u"Dates don't belong to TAUX dates")

        values_holder_xml_json = slice.get('TAUX')
        values_xml_json = values_holder_xml_json[0]['VALUE'] if values_holder_xml_json else []
        for value_index, value_xml_json in enumerate(values_xml_json):
            from_date = datetime.date(*(int(fragment) for fragment in value_xml_json['deb'].split('-')))
            to_date = datetime.date(*(int(fragment) for fragment in value_xml_json['fin'].split('-')))
            for threshold_segment in threshold_segments:
                if threshold_segment[0] <= from_date and to_date <= threshold_segment[1]:
                    break
            else:
                errors.setdefault(slice_index, {}).setdefault('TAUX', {}).setdefault(0, {}).setdefault('VALUE',
                    {}).setdefault(value_index, {})['deb'] = state._(u"Dates don't belong to SEUIL dates")

        values_holder_xml_json = slice.get('SEUIL')
        values_xml_json = values_holder_xml_json[0]['VALUE'] if values_holder_xml_json else []
        for value_index, value_xml_json in enumerate(values_xml_json):
            from_date = datetime.date(*(int(fragment) for fragment in value_xml_json['deb'].split('-')))
            to_date = datetime.date(*(int(fragment) for fragment in value_xml_json['fin'].split('-')))
            for rate_segment in rate_segments:
                if rate_segment[0] <= from_date and to_date <= rate_segment[1]:
                    break
            else:
                errors.setdefault(slice_index, {}).setdefault('SEUIL', {}).setdefault(0, {}).setdefault('VALUE',
                    {}).setdefault(value_index, {})['deb'] = state._(u"Dates don't belong to TAUX dates")

    return slices, errors or None


def validate_value_xml_json(value, state = None):
    if value is None:
        return None, None
    container = state.ancestors[-1]
    value_converter = dict(
        bool = conv.pipe(
            conv.test_isinstance(basestring),
            conv.cleanup_line,
            conv.test_in([u'0', u'1']),
            ),
        float = conv.pipe(
            conv.test_isinstance(basestring),
            conv.cleanup_line,
            conv.test_conv(conv.anything_to_float),
            ),
        integer = conv.pipe(
            conv.test_isinstance(basestring),
            conv.cleanup_line,
            conv.test_conv(conv.anything_to_strict_int),
            ),
        percent = conv.pipe(
            conv.test_isinstance(basestring),
            conv.cleanup_line,
            conv.test_conv(conv.anything_to_float),
            ),
        )[container.get('format') or 'float']  # Only CODE have a "format".
    state = conv.add_ancestor_to_state(state, value)
    validated_value, errors = conv.pipe(
        conv.test_isinstance(dict),
        conv.struct(
            dict(
                code = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_line,
                    ),
                deb = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.iso8601_input_to_date,
                    conv.date_to_iso8601_str,
                    conv.not_none,
                    ),
                fin = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.iso8601_input_to_date,
                    conv.date_to_iso8601_str,
                    conv.not_none,
                    ),
                format = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.input_to_slug,
                    conv.test_in(xml_json_formats),
                    conv.test_equals(container.get('format')),
                    ),
                tail = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_text,
                    ),
                text = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.cleanup_text,
                    ),
                type = conv.pipe(
                    conv.test_isinstance(basestring),
                    conv.input_to_slug,
                    conv.test_in([
                        'age',
                        'days',
                        'hours',
                        'monetary',
                        'months',
                        ]),
                    conv.test_equals(container.get('type')),
                    ),
                valeur = conv.pipe(
                    value_converter,
                    conv.not_none,
                    ),
                ),
            constructor = collections.OrderedDict,
            drop_none_values = 'missing',
            keep_value_order = True,
            ),
        )(value, state = state)
    conv.remove_ancestor_from_state(state, value)
    return validated_value, errors


validate_values_holder_xml_json = conv.struct(
    dict(
        VALUE = conv.pipe(
            conv.test_isinstance(list),
            conv.uniform_sequence(
                validate_value_xml_json,
                drop_none_items = True,
                ),
            make_validate_values_xml_json_dates(require_consecutive_dates = False),
            conv.empty_to_none,
            conv.not_none,
            ),
        ),
    constructor = collections.OrderedDict,
    drop_none_values = 'missing',
    keep_value_order = True,
    )


def xml_legislation_to_json(xml_element, state = None):
    if xml_element is None:
        return None, None
    json_key, json_element = translate_xml_element_to_json_item(xml_element)
    if json_key != 'NODE':
        if state is None:
            state = conv.default_state
        return json_element, state._(u'Invalid root element in XML: "{}" instead of "NODE"').format(xml_element.tag)
    return json_element, None
