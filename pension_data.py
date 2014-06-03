# -*- coding: utf-8 -*-
from datetime import date
from numpy import array, ndarray
from pandas import DataFrame
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
        
        assert sorted(sali.dates) == sali.dates
        self.initial_date = DateTil(sali.dates[0])
        
        if 'date_liquidation' not in info_ind.columns:
            self.info_ind['date_liquidation'] = datesim.datetime
        
    def selected_dates(self, first=None, last=None, date_type='year', inplace=False):
        ''' cf TimeArray '''
        if inplace:
            self.workstate.selected_dates(first, last, date_type, inplace=True)
            self.sali.selected_dates(first, last, date_type, inplace=True)
        else:
            wk = self.workstate.selected_dates(first, last, date_type, False)
            sal = self.sali.selected_dates(first, last, date_type, False)
            return PensionData(wk, sal, self.info_ind)
        
    def translate_frequency(self, output_frequency='month', method=None, inplace=False):
        ''' cf TimeArray '''
        if inplace:
            self.workstate.translate_frequency(output_frequency, method, inplace=True)
            self.sali.translate_frequency(output_frequency, method, inplace=True)
        else:
            wk = self.workstate.translate_frequency(output_frequency, method, False)
            sal = self.sali.translate_frequency(output_frequency, method, False)
            return PensionData(wk, sal, self.info_ind)

    @classmethod
    def from_arrays(cls, workstate, sali, info_ind, datesim=None):
        if isinstance(sali, DataFrame):
            assert isinstance(workstate, DataFrame)
            try:
                assert all(sali.index == workstate.index) and all(sali.index == info_ind.index)
            except:
                assert all(sali.index == workstate.index)
                assert len(sali) == len(info_ind)
                sal = sali.index
                idx = info_ind.index
                assert all(sal[sal.isin(idx)] == idx[idx.isin(sal)])
                print(sal[~sal.isin(idx)])
                print(idx[~idx.isin(sal)])
                # un décalage ?
                decal = idx[~idx.isin(sal)][0] - sal[~sal.isin(idx)][0]
                import pdb
                pdb.set_trace()
        
            #TODO: should be done before
            assert sali.columns.tolist() == workstate.columns.tolist()
            assert sali.columns.tolist() == (sorted(sali.columns))
            dates = sali.columns.tolist()
            sali = array(sali)
            workstate = array(workstate)
        
        if isinstance(sali, ndarray):
            assert isinstance(workstate, ndarray)
            sali = TimeArray(sali, dates, name='sali')
            workstate = TimeArray(workstate, dates, name='workstate')
            
        return PensionData(workstate, sali, info_ind, datesim)
        