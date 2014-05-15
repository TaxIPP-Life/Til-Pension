# -*- coding: utf-8 -*-

import calendar
import collections
import copy
import datetime as dt
import gc
import numpy as np
import pandas as pd

from time_array import TimeArray
from utils_pension import _isin, build_long_values, build_long_baremes, translate_frequency, valbytranches
first_year_sal = 1949

class Regime(object):
    """
    A Simulation class tailored to compute pensions (deal with survey data )
    """
    descr = None
     
    def __init__(self):
        self.code_regime = None
        self.regime = None
        self.param_name = None
        
        self.info_ind = None
        self.dates = None
        
        self.time_step = None
        self.data_type = None
        self.first_year = None
        self.yearsim = None
        
        self.P = None
        self.P_longit = None
        
    def set_config(self, **kwargs):
        """
        Configures the Regime
        """
        # Setting general attributes and getting the specific ones
        for key, val in kwargs.iteritems():
            if hasattr(self, key):
                setattr(self, key, val)
                
    def _decote(self):
        raise NotImplementedError

    def _surcote(self):
        raise NotImplementedError
       
    def calculate_taux(self, decote, surcote):
        ''' Détérmination du taux de liquidation à appliquer à la pension '''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        taux_plein = P.plein.taux
        decote = self._decote()
        surcote = self._surcote()
        return taux_plein*(1 - decote + surcote)
    
    def calculate_coeff_proratisation(self):
        raise NotImplementedError
            
    def calculate_salref(self):
#         self.sal_regime = sali.array*_isin(self.workstate.array,self.code_regime)
        raise NotImplementedError
    
    def calculate_pension(self):
        taux = self.calculate_taux()
        cp = self.calculate_coeff_proratisation()
        salref = self.calculate_salref()
        return cp*salref*taux


class RegimeBase(Regime):

    def nb_trim_valide(self, workstate, code=None): #sali, 
        ''' Cette fonction pertmet de calculer des nombres par trimestres
        TODO: gérer la comptabilisation des temps partiels quand variable présente'''
        assert isinstance(workstate, TimeArray)
        #assert isinstance(sali, TimeArray)
        if code is None:
            code = self.code_regime
        wk_selection = TimeArray(_isin(workstate.array, self.code_regime), workstate.dates)
        wk_selection.array, wk_selection.dates = translate_frequency(wk_selection, input_frequency=self.time_step, output_frequency='month')
        trim = np.divide(wk_selection.array.sum(axis=1), 4).astype(int)
        return trim
    
    def revenu_valides(self, workstate, sali, code=None): #sali, 
        ''' Cette fonction pertmet de calculer des nombres par trimestres
        TODO: gérer la comptabilisation des temps partiels quand variable présente'''
        assert isinstance(workstate, TimeArray)
        #assert isinstance(sali, TimeArray)
        if code is None:
            code = self.code_regime
        wk_selection = TimeArray(_isin(workstate.array, self.code_regime), workstate.dates)
        wk_selection.array, wk_selection.dates = translate_frequency(wk_selection, \
                                        input_frequency=self.time_step, output_frequency='month')
        #TODO: condition not assuming sali is in year
        sali = TimeArray(*translate_frequency(sali, input_frequency=self.time_step, output_frequency='month'))
        sali.array = np.around(np.divide(sali.array, 12), decimals=3)
        sal_selection = TimeArray(wk_selection.array*sali.array, sali.dates)
        trim = np.divide(wk_selection.array.sum(axis=1), 4).astype(int)
        return trim
    
    def get_trimester(self, workstate, sali):
        raise NotImplementedError
    

class RegimeComplementaires(Regime):
    
    def plaf_sali(self, sali):
        ''' Cette fonction plafonne les salaires des cadres 1 pss pour qu'il ne paye que la première tranche '''
        sali = sali.array
        yearsim = self.yearsim
        plaf_ss = self.P_longit.common.plaf_ss
        pss = build_long_values(plaf_ss, first_year=first_year_sal, last_year=yearsim) 
        return np.minimum(sali, pss)
    
    def old_plaf_sali(self, workstate, sali):
        cadre_selection = (workstate.array == self.code_cadre)
        noncadre_selection = ~cadre_selection
        plaf_sali = self.plaf_sali(sali) 
        return sali.array*noncadre_selection + plaf_sali*cadre_selection
    
    
        
    def nombre_points(self, sali, first_year=first_year_sal, last_year=None, data_type='numpy'):
        ''' Détermine le nombre de point à liquidation de la pension dans les régimes complémentaires (pour l'instant Ok pour ARRCO/AGIRC)
        Pour calculer ces points, il faut diviser la cotisation annuelle ouvrant des droits par le salaire de référence de l'année concernée 
        et multiplier par le taux d'acquisition des points'''
        yearsim = self.yearsim
        last_year_sali = yearsim - 1
        if last_year == None:
            last_year = last_year_sali
        regime = self.regime
        P = reduce(getattr, self.param_name.split('.'), self.P)
        P = P.complementaire.__dict__[regime]
        Plong = self.P_longit.prive.complementaire.__dict__[regime]
        salref = build_long_values(Plong.sal_ref, first_year=first_year_sal, last_year=yearsim)
        plaf_ss = self.P_longit.common.plaf_ss
        pss = build_long_values(plaf_ss, first_year=first_year_sal, last_year=yearsim)    
        taux_cot = build_long_baremes(Plong.taux_cot_moy, first_year=first_year_sal, last_year=yearsim, scale=pss)
        assert len(salref) == sali.shape[1] == len(taux_cot)
        if data_type == 'pandas':
            nb_points = pd.Series(np.zeros(len(sali.index)), index=sali.index)
            if last_year_sali < first_year:
                return nb_points
            for year in range(first_year, min(last_year_sali, last_year) + 1):
                points_acquis = np.divide(taux_cot[year].calc(sali[year*100 + 1]), salref[year-first_year_sal]).round(2) 
                gmp = P.gmp
                #print year, taux_cot[year], sali.ix[1926 ,year *100 + 1], salref[year-first_year_sal]
                #print 'result', pd.Series(points_acquis, index=sali.index).ix[1926]
                nb_points += np.maximum(points_acquis, gmp)*(points_acquis > 0)
            return nb_points
        if data_type == 'numpy':
            nb_points = np.zeros(sali.shape[0])
            if last_year_sali < first_year:
                return nb_points
            for year in range(first_year, min(last_year_sali, last_year) + 1):
                ix_year = year - first_year
                points_acquis = np.divide(taux_cot[year].calc(sali[:,ix_year]), salref[year-first_year_sal]).round(2) 
                gmp = P.gmp
                #print year, taux_cot[year], sali.ix[1926 ,year *100 + 1], salref[year-first_year_sal]
                #print 'result', pd.Series(points_acquis, index=sali.index).ix[1926]
                nb_points += np.maximum(points_acquis, gmp)*(points_acquis > 0)
            return nb_points
 
    def coeff_age(self, agem, trim):
        ''' TODO: add surcote  pour avant 1955 '''
        regime = self.regime
        P = reduce(getattr, self.param_name.split('.'), self.P)
        P = P.complementaire.__dict__[regime]
        coef_mino = P.coef_mino
        age_annulation_decote = valbytranches(self.P.prive.RG.decote.age_null, self.info_ind) #TODO: change the param place
        N_taux = valbytranches(self.P.prive.RG.plein.N_taux, self.info_ind) #TODO: change the param place
        diff_age = np.maximum(np.divide(age_annulation_decote - agem, 12), 0)
        coeff_min = pd.Series(np.zeros(len(agem)), index=agem.index)
        coeff_maj = pd.Series(np.zeros(len(agem)), index=agem.index)
        for nb_annees, coef_mino in coef_mino._tranches:
            coeff_min += (diff_age == nb_annees)*coef_mino
        if self.yearsim <= 1955:
            maj_age = np.maximum(np.divide(agem - age_annulation_decote, 12), 0)
            coeff_maj = maj_age*0.05
            return coeff_min + coeff_maj
        elif  self.yearsim < 1983:
            return coeff_min
        elif self.yearsim >= 1983:
            # A partir de cette date, la minoration ne s'applique que si la durée de cotisation au régime général est inférieure à celle requise pour le taux plein
            return  coeff_min*(N_taux > trim) + (N_taux <= trim)             