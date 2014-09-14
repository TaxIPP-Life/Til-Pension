# -*- coding:utf-8 -*-

from numpy import minimum
from til_pension.regime import RegimeComplementaires, compare_destinie


class AGIRC(RegimeComplementaires):
    ''' L'Association générale des institutions de retraite des cadres gère
    le régime de retraite des cadres du secteur privé
    de l’industrie, du commerce, des services et de l’agriculture. '''

    def __init__(self):
        RegimeComplementaires.__init__(self)
        self.name = 'agirc'
        self.code_regime = [4]
        self.param_name = 'prive.complementaire.agirc'
        self.regime_base = 'RG'
        self.code_cadre = 4

    # should be nb_trimesters(self, regime=self.regime_base)
    def nb_trimesters(self, regime='RG'):
        pass

    def trim_decote(self, regime='RG'):
        pass

    def sali_for_regime(self, data):
        workstate = data.workstate
        sali = data.sali
        return sali*(workstate.isin(self.code_regime))


class ARRCO(RegimeComplementaires):
    ''' L'association pour le régime de retraite complémentaire des salariés
    gère le régime de retraite complémentaire de l’ensemble
    des salariés du secteur privé de l’industrie, du commerce, des services
    et de l’agriculture, cadres compris. '''
    def __init__(self):
        RegimeComplementaires.__init__(self)
        self.name = 'arrco'
        self.param_name = 'prive.complementaire.arrco'
        self.regime_base = 'RG'
        self.code_regime = [3, 4]
        self.code_noncadre = 3
        self.code_cadre = 4

    # should be nb_trimesters(self, regime=self.regime_base)
    def nb_trimesters(self, regime='RG'):
        pass

    def trim_decote(self, regime='RG'):
        pass

    def trim_FP_to_RG(self, regime='FP'):
        pass

    def sali_for_regime(self, data, trim_FP_to_RG):
        '''plafonne le salaire des cadres à 1 pss pour qu'il ne pait que
        la première tranche '''
        workstate = data.workstate
        sal = data.sali.copy()
        plaf_ss = self.P_longit.common.plaf_ss
        nb_pss = 1  # TODO: Should be a parameter
        cadre_selection = (workstate == self.code_cadre)
        plaf_sal = minimum(sal, nb_pss*plaf_ss)
        noncadre_selection = (workstate == self.code_noncadre)
        if compare_destinie:
            # Dans Destinie, les FP reversés au RG sont considérés
            # comme cotisants non-cadre
            FP_selection = (trim_FP_to_RG != 0)*sal
            noncadre_selection += FP_selection
        return sal*noncadre_selection + plaf_sal*cadre_selection
