# -*- coding: utf-8 -*-

import calendar
import collections
import pdb
import datetime as dt
from datetime import datetime

from numpy import array, ones, zeros
from pandas import DataFrame


def substract_months(sourcedate, months):
    ''' fonction soustrayant le nombre de "months" donné à la "sourcedate" indiquée '''
    month = sourcedate.month - 1 - months
    year = sourcedate.year + month / 12
    month = month % 12 + 1
    day = min(sourcedate.day,calendar.monthrange(year,month)[1])
    return dt.date(year,month,day)


def build_naiss(agem, datesim):
    ''' Détermination de la date de naissance à partir de l'âge et de la date de simulation '''
    naiss = agem.apply(lambda x: substract_months(datesim, int(x)))
    return naiss

def _info_numpy(np_object, ident, list_ident, text=None):
    id_ix = list(list_ident).index(ident)
    if text:
        print str(text) + " : "
    if len(np_object.shape) == 2:
        #type = '2d-matrix'
        return np_object[id_ix, :]
    else:
        #type = 'vector'
        return np_object[id_ix]

def print_multi_info_numpy(list_timearray, ident, list_ident):
    to_print = {}
    first_shape = list_timearray[0].array.shape
    max_nb_dates = 0
    print "Les informatons personnelles de l'individu {} sont : ".format(ident)
    for timearray in list_timearray:
        array = timearray.array
        assert len(array.shape) == 2
        nb_rows = array.shape[0]
        nb_cols = array.shape[1]
        assert first_shape[0] == nb_rows
        if nb_cols > max_nb_dates:
            max_nb_dates = nb_cols
    
    for timearray in list_timearray:
        array = timearray.array
        nb_dates = array.shape[1]
        col_to_print = _info_numpy(array, ident, list_ident, text=None)
        if nb_dates < max_nb_dates:
            long_col_to_print = zeros(max_nb_dates)
            long_col_to_print[-len(col_to_print):] = col_to_print
            col_to_print = long_col_to_print
        to_print[timearray.name] = col_to_print
    print DataFrame(to_print).to_string()
        