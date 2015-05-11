# -*- coding:utf-8 -*-
from numpy import isnan, divide, minimum, multiply, zeros


from til_pension.pension_data import PensionData
from til_pension.regime import compare_destinie
from til_pension.regime_prive import RegimePrive
from til_pension.trimesters_functions import trimesters_after_event, imput_sali_avpf, trim_mda


code_avpf = 8
code_chomage = 2
code_preretraite = 9


class RegimeGeneral(RegimePrive):

    def __init__(self):
        RegimePrive.__init__(self)
        self.name = 'RG'
        self.code_regime = [3, 4]
        self.param_name_bis = 'prive.RG'

    def trim_ass_by_year(self, data):
        if compare_destinie:
            return (data.workstate.isin([code_chomage, code_preretraite]))*4
        return trimesters_after_event(data, self.code_regime, code_chomage)

    def data_avpf(self, data):
        # TODO: move to an other place in set_config or in PensionData
        data_avpf = PensionData(data.workstate, data.sali, data.info_ind)
        data_avpf.sali = imput_sali_avpf(data_avpf, code_avpf, self.P_longit)
        if compare_destinie:
            smic_long = self.P_longit.common.smic_proj
            year_avpf = (data_avpf.workstate != 0)
            data_avpf.sali = multiply(year_avpf, smic_long)
        return data_avpf

    def sal_avpf(self, data_avpf):
        select = data_avpf.workstate.isin(code_avpf)
        sal_avpf = data_avpf.sali*select
        sal_avpf[isnan(sal_avpf)] = 0
        return sal_avpf

    def trim_avpf_by_year(self, data_avpf, sal_avpf):
        P_long = reduce(getattr, self.param_name.split('.'), self.P_longit)
        salref = P_long.salref
        plafond = 4  # nombre de trimestres dans l'année
        ratio = divide(sal_avpf, salref).astype(int)
        return minimum(ratio, plafond)

    def sal_FP_to_RG(self, regime='FP'):
        pass

    def trim_FP_to_RG(self, regime='FP'):
        pass

    def trimesters(self, trim_cot_by_year, trim_avpf_by_year, trim_ass_by_year,
                   trim_FP_to_RG):
        # TODO: est-ce qu'on ne devrait pas vérifier qu'on n'a pas plus de
        #  qutre trimestre dans l'année ?
        return trim_cot_by_year + trim_avpf_by_year + \
            trim_ass_by_year + trim_FP_to_RG

    def wages(self, sal_cot, sal_avpf, sal_FP_to_RG):
        return sal_cot + sal_avpf + sal_FP_to_RG

    def sal_regime(self, sal_cot, sal_avpf, sal_FP_to_RG):
        return sal_cot + sal_avpf + sal_FP_to_RG

    def trim_maj_mda_ini(self, data, trim_cot_by_year, trim_ass_by_year):
        P_mda = self.P.prive.RG.mda
        info_ind = data.info_ind
        trims = trim_cot_by_year.sum(axis=1) + trim_ass_by_year.sum(axis=1)
        return trim_mda(info_ind, self.name, P_mda)*(trims > 0)

    def trim_maj_mda_RG(self, trim_maj_mda):
        return trim_maj_mda

    def trim_maj_mda(self, trim_maj_mda_ini, nb_trimesters):
        ''' La Mda (attribuée par tous les régimes de base), ne peut être
        accordé par plus d'un régime.
        Régle d'attribution : a cotisé au régime + si polypensionnés
        -> ordre d'attribution : RG, RSI, FP
        Rq : Pas beau mais temporaire, pour comparaison Destinie'''
        return trim_maj_mda_ini*(nb_trimesters > 0)


class RegimeSocialIndependants(RegimePrive):

    def __init__(self):
        RegimePrive.__init__(self)
        self.name = 'RSI'
        self.code_regime = [7]
        self.param_name_bis = 'indep.rsi'


#     #TODO : pour l'instant tous les trimestres assimilés sont imputés au RG
#     def trim_ass_by_year(self, data):
#         return trim_ass_by_year(data, self.code_regime, compare_destinie)

    def trimesters(self, trim_cot_by_year):
        return trim_cot_by_year

    def sal_regime(self, sal_cot):
        return sal_cot

    def trim_maj_mda_ini(self, data, trim_cot_by_year):
        P_mda = self.P.prive.RG.mda
        info_ind = data.info_ind
        trims = trim_cot_by_year.sum(axis=1)
        return trim_mda(info_ind, self.name, P_mda)*(trims > 0)

    def trim_maj_mda_RSI(self, trim_maj_mda):  #
        return trim_maj_mda

    def trim_maj_mda_RG(self, regime='RG'):
        pass

    def trim_maj_mda(self, trim_maj_mda_ini, nb_trimesters, trim_maj_mda_RG):
        ''' La Mda (attribuée par tous les régimes de base), ne peut être
        accordé par plus d'un régime.
        Régle d'attribution : a cotisé au régime + si polypensionnés
        -> ordre d'attribution : RG, RSI, FP
        Rq : Pas beau mais temporaire, pour comparaison Destinie'''
        if sum(trim_maj_mda_RG) > 0:
            return 0*trim_maj_mda_RG
        return trim_maj_mda_ini*(nb_trimesters > 0)

    def cotisations(self, data):
        ''' Calcul des cotisations passées par année'''
        sali = data.sali*data.workstate.isin(self.code_regime).astype(int)
        taux = self.P_cot.indep.cot_arti
        assert len(taux) == sali.shape[1]
        cot_by_year = zeros(sali.shape)
        for ix_year in range(sali.shape[1]):
            cot_by_year[:,ix_year] = taux[ix_year]*sali[:,ix_year]
        return {'tot': cot_by_year}
