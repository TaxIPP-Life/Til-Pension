# -*- coding: utf-8 -*-

import calendar
import collections
import pdb
import datetime as dt

from numpy import array, ones
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
    if isinstance(param, float) or isinstance(param, int):
        return param
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
    param = DataFrame( {'year' : range(first_year, last_year), 'param' : - ones(last_year - first_year)} ) 
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
    return array(param['param'])

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


def build_salref_bareme(bareme_long, first_year, last_year, scale=None):
    '''
    salaire trimestriel de référence minimum
    Rq : Toute la série chronologique est exprimé en euros
    '''
    assert first_year <= 1972 
    assert last_year > 1972
    salmin = DataFrame({'year': range(first_year, last_year ), 'sal': -ones(last_year - first_year)} ) 
    avts_year = []
    smic_year = []
    smic_long = bareme_long.smic
    avts_long = bareme_long.avts.montant
    for year in range(first_year, 1972):
        avts_old = avts_year
        avts_year = []
        for key in avts_long.keys():
            if str(year) in key:
                avts_year.append(key)
        if not avts_year:
            avts_year = avts_old
        salmin.loc[salmin['year'] == year, 'sal'] = avts_long[avts_year[0]] 
        
    #TODO: Trancher si on calcule les droits à retraites en incluant le travail à l'année de simulation pour l'instant
    #non (ex : si datesim = 2009 on considère la carrière en emploi jusqu'en 2008)
    for year in range(1972, last_year):
        smic_old = smic_year
        smic_year = []
        for key in smic_long.keys():
            if str(year) in key:
                smic_year.append(key)
        if not smic_year:
            smic_year = smic_old
        if year <= 2013 :
            salmin.loc[salmin['year'] == year, 'sal'] = 200*smic_long[smic_year[0]]
            if year <= 2001 :
                salmin.loc[salmin['year'] == year, 'sal'] = 200*smic_long[smic_year[0]]/6.5596
        else:
            salmin.loc[salmin['year'] == year, 'sal'] = 150*smic_long[smic_year[0]]
    return array(salmin['sal'])

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
    long_dated_legislation_json = legislations.generate_long_legislation_json(legislation_json, date)
    compact_legislation_long = legislations.compact_long_dated_node_json(long_dated_legislation_json)
    return compact_legislation, compact_legislation_long

def print_info_numpy(np_object, ident, list_ident, text=None):
    id_ix = list(list_ident).index(ident)
    if text:
        print str(text) + " : "
    if len(np_object.shape) == 2:
        #type = '2d-matrix'
        print np_object[id_ix, :]
    else:
        #type = 'vector'
        print np_object[id_ix]

