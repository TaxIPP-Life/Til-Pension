# -*- coding: utf-8 -*-

import calendar
import collections
import copy
import datetime as dt
import gc
import numpy as np
import pandas as pd

from time_array import TimeArray
from utils_pension import build_long_values, build_long_baremes, _isin, valbytranches
#from .columns import EnumCol, EnumPresta
#from .taxbenefitsystems import TaxBenefitSystem

first_year_sal = 1949 



class PensionSimulation(object):
    """
    A Simulation class tailored to compute pensions (deal with survey data )
    """
    descr = None
     
    def __init__(self, survey_filename = None):
        self.survey_filename = survey_filename
        self.workstate = None
        self.sali = None
        self.dates = None
        self.code_regime = None
        self.regime = None
        self.info_ind = None
        self.time_step = None
        self.data_type = None
        self.first_year = None
        self.yearsim = None
        
    def set_config(self, **kwargs):
        """
        Configures the PensionSimulation
        """
        # Setting general attributes and getting the specific ones
        for key, val in kwargs.iteritems():
            if hasattr(self, key):
                setattr(self, key, val)
        if self.data_type == 'numpy':
            sali = TimeArray(self.sali, self.dates)
            setattr(self, 'sali', sali)
            workstate = TimeArray(self.workstate, self.dates)
            setattr(self, 'workstate', workstate)
        if self.first_year:
            workstate.selected_dates(first=first_year_sal, last=self.yearsim, inplace=True) 
            sali.selected_dates(first=first_year_sal, last=self.yearsim, inplace=True)
            
#    def build_sal_regime(self):
#        self.sal_regime = self.sali.array*_isin(self.workstate.array,self.code_regime)
#        
    def calculate_taux(self, decote, surcote):
        ''' Détermination du taux de liquidation à appliquer à la pension '''
        taux_plein = self._P.plein.taux
        return taux_plein*(1 - decote + surcote)
        
    def nombre_points(self, first_year=first_year_sal, last_year=None, data_type='numpy'):
        ''' Détermine le nombre de point à liquidation de la pension dans les régimes complémentaires (pour l'instant Ok pour ARRCO/AGIRC)
        Pour calculer ces points, il faut diviser la cotisation annuelle ouvrant des droits par le salaire de référence de l'année concernée 
        et multiplier par le taux d'acquisition des points'''
        yearsim = self.yearsim
        last_year_sali = yearsim - 1
        if last_year == None:
            last_year = last_year_sali
        regime = self.regime
        P = self._P.complementaire.__dict__[regime]
        Plong = self._Plongitudinal.prive.complementaire.__dict__[regime]
        salref = build_long_values(Plong.sal_ref, first_year=first_year_sal, last_year=yearsim)
        plaf_ss = self._Plongitudinal.common.plaf_ss
        pss = build_long_values(plaf_ss, first_year=first_year_sal, last_year=yearsim)    
        taux_cot = build_long_baremes(Plong.taux_cot_moy, first_year=first_year_sal, last_year=yearsim, scale=pss)
        sali = self.sal_regime
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
 
#    def coeff_age(self, agem, trim):
#        ''' TODO: add surcote  pour avant 1955 '''
#        regime = self.regime
#        P = self._P.complementaire.__dict__[regime]
#        coef_mino = P.coef_mino
#        age_annulation_decote = valbytranches(self._P.RG.decote.age_null, self.info_ind) 
#        N_taux = valbytranches(self._P.RG.plein.N_taux, self.info_ind)
#        diff_age = np.maximum(np.divide(age_annulation_decote - agem, 12), 0)
#        coeff_min = pd.Series(np.zeros(len(agem)), index=agem.index)
#        coeff_maj = pd.Series(np.zeros(len(agem)), index=agem.index)
#        for nb_annees, coef_mino in coef_mino._tranches:
#            coeff_min += (diff_age == nb_annees)*coef_mino
#        if self.yearsim <= 1955:
#            maj_age = np.maximum(np.divide(agem - age_annulation_decote, 12), 0)
#            coeff_maj = maj_age*0.05
#            return coeff_min + coeff_maj
#        elif  self.yearsim < 1983:
#            return coeff_min
#        elif self.yearsim >= 1983:
#            # A partir de cette date, la minoration ne s'applique que si la durée de cotisation au régime général est inférieure à celle requise pour le taux plein
#            return  coeff_min*(N_taux > trim) + (N_taux <= trim)             