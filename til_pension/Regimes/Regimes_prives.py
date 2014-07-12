# -*- coding:utf-8 -*-
import math
from datetime import datetime


from til_pension.pension_data import PensionData

from til_pension.regime import compare_destinie
from til_pension.regime_prive import RegimePrive
from til_pension.trimesters_functions import trim_ass_by_year, validation_trimestre, trim_mda, imput_sali_avpf

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