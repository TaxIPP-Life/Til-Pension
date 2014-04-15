# -*- coding: utf-8 -*-

import calendar
import datetime as dt
import numpy as np
import pandas as pd


def interval_years(table):
    table = pd.DataFrame(table)
    if 'id' in table.columns:
        table = table.drop(['id'], axis = 1)
    table = table.reindex_axis(sorted(table.columns), axis=1)
    year_start = int(str(table.columns[0])[0:4])
    year_end = int(str(table.columns[-1])[0:4])
    return year_start, year_end + 1


def years_to_months(table, division = False):
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