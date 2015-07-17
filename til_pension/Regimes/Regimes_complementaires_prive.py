# -*- coding:utf-8 -*-

from numpy import minimum, zeros, maximum
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
        return sali * (workstate.isin(self.code_regime))

    def minimum_points(self, nombre_points):
        ''' Application de la garantie minimum de points '''
        P = reduce(getattr, self.param_name.split('.'), self.P)
        gmp = P.gmp
        nb_points_ini = nombre_points.sum(axis=1)
        nb_points_gmp = maximum(nombre_points, gmp) * (nombre_points > 0)
        return maximum(nb_points_gmp.sum(axis=1) - nb_points_ini, 0)

    def cotisations(self, data):
        ''' Détermine les cotisations payées au cours de la carrière : même fonction que dans régime mais cet en plus'''
        sali = data.sali * data.workstate.isin(self.code_regime).astype(int)
        Pcot_regime = reduce(getattr, self.param_name.split('.'), self.P_cot)
        # getattr(self.P_longit.prive.complementaire,  self.name)
        taux_pat = Pcot_regime.cot_pat
        taux_sal = Pcot_regime.cot_sal
        assert len(taux_pat) == sali.shape[1] == len(taux_sal)
        cot_sal_by_year = zeros(sali.shape)
        cot_pat_by_year = zeros(sali.shape)
        for ix_year in range(sali.shape[1]):
            cot_sal_by_year[:, ix_year] = taux_sal[ix_year].calc(sali[:, ix_year])
            cot_pat_by_year[:, ix_year] = taux_pat[ix_year].calc(sali[:, ix_year])

        cet_pat = Pcot_regime.cet_pat
        cet_sal = Pcot_regime.cet_sal
        assert len(cet_pat) == sali.shape[1] == len(cet_sal)
        for ix_year in range(sali.shape[1]):
            cot_sal_by_year[:, ix_year] += cet_sal[ix_year] * sali[:, ix_year]
            cot_pat_by_year[:, ix_year] += cet_pat[ix_year] * sali[:, ix_year]
        return {'sal': cot_sal_by_year, 'pat': cot_pat_by_year}


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
        plaf_sal = minimum(sal, nb_pss * plaf_ss)
        noncadre_selection = (workstate == self.code_noncadre)
        if compare_destinie:
            # Dans Destinie, les FP reversés au RG sont considérés
            # comme cotisants non-cadre
            FP_selection = (trim_FP_to_RG != 0) * sal
            noncadre_selection += FP_selection
        return sal * noncadre_selection + plaf_sal * cadre_selection

    def minimum_points(self, nombre_points):
        return nombre_points.sum(axis=1) * 0
