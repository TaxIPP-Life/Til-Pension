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
        sali = data.sali.copy()
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
        sali = data.sali.copy() * data.workstate.isin(self.code_regime).astype(int)
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

    def cotisations_moyennes(self, data):
        ''' Détermine les cotisations payées au cours de la carrière quand les taux moyens sont appliqués'''
        sali = data.sali.copy() * data.workstate.isin(self.code_regime).astype(int)
        Pcot_regime = reduce(getattr, self.param_name.split('.'), self.P_cot)
        # getattr(self.P_longit.prive.complementaire,  self.name)
        taux_contractuel_moy = Pcot_regime.taux_contractuel_moy
        taux_appel = Pcot_regime.taux_appel
        assert len(taux_contractuel_moy) == sali.shape[1] == len(taux_appel)
        cot_moy_by_year = zeros(sali.shape)
        for ix_year in range(sali.shape[1]):
            cot_moy_by_year[:, ix_year] = taux_contractuel_moy[ix_year].calc(sali[:, ix_year]) * taux_appel[ix_year]
        cet_pat = Pcot_regime.cet_pat
        cet_sal = Pcot_regime.cet_sal
        assert len(cet_pat) == sali.shape[1] == len(cet_sal)
        for ix_year in range(sali.shape[1]):
            cot_moy_by_year[:, ix_year] += cet_sal[ix_year] * sali[:, ix_year] + cet_pat[ix_year] * sali[:, ix_year]
        return cot_moy_by_year

    def pension(self, data, coefficient_age, pension_brute,
                majoration_pension, trim_decote):
        ''' le régime agirc tient compte du coefficient de
        minoration dans le calcul des majorations pour enfants '''
        pension = coefficient_age * (pension_brute + majoration_pension)
        return pension

    def nb_points(self, data, nb_points_cot):
        return nb_points_cot


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

    def nb_points(self, data, nb_points_cot):
        nb_points_other = 0
        # Points d'ancienneté dans le Régime qui sont déterminées par une source externe (EIR)
        if 'nb_point_anc_arrco' in data.info_ind.columns:
            nb_points_other = data.info_ind['nb_point_anc_arrco']
        if 'nb_point_grat_arrco' in data.info_ind.columns:
            nb_points_other += data.info_ind['nb_point_grat_arrco']
        return nb_points_cot

    def pension(self, data, coefficient_age, pension_brute,
                majoration_pension, trim_decote):
        ''' le régime Arrco ne tient pas compte du coefficient de
        minoration dans le calcul des majorations pour enfants '''
        pension = coefficient_age * pension_brute + majoration_pension
        return pension

    def cotisations_moyennes(self, sali_for_regime):
        ''' Détermine les cotisations payées au cours de la carrière quand les taux moyens sont appliqués'''
        sali = sali_for_regime.copy()
        Pcot_regime = reduce(getattr, self.param_name.split('.'), self.P_cot)
        # getattr(self.P_longit.prive.complementaire,  self.name)
        taux_contractuel_moy = Pcot_regime.taux_contractuel_moy
        taux_appel = Pcot_regime.taux_appel
        assert len(taux_contractuel_moy) == sali.shape[1] == len(taux_appel)
        cot_moy_by_year = zeros(sali.shape)
        for ix_year in range(sali.shape[1]):
            cot_moy_by_year[:, ix_year] = taux_contractuel_moy[ix_year].calc(sali[:, ix_year]) * taux_appel[ix_year]
        return cot_moy_by_year
