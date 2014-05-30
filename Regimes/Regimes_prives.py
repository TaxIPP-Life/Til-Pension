# -*- coding:utf-8 -*-
import math
from datetime import datetime

import os
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir) 
from time_array import TimeArray

from numpy import array, multiply
from pandas import Series

from regime import compare_destinie
from regime_prive import RegimePrive
from utils_pension import build_long_values, build_salref_bareme
from pension_functions import nb_trim_surcote, unemployment_trimesters, sal_to_trimcot

code_avpf = 8
code_chomage = 2
code_preretraite = 9
first_year_indep = 1972
first_year_avpf = 1972
    
class RegimeGeneral(RegimePrive):
    
    def __init__(self):
        RegimePrive.__init__(self)
        self.regime = 'RG'
        self.code_regime = [3,4]
        self.param_name_bis = 'prive.RG'
     
    def get_trimesters_wages(self, data, to_check=False):
        trimesters = dict()
        wages = dict()
        trim_maj = dict()
        to_other = dict()
        
        workstate = data.workstate
        sali = data.sali
        info_ind = data.info_ind
        
        trim_cot = self.trim_cot_by_year(data)
        trimesters['cot']  = trim_cot
        
        sal_by_year = sali.translate_frequency(output_frequency='year', method='sum')
        wages['cot'] = TimeArray((trim_cot.array > 0)*sal_by_year.array, sal_by_year.dates, name='sal_RG')
        
        trim_ass = self.trim_ass_by_year(workstate, trim_cot)
        trimesters['ass'] = trim_ass
        sal_for_avpf = self.sali_avpf(data) # Allocation vieillesse des parents au foyer : nombre de trimestres attribués 
        
        salref = build_salref_bareme(self.P_longit.common, first_year_avpf, data.datesim.year)
        trim_avpf = sal_to_trimcot(sal_for_avpf, salref, plafond=4)
        trimesters['avpf']  = trim_avpf    
        wages['avpf'] = sal_for_avpf
        
        trim_maj['DA'] = self.trim_mda(info_ind)

        if to_check is not None:
            to_check['DA_RG'] = ((trimesters['cot'] + trimesters['ass'] + trimesters['avpf']).sum(1) 
                                 + trim_maj['DA'])/4
        output = {'trimesters': trimesters, 'wages': wages, 'maj': trim_maj}
        return output, to_other

    def trim_cot_by_year(self, data, table=False):
        ''' Nombre de trimestres côtisés pour le régime général par année 
        ref : code de la sécurité sociale, article R351-9
        '''
        # Selection des salaires à prendre en compte dans le décompte (mois où il y a eu côtisation au régime)
        workstate = data.workstate
        sali = data.sali
        first_year_sal = min(workstate.dates) // 100
        wk_selection = workstate.isin(self.code_regime)
        sal_selection = TimeArray(wk_selection.array*sali.array, sali.dates)
        salref = build_salref_bareme(self.P_longit.common, first_year_sal, data.datesim.year)
        trim_cot_by_year = sal_to_trimcot(sal_selection, salref, plafond=4)
        return trim_cot_by_year
    
    def sali_avpf(self, data):
        ''' Allocation vieillesse des parents au foyer : 
             - selectionne les revenus correspondant au periode d'AVPF
             - imputes des salaires de remplacements (quand non présents)
        '''
        workstate = data.workstate
        sali = data.sali
        avpf_selection = workstate.isin([code_avpf]).selected_dates(first_year_avpf)
        sal_for_avpf = sali.selected_dates(first_year_avpf)
        sal_for_avpf.array = sal_for_avpf.array*avpf_selection.array
        if sal_for_avpf.array.all() == 0:
            # TODO: frquency warning, cette manière de calculer les trimestres avpf ne fonctionne qu'avec des tables annuelles
            avpf = build_long_values(param_long=self.P_longit.common.avpf, first_year=first_year_avpf, last_year=data.datesim.year)
            sal_for_avpf.array = multiply(avpf_selection.array, 12*avpf)
            if compare_destinie == True:
                smic_long = build_long_values(param_long=self.P_longit.common.smic_proj, first_year=first_year_avpf, last_year=data.datesim.year) 
                sal_for_avpf.array = multiply(avpf_selection.array, smic_long)    
        return sal_for_avpf
        
    

class RegimeSocialIndependants(RegimePrive):
    
    def __init__(self):
        RegimePrive.__init__(self)
        self.regime = 'RSI'
        self.code_regime = [7]
        self.param_name_bis = 'indep.rsi'

    def get_trimesters_wages(self, data, to_check=False):
        trimesters = dict()
        wages = dict()
        trim_maj = dict()
        to_other = dict()
        
        workstate = data.workstate
        sali = data.sali
        
        reduce_data = data.selected_dates(first=first_year_indep)
        nb_trim_cot = self.trim_cot_by_year(reduce_data.workstate)
        trimesters['cot']  = nb_trim_cot
        nb_trim_ass = self.trim_ass_by_year(reduce_data.workstate, nb_trim_cot)
        trimesters['ass'] = nb_trim_ass
        wages['regime'] = self.sali_in_regime(sali, workstate)
        trim_maj['DA'] = 0*self.trim_mda(data.info_ind)
        if to_check is not None:
                to_check['DA_RSI'] = (trimesters['cot'].sum(1) + trim_maj['DA'])//4
        output = {'trimesters': trimesters, 'wages': wages, 'maj': trim_maj}
        return output, to_other