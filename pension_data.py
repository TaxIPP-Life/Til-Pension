# -*- coding: utf-8 -*-

from numpy import array, ndarray
from pandas import DataFrame
from time_array import TimeArray
from datetil import DateTil

compare_destinie = True 

class PensionData(object):
    '''
    Class à envoyer à Simulation de Til-pension
    '''
    def __init__(self, workstate, sali, info_ind): 
        assert isinstance(workstate, TimeArray)
        assert isinstance(sali, TimeArray)
        self.workstate = workstate
        self.sali = sali
        self.info_ind = info_ind
        
        
        assert workstate.dates == sali.dates
        dates = sali.dates
        assert sorted(dates) == dates
        self.last_date = None #intialisation for assertion in set_dates
        self.set_dates(dates)
        if 'date_liquidation' not in info_ind.columns:
            self.info_ind['date_liquidation'] = self.last_date.datetime
  
    def set_dates(self, dates):
        self.dates = dates
        # on ne change pas last_date pour ne pas avoir d'incohérence avec date_liquidation
        if self.last_date is not None and DateTil(dates[-1]).liam != self.last_date.liam:
            raise Exception("Impossible to change last_date of a data_frame")
        self.last_date = DateTil(dates[-1])
        self.first_date = DateTil(dates[0])
        
    def selected_dates(self, first=None, last=None, date_type='year', inplace=False):
        ''' cf TimeArray '''
        if inplace:
            self.workstate.selected_dates(first, last, date_type, inplace=True)
            self.sali.selected_dates(first, last, date_type, inplace=True)
            self.set_dates(self.sali.dates)
        else:
            wk = self.workstate.selected_dates(first, last, date_type)
            sal = self.sali.selected_dates(first, last, date_type)
            return PensionData(wk, sal, self.info_ind)
        
    def selected_regime(self, code_regime):
        ''' Cette fonction renvoie une copie corrigée de l'objet PensionData dans lequel :
        - tous les workstate de data.workstate qui ne figurent pas dans code_regime sont remplacés par 0
        - tous les salaires non-associés à un workstate dans code_regime sont remplacés par 0
        '''
        wk_selection = self.workstate.isin([code_regime])
        sal = self.sali.copy()
        work = self.workstate.copy()
        wk_regime = TimeArray(wk_selection.array*work.array, sal.dates, name='workstate_regime')
        sal_regime = TimeArray(wk_selection.array*sal.array, sal.dates, name='sali_regime') 
        return PensionData(wk_regime, sal_regime, self.info_ind)
        
    def translate_frequency(self, output_frequency='month', method=None, inplace=False):
        ''' cf TimeArray '''
        if inplace:
            self.workstate.translate_frequency(output_frequency, method, inplace=True)
            self.sali.translate_frequency(output_frequency, method, inplace=True)
            self.set_dates(self.sali.dates)
        else:
            wk = self.workstate.translate_frequency(output_frequency, method)
            sal = self.sali.translate_frequency(output_frequency, method)
            return PensionData(wk, sal, self.info_ind)

    @classmethod
    def from_arrays(cls, workstate, sali, info_ind, dates=None):
        if isinstance(sali, DataFrame):
            assert isinstance(workstate, DataFrame)
            try:
                assert all(sali.index == workstate.index) and all(sali.index == info_ind.index)
            except:
                assert all(sali.index == workstate.index)
                assert len(sali) == len(info_ind)
                sal = sali.index
                idx = info_ind.index
                assert all(sal[sal.isin(idx)] == idx[idx.isin(sal)]) #ici c'est que l'ordre change
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
        
        assert info_ind['sexe'].isin([0,1]).all() 
        return PensionData(workstate, sali, info_ind)
        