# -*- coding:utf-8 -*-
import math
from datetime import datetime

import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir) 
from time_array import TimeArray

from numpy import maximum, minimum, array, divide, zeros, multiply, ceil
from pandas import DataFrame

from regime import compare_destinie
from Regime_general import RegimeGeneral
from utils_pension import build_long_values, build_salref_bareme, _info_numpy, print_multi_info_numpy
from pension_functions import nb_trim_surcote, sal_to_trimcot, unemployment_trimesters

code_avpf = 8
code_chomage = 2
code_preretraite = 9
first_year_indep = 1972

class RegimeSocialIndependants(RegimeGeneral):
    
    def __init__(self):
        RegimeGeneral.__init__(self)
        self.regime = 'RSI'
        self.code_regime = [7]
        self.param_indep = 'indep.rsi'

    def get_trimesters_wages(self, workstate, sali, info_ind, to_check=False):
        trimesters = dict()
        wages = dict()
        work = workstate.selected_dates(first=first_year_indep)
        sal = sali.selected_dates(first=first_year_indep)
        nb_trim_cot = self.trim_cot_by_year(work, sal)
        trimesters['cot_RSI']  = nb_trim_cot
        nb_trim_ass = self.trim_ass_by_year(work, nb_trim_cot)
        trimesters['ass_RSI'] = nb_trim_ass
        nb_trim_cot.add(nb_trim_ass)
        trim_by_year = workstate.translate_frequency('year')
        return trimesters, wages
    
    def calculate_salref(self, workstate, sali, regime):
        ''' RAM : Calcul du revenu annuel moyen de référence : 
        notamment application du plafonnement à un PSS'''
        yearsim = self.yearsim
        P = reduce(getattr, self.param_indep.split('.'), self.P)
        nb_best_years_to_take = P.nb_ram
        if compare_destinie == True:
            P = reduce(getattr, self.param_name.split('.'), self.P)
            nb_best_years_to_take = P.nb_sam
        first_year_sal = min(sali.dates) // 100
        plafond = build_long_values(param_long=self.P_longit.common.plaf_ss, first_year=first_year_sal, last_year=yearsim)
        revalo = build_long_values(param_long=self.P_longit.prive.RG.revalo, first_year=first_year_sal, last_year=yearsim)
        
        for i in range(1, len(revalo)) :
            revalo[:i] *= revalo[i]
            
        sal_regime = sali.copy()
        sal_regime.array = sal_regime.array*workstate.isin(self.code_regime).array
        sal_regime.translate_frequency(output_frequency='year', inplace=True,  method='sum')
        print_multi_info_numpy([workstate, sali, sal_regime], 186, self.index)
        years_sali = (sal_regime.array != 0).sum(1)
        nb_best_years_to_take = array(nb_best_years_to_take)
        nb_best_years_to_take[years_sali < nb_best_years_to_take] = years_sali[years_sali < nb_best_years_to_take]    

        if plafond is not None:
            assert sal_regime.array.shape[1] == len(plafond)
            sal_regime.array = minimum(sal_regime.array, plafond) 
        if revalo is not None:
            assert sal_regime.array.shape[1] == len(revalo)
            sal_regime.array = multiply(sal_regime.array,revalo)
        salref = sal_regime.best_dates_mean(nb_best_years_to_take)
        return salref.round(2)

        
            