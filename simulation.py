# -*- coding: utf-8 -*-

import datetime as dt
import os
from pandas import DataFrame
from Regimes.Fonction_publique import FonctionPublique
from Regimes.Regimes_complementaires_prive import AGIRC, ARRCO
from Regimes.Regimes_prives import RegimeGeneral, RegimeSocialIndependants

from utils_pension import load_param, build_long_values, scales_long_baremes
from pension_functions import select_regime_base, sum_by_regime, update_all_regime
first_year_sal = 1949 
first_year_avpf = 1972
import cProfile

base_regimes = ['RegimeGeneral', 'FonctionPublique', 'RegimeSocialIndependants']
complementaire_regimes = ['ARRCO', 'AGIRC']
base_to_complementaire = {'RegimeGeneral': ['arrco', 'agirc'], 'FonctionPublique': []}

def til_pension(sali, workstate, info_ind, time_step='year', yearsim=2009, yearleg=None, example=False):
    command = """run_pension(sali, workstate, info_ind, time_step, yearsim, yearleg, example)"""
    cProfile.runctx( command, globals(), locals(), filename="profile_pension" + str(yearsim))

class PensionSimulation(object):

    def __init__(self, data):
        self.yearsim = None
        self.data = data
        #TODO: base_to_complementaire n'est pas vraiment de la législation
        self.legislation = dict(base_regimes = ['RegimeGeneral', 'FonctionPublique', 'RegimeSocialIndependants'],
                                complementaire_regimes = ['ARRCO', 'AGIRC'],
                                base_to_complementaire = {'RegimeGeneral': ['arrco', 'agirc'], 'FonctionPublique': []}
                                )
        self.param = None
        
#     def load_data_from_pieces(self, workstate, sali, info_ind):
#         ''' generate data
#             table are taken only since first_year_sal
#             and until yearsim if yearsim is not None
#             - workstate, sali: longitudinal array, or pandas DataFrame or TimeArray
#             - info_ind : pandas DataFrame
#             - yearsim: int
#         '''
#         if max(info_ind.loc[:,'sexe']) == 2:
#             info_ind.loc[:,'sexe'] = info_ind.loc[:,'sexe'].replace(1,0)
#             info_ind.loc[:,'sexe'] = info_ind.loc[:,'sexe'].replace(2,1)
#         yearsim = sali.dates[-1]
#         info_ind.loc[:,'naiss'] = build_naiss(info_ind.loc[:,'agem'], dt.date(yearsim,1,1))
#         data = PensionData.from_arrays(workstate, sali, info_ind)
#         data.selected_dates(first=first_year_sal, inplace=True)
#         self.data = data
        
    def long_param_builder(self, P_longit, yearleg): 
        ''' Cette fonction permet de traduire les paramètres longitudinaux en vecteur numpy 
        comportant une valeur par année comprise entre first_year_sim et last_year_sim '''
        first_year_sim = self.data.first_date.year + (self.data.last_date.year + 1 - yearleg) 
        last_year_sim = yearleg
        # TODO: trouver une méthode plus systématique qui test le 'type' du noeud et construit le long parameter qui va bien
        P_longit.common.plaf_ss = build_long_values(P_longit.common.plaf_ss, 
                                                 first=first_year_sim, last=last_year_sim) 
        P_longit.prive.RG.revalo = build_long_values(P_longit.prive.RG.revalo,
                                                  first=first_year_sim, last=last_year_sim) 
        def _complementaire(regime):
            P = getattr(P_longit.prive.complementaire, regime)
            salref_long = P.sal_ref
            salref_long = build_long_values(salref_long,
                                        first=first_year_sim, last=last_year_sim) 
            taux_cot_long = P.taux_cot_moy
            taux_cot_long = build_long_values(taux_cot_long,
                                               first=first_year_sim, last=last_year_sim)
            taux_cot_long = scales_long_baremes(baremes=taux_cot_long, scales=P_longit.common.plaf_ss)
            return salref_long, taux_cot_long

        P_longit.prive.complementaire.arrco.sal_ref, P_longit.prive.complementaire.arrco.taux_cot_moy  = _complementaire('arrco')
        P_longit.prive.complementaire.agirc.sal_ref, P_longit.prive.complementaire.agirc.taux_cot_moy  = _complementaire('agirc')
        P_longit.common.smic_proj = build_long_values(param_long=P_longit.common.smic_proj,
                                                      first=1972, last=last_year_sim) 
        P_longit.common.avpf = build_long_values(param_long=P_longit.common.avpf, 
                                 first=first_year_avpf, last=last_year_sim)
        return P_longit


    def load_param(self, yearleg):
        ''' should run after having a data'''
        assert self.data is not None
        path_pension = os.path.dirname(os.path.abspath(__file__))
        param_file = path_pension + '\\France\\param.xml'
        date_param = str(yearleg)+ '-01-01'
        date_param = dt.datetime.strptime(date_param ,"%Y-%m-%d").date()
        P, P_longit = load_param(param_file, self.data.info_ind, date_param)
        P_longit = self.long_param_builder(P_longit, yearleg)
        self.param = P, P_longit
        self.yearleg = yearleg
        
    def evaluate(self, time_step='year', to_check=False):
        if self.param is None:
            raise Exception("you should give parameter to PensionData before to evaluate")
        dict_to_check = dict()
        P = self.param[0]
        P_longit = self.param[1]
        #TODO: remove yearleg
        config = {'dateleg' : self.yearleg, 'P': P, 'P_longit': P_longit,
                  'time_step': time_step}
        
        data = self.data
        leg = self.legislation
        base_regimes = leg['base_regimes']
        complementaire_regimes = leg['complementaire_regimes']
        base_to_complementaire = leg['base_to_complementaire']
        ### get trimesters (only TimeArray with trim by year), wages (only TimeArray with wage by year) and trim_maj (only vector of majoration): 
        trimesters_wages = dict()
        to_other = dict()
        for reg_name in base_regimes:
            reg = eval(reg_name + '()')
            reg.set_config(**config)
            trimesters_wages_regime, to_other_regime = reg.get_trimesters_wages(data)
            trimesters_wages[reg_name] = trimesters_wages_regime
            to_other.update(to_other_regime)
            
        trimesters_wages = sum_by_regime(trimesters_wages, to_other)
        trimesters_wages = update_all_regime(trimesters_wages, dict_to_check)
        
        for reg_name in base_regimes:
            reg = eval(reg_name + '()')
            reg.set_config(**config)
            pension_reg = reg.calculate_pension(data, trimesters_wages[reg_name], trimesters_wages['all_regime'], dict_to_check)
            if to_check == True:
                dict_to_check['pension_' + reg.regime] = pension_reg
    
        for reg_name in complementaire_regimes:
            reg = eval(reg_name + '()')
            reg.set_config(**config)
            regime_base = select_regime_base(trimesters_wages, reg.regime, base_to_complementaire)
            pension_reg = reg.calculate_pension(data, regime_base['trimesters'], dict_to_check)
            if to_check == True:
                dict_to_check['pension_' + reg.regime] = pension_reg
    
        if to_check == True:
            #pd.DataFrame(to_check).to_csv('resultat2004.csv')
            return DataFrame(dict_to_check)
        else:
            return pension_reg # TODO: define the output
        
             
    def main(self, yearleg, time_step='year', to_check=False):
        self.load_param(yearleg)
        return self.evaluate(time_step='year', to_check=to_check)

    def profile_main(self, yearleg, time_step='year', to_check=False):
        prof = cProfile.Profile()
        result =prof.runcall( self.main, *(yearleg, time_step, to_check))
        prof.dump_stats("profile_pension" + str(yearleg))
        return result
        
