# -*- coding: utf-8 -*-

import calendar
import collections
import datetime as dt
import numpy as np
import pandas as pd

from datetime import date

def interval_years(table):
    table = pd.DataFrame(table)
    if 'id' in table.columns:
        table = table.drop(['id'], axis = 1)
    table = table.reindex_axis(sorted(table.columns), axis=1)
    year_start = int(str(table.columns[0])[0:4])
    year_end = int(str(table.columns[-1])[0:4])
    return year_start, year_end + 1


def years_to_months(table, division=False):
    ''' 
    input : yearly-table 
    output: monthly-table with :
        - division == False : val[yyyymm] = val[yyyy]
        - division == True : val[yyyymm] = val[yyyy] / 12
    '''
    #TODO: use only numpy
    if 'id' in table.columns:
        table = table.drop(['id'], axis = 1)
        
    year_start, year_end = interval_years(table)
    for year in range(year_start, year_end) :
        for i in range(2,13):
            date = year * 100 + i
            table[date] = table[ year * 100 + 1 ]
    table = table.reindex_axis(sorted(table.columns), axis=1)
    table = np.array(table)
    if division == True:
        table = np.around(np.divide(table, 12), decimals = 3)
    return table


def months_to_years(table):
    year_start, year_end = interval_years(table)
    new_table = pd.DataFrame(index = table.index, columns = [(year * 100 + 1) for year in range(year_start, year_end)]).fillna(0)
    for year in range(year_start, year_end) :
        year_data = table[ year * 100 + 1 ]
        for i in range(2,13):
            date = year * 100 + i
            year_data += table[date]
        new_table.loc[:, year * 100 + 1] = year_data
    return new_table.astype(float)


def substract_months(sourcedate,months):
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
    
def table_selected_dates(table, first_year=None, last_year=None):
    ''' La table d'input dont les colonnes sont des dates est renvoyées emputée des années postérieures à last_year (last_year incluse) 
    et antérieures à first_year (first_year incluse) '''
    dates_to_drop = []
    if last_year:
        for date in table.columns:
            if int(date) > last_year * 100 + 1:
                dates_to_drop.append(date)
    if first_year:
        for date in table.columns:
            if int(date) < first_year * 100 + 1 :
                dates_to_drop.append(date)
    return table.drop(dates_to_drop, axis = 1)

        
def build_long_values(param_long, first_year, last_year):   
    ''' Cette fonction permet de traduire les paramètres longitudinaux en vecteur numpy 
    comportant une valeur par année comprise en first_year et last_year '''
    param = pd.DataFrame( {'year' : range(first_year, last_year), 'param' : - np.ones(last_year - first_year)} ) 
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
    return param['param'] 

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