# -*- coding:utf-8 -*-
import math
from datetime import datetime


from til_pension.pension_data import PensionData

from til_pension.regime import compare_destinie
from til_pension.regime_prive import RegimePrive
from til_pension.trimesters_functions import trim_ass_by_year, validation_trimestre, imput_sali_avpf

code_avpf = 8


class RegimeGeneral(RegimePrive):

    def __init__(self):
        RegimePrive.__init__(self)
        self.name = 'RG'
        self.code_regime = [3,4]
        self.param_name_bis = 'prive.RG'

    def get_trimesters_wages(self, data):
        trimesters = dict()
        wages = dict()
        trim_maj = dict()
        to_other = dict()

        info_ind = data.info_ind

        P_long = reduce(getattr, self.param_name.split('.'), self.P_longit)
        salref = P_long.salref
        trimesters['cot'], wages['cot'] = validation_trimestre(data, self.code_regime, salref, name='cot')
        trimesters['ass'], _ = trim_ass_by_year(data, self.code_regime, compare_destinie)

        #TODO: imput_sali_avpf should be much more upper in the code
        data_avpf = PensionData(data.workstate, data.sali, data.info_ind)
        data_avpf.sali = imput_sali_avpf(data_avpf, code_avpf, self.P_longit, compare_destinie)

        # Allocation vieillesse des parents au foyer : nombre de trimestres attribués
        trimesters['avpf'], wages['avpf'] = validation_trimestre(data_avpf, code_avpf, salref, name='avpf')
        P_mda = self.P.prive.RG.mda
        trim_maj['DA'] = trim_mda(info_ind, self.name, P_mda)*(trimesters['cot'].sum(axis=1)+ trimesters['ass'].sum(axis=1)>0)
        output = {'trimesters': trimesters, 'wages': wages, 'maj': trim_maj}
        #print_multi_info_numpy([data.workstate, data.sali, trimesters['cot'], wages['cot'], trimesters['avpf'], wages['avpf'], trimesters['ass']], 1882, data.info_ind.index)
        return output, to_other
  
    
    def trim_ass_by_year(self, data):
        return trim_ass_by_year(data, self.code_regime, compare_destinie)

    def trim_cot_by_year_avpf(self, data):
        P_long = reduce(getattr, self.param_name.split('.'), self.P_longit)
        salref = P_long.salref
        data_avpf = PensionData(data.workstate, data.sali, data.info_ind)
        data_avpf.sali = imput_sali_avpf(data_avpf, code_avpf, self.P_longit, compare_destinie)
        trim_avpf, sal_avpf = validation_trimestre(data_avpf, code_avpf, salref, name='avpf')
        return trim_avpf, sal_avpf  
    
    def FP_to_RG(self, regime='FP'):
        pass
    
    def trimesters(self, trim_cot_by_year_regime, trim_cot_by_year_avpf, trim_ass_by_year, FP_to_RG):
        # TODO: est-ce qu'on ne devrait pas vérifier qu'on n'a pas plus de qutre trimestre dans l'année ? 
        return trim_cot_by_year_regime[0] + trim_cot_by_year_avpf[0] + trim_ass_by_year + FP_to_RG[0]
    
    def trim_maj_mda_RG(self,trim_maj_mda_ini, nb_trimesters):  #
        return trim_maj_mda_ini*(nb_trimesters > 0)

    def wages(self, trim_cot_by_year_regime, trim_cot_by_year_avpf, FP_to_RG):
        return trim_cot_by_year_regime[1] + trim_cot_by_year_avpf[1] + FP_to_RG[1]

    def trim_maj_mda(self, trim_maj_mda_RG):
        ''' La Mda (attribuée par tous les régimes de base), ne peut être accordé par plus d'un régime.
        Régle d'attribution : a cotisé au régime + si polypensionnés -> ordre d'attribution : RG, RSI, FP
        Rq : Pas beau mais temporaire, pour comparaison Destinie'''
        return trim_maj_mda_RG
    
    def trim_maj(self, trim_maj_mda):
        return trim_maj_mda

class RegimeSocialIndependants(RegimePrive):

    def __init__(self):
        RegimePrive.__init__(self)
        self.name = 'RSI'
        self.code_regime = [7]
        self.param_name_bis = 'indep.rsi'

    def get_trimesters_wages(self, data):
        trimesters = dict()
        wages = dict()
        trim_maj = dict()
        to_other = dict()

        P_long = reduce(getattr, self.param_name.split('.'), self.P_longit)
        salref = P_long.salref
        trimesters['cot'], wages['cot'] = validation_trimestre(data, self.code_regime, salref, name='cot')

        #TODO : pour l'instant tous les trimestres assimilés sont imputés au RG
        #nb_trim_ass, _ = trim_ass_by_year(reduce_data, self.code_regime, compare_destinie)
        #trimesters['ass'] = nb_trim_ass

        P_mda = self.P.prive.RG.mda
        trim_maj['DA'] = trim_mda(data.info_ind, self.name, P_mda)*(trimesters['cot'].sum(axis=1)>0)
        output = {'trimesters': trimesters, 'wages': wages, 'maj': trim_maj}
        return output, to_other
       
#     #TODO : pour l'instant tous les trimestres assimilés sont imputés au RG
#     def trim_ass_by_year(self, data):
#         return trim_ass_by_year(data, self.code_regime, compare_destinie)
    
    def trimesters(self, trim_cot_by_year_regime):
        return trim_cot_by_year_regime[0]
    
    def trim_maj_mda_RG(self,trim_maj_mda_ini, nb_trimesters):  #
        return trim_maj_mda_ini*(nb_trimesters > 0)

    def wages(self, trim_cot_by_year_regime):
        return trim_cot_by_year_regime[1]

    def trim_maj_mda(self, trim_maj_mda_RG):
        ''' La Mda (attribuée par tous les régimes de base), ne peut être accordé par plus d'un régime.
        Régle d'attribution : a cotisé au régime + si polypensionnés -> ordre d'attribution : RG, RSI, FP
        Rq : Pas beau mais temporaire, pour comparaison Destinie'''
        return trim_maj_mda_RG
    
    def trim_maj(self, trim_maj_mda):
        return trim_maj_mda