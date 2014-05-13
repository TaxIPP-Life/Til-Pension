# -*- coding: utf-8 -*-

import calendar
import collections
import pdb
import datetime as dt
import numpy as np
from pandas import DataFrame

from datetime import date
from xml.etree import ElementTree
from Param import legislations_add_pension as legislations
from Param import legislationsxml_add_pension as  legislationsxml
from openfisca_core import conv

def sum_by_years(table):
    years = set([x//100 for x in table.columns])
    years_columns = [100*year + 1 for year in years]
    output = table.loc[:,years_columns]
    for month in range(1,12):
        month_to_add = [year + month for year in years_columns]
        output += table.loc[:, month_to_add].values
    return output


def substract_months(sourcedate, months):
    ''' fonction soustrayant le nombre de "months" donné à la "sourcedate" indiquée '''
    month = sourcedate.month - 1 - months
    year = sourcedate.year + month / 12
    month = month % 12 + 1
    day = min(sourcedate.day,calendar.monthrange(year,month)[1])
    return dt.date(year,month,day)

def valbytranches(param, info_ind):
    ''' Associe à chaque individu la bonne valeur du paramètre selon la valeur de la variable de control 
    var_control spécifié au format date (exemple : date de naissance) '''
    if '_control' in  param.__dict__ :
        var_control = info_ind[str(param.control)]
        param_indiv = var_control.copy()
        for i in range(param._nb) :
            param_indiv[(var_control >= param._tranches[i][0])] = param._tranches[i][1]
        return param_indiv
    else:
        return param


def build_long_values(param_long, first_year, last_year):   
    ''' Cette fonction permet de traduire les paramètres longitudinaux en vecteur numpy 
    comportant une valeur par année comprise en first_year et last_year '''
    param = DataFrame( {'year' : range(first_year, last_year), 'param' : - np.ones(last_year - first_year)} ) 
    param_t = []
    for year in range(first_year, last_year):
        param_old = param_t
        param_t = []
        for key in param_long.keys():
            if str(year) in key:
                param_t.append(key)
        if not param_t:
            param_t = param_old
        param.loc[param['year'] == year, 'param'] = param_long[param_t[0]] # Hypothèse sous-jacente : on prend la première valeur de l'année
    return np.array(param['param'])

def build_long_baremes(bareme_long, first_year, last_year, scale=None):   
    ''' Cette fonction permet de traduire les barèmes longitudinaux en dictionnaire de bareme
    comportant un barème par année comprise en first_year et last_year'''
    baremes = collections.OrderedDict()
    bareme_t = []
    for year in range(first_year, last_year):
        bareme_old = bareme_t
        bareme_t = []
        for key in bareme_long.keys():
            if str(year) in key:
                bareme_t.append(key)
        if not bareme_t:
            bareme_t = bareme_old
        baremes[year] = bareme_long[bareme_t[0]]
    if scale is not None:
        from Param.Scales import scaleBaremes
        assert len(scale) == len(baremes)
        for year, val_scale in zip(baremes.keys(),scale):
            baremes[year] = scaleBaremes(baremes[year], val_scale)
    return baremes

def calculate_age(birth_date, date):
    ''' calculate age at date thanks birthdate '''
    def _age(birthdate):
        try: 
            birthday = birthdate.replace(year=date.year)
        except ValueError: # raised when birth date is February 29 and the current year is not a leap year
            birthday = birthdate.replace(year=date.year, month=birthdate.month+1, day=1)
        if birthday > date:
            return date.year - birthdate.year - 1
        else:
            return date.year - birthdate.year
    return birth_date.apply(_age)


def build_naiss(agem, datesim):
    ''' Détermination de la date de naissance à partir de l'âge et de la date de simulation '''
    naiss = agem.apply(lambda x: substract_months(datesim, int(x)))
    return naiss

def _isin(table, selected_values, data_type='numpy'):
    selection = np.in1d(table, selected_values).reshape(table.shape)
    if data_type == 'pandas':
        return DataFrame(selection, index=table.index.copy(), columns=table.columns.copy())
    if data_type == 'numpy':
        return selection

def translate_frequency(table, input_frequency='month', output_frequency='month', method=None,
                         data_type='numpy'):
    '''method should eventually control how to switch from month based table to year based table
        so far we assume year is True if January is True 
        idea : format_table as an argument instead of testing with isinstance
        '''
    if input_frequency == output_frequency:
        return table
        
    if data_type == 'numpy':
        if output_frequency == 'year': # if True here, input_frequency=='month'
            assert len(table.dates) % 12 == 0 #TODO: to remove eventually
            nb_years = len(table.dates) // 12
            output_dates = [date for date in table.dates if date % 100 == 1]
            output_dates_ix = table.dates.index(output_dates)
            #here we could do more complex
            if method is None: #first month of each year
                return table.array[:, output_dates_ix], output_dates
            if method is 'sum':
                output = table[:, output_dates_ix].copy()
                for month in range(1,12):
                    month_to_add = [year*12 + month for year in xrange(nb_years)]
                    output += table[:, month_to_add]
                return output, output_dates

        if output_frequency == 'month': # if True here, input_frequency=='year'
            output_dates = [year + month for year in table.dates for month in range(12)]
            return np.repeat(table.array, 12, axis=1), output_dates
            #return np.kron(table, np.ones(12))
    else:
        assert data_type == 'pandas'
        if output_frequency == 'year': # if True here, input_frequency=='month'
            detected_years = set([date // 100 for date in table.columns])
            output_dates = [100*x + 1 for x in detected_years]
            #here we could do more complex
            if method is None:
                return table.loc[:, output_dates]
            if method is 'sum':
                pdb.set_trace()
        if output_frequency == 'month': # if True here, input_frequency=='year'
            output_dates = [x + k for k in range(12) for x in table.columns ]
            output_table1 = DataFrame(np.tile(table, 12), index=table.index, columns=output_dates)
            return output_table1.reindex_axis(sorted(output_table1.columns), axis=1)  
        
def table_selected_dates(table, dates, first_year=None, last_year=None):
    ''' La table d'input dont les colonnes sont des dates est renvoyées emputée des années postérieures à last_year (last_year non-incluse) 
    et antérieures à first_year (first_year incluse) '''
    try:
        idx1 = dates.index(100*first_year + 1)
    except:
        idx1 = 0
    try:
        idx2 = dates.index(100*(last_year + 1) + 1)
    except:
        idx2 = len(dates)
    idx_to_take = range(idx1, idx2)
    return table[:,idx_to_take]

def load_param(param_file, date):
    ''' It's a simplification of an (old) openfisca program '''
    legislation_tree = ElementTree.parse(param_file)
    legislation_xml_json = conv.check(legislationsxml.xml_legislation_to_json)(legislation_tree.getroot(),
        state = conv.default_state)
    legislation_xml_json, _ = legislationsxml.validate_node_xml_json(legislation_xml_json,
        state = conv.default_state)
    _, legislation_json = legislationsxml.transform_node_xml_json_to_json(legislation_xml_json)
    dated_legislation_json = legislations.generate_dated_legislation_json(legislation_json, date)
    compact_legislation = legislations.compact_dated_node_json(dated_legislation_json)
    return compact_legislation

