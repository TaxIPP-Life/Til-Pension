# -*- coding:utf-8 -*-
import os

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0,parentdir) 

from numpy import minimum
from regime import RegimeComplementaires, compare_destinie


class AGIRC(RegimeComplementaires):
    ''' L'Association générale des institutions de retraite des cadres gère le régime de retraite des cadres du secteur privé 
    de l’industrie, du commerce, des services et de l’agriculture. '''
    
    def __init__(self):
        RegimeComplementaires.__init__(self)
        self.name = 'agirc'
        self.code_regime = [4]
        self.param_name = 'prive.complementaire.agirc'
        self.regime_base = 'RG'
        self.code_cadre = 4
        
    def sali_for_regime(self, data, trim_wages=None):
        workstate = data.workstate
        sali = data.sali
        return sali.array*(workstate.isin(self.code_regime).array)
        
        

class ARRCO(RegimeComplementaires):
    ''' L'association pour le régime de retraite complémentaire des salariés gère le régime de retraite complémentaire de l’ensemble 
    des salariés du secteur privé de l’industrie, du commerce, des services et de l’agriculture, cadres compris. '''
    def __init__(self):
        RegimeComplementaires.__init__(self)
        self.name = 'arrco'
        self.param_name = 'prive.complementaire.arrco'
        self.regime_base = 'RG'
        self.code_regime = [3,4]
        self.code_noncadre = 3
        self.code_cadre = 4
        
    def sali_for_regime(self, data, trim_wages):
        '''plafonne le salaire des cadres à 1 pss pour qu'il ne pait que la première tranche '''
        workstate = data.workstate
        sal = data.sali.array.copy()
        plaf_ss = self.P_longit.common.plaf_ss
        nb_pss = 1 # TODO: Should be a parameter
        cadre_selection = (workstate.array == self.code_cadre)
        plaf_sal = minimum(sal, nb_pss*plaf_ss)
        noncadre_selection = (workstate.array == self.code_noncadre)
        if compare_destinie:
            # Dans Destinie, les FP reversés au RG sont considérés comme cotisants non-cadre 
            FP_selection = (trim_wages['trimesters']['cot_FP'].array != 0)*sal
            noncadre_selection += FP_selection
        return sal*noncadre_selection + plaf_sal*cadre_selection
        