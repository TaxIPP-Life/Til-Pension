# -*- coding: utf-8 -*-
from datetime import date
from numpy import maximum, array, nan_to_num, greater, divide, around, zeros, minimum
from pandas import Series
from time_array import TimeArray
from datetil import DateTil
from utils_pension import build_long_values, build_long_baremes
first_year_sal = 1949
compare_destinie = True 

class PensionData(object):
    '''
    Class à envoyer à Simulation de Til-pension
    '''
    def __init__(self, workstate, sali, info_ind, datesim=None): 
        assert isinstance(workstate, TimeArray)
        assert isinstance(sali, TimeArray)
        assert workstate.dates == sali.dates
        
        self.workstate = workstate
        self.sali = sali
        self.info_ind = info_ind
        
        if datesim is None: 
            datesim = max(sali.dates)
        datesim = DateTil(datesim)
        self.datesim = datesim
        
    def selected_dates(self, first=None, last=None, date_type='year', inplace=False):
        ''' cf TimeArray '''
        if inplace:
            self.workstate.selected_dates(first, last, date_type, inplace=True)
            self.sali.selected_dates(first, last, date_type, inplace=True)
        else:
            wk = self.workstate.selected_dates(first, last, date_type, False)
            sal = self.sali.selected_dates(first, last, date_type, False)
            return PensionData(wk, sal, self.info_ind, self.datesim)
        