# -*- coding: utf-8 -*-
from numpy import array
from pandas import DataFrame
from pension_functions import sum_by_regime, update_all_regime
from sandbox.compare.print_decorator import PrintDecorator
from add_print import AddPrint

import cProfile

class PensionSimulation(object):
    ''' class qui permet de simuler un système de retraite :
            a besoin d'une data et d'une legislation
          La méthode evaluate renvoie un vecteur qui est le montant de pension calculé
    '''
        
    def __init__(self, data, legislation):
        self.data = data
        self.legislation = legislation
        
        #adapt longitudinal parameter to data
        duration_sim = data.last_date.year - data.first_date.year
        self.legislation.param_long = legislation.long_param_builder(duration_sim)
        self.legislation.param = legislation.param.param
        
        self.trimesters_wages = dict()
        self.pensions = dict()
    
    @staticmethod
    def intermediate_print():
#         index = self.data.info_ind.index
#         tout = range(len(index))
        return PrintDecorator(func_to_print, selection=[4,8])
        
    def evaluate(self, time_step='year', to_check=False, output='pension'):
        if self.legislation.param is None:
            raise Exception("you should give parameter to PensionData before to evaluate")
        
        look_into = {'FP' : {'calculate_coeff_proratisation': True}} 
        
        dict_to_check = dict()
        P = self.legislation.param
        P_longit = self.legislation.param_long
        yearleg = self.legislation.date.year
        #TODO: remove yearleg
        config = {'dateleg' : yearleg, 'P': P, 'P_longit': P_longit, 'time_step': time_step}
        
        data = self.data
        regimes = self.legislation.regimes
        base_regimes = regimes['bases']
        complementaire_regimes = regimes['complementaires']
        ### get trimesters (only TimeArray with trim by year), wages (only TimeArray with wage by year) and trim_maj (only vector of majoration): 
        trimesters_wages = self.trimesters_wages
        
        # 1 - Détermination des trimestres et des salaires cotisés, assimilés, avpf et majorés par régime
        if len(trimesters_wages) == 0:
            to_other = dict()
            for reg in base_regimes:
                reg.set_config(**config)
                if reg.name in look_into:
                    methods_to_look = look_into[reg.name]
                    for method in methods_to_look:
                        method_init = reg.__getattribute__(method)
                        new_method = AddPrint(None)(method_init)
                        reg.__setattr__(method, new_method)
                trimesters_wages_regime, to_other_regime = reg.get_trimesters_wages(data)
                trimesters_wages[reg.name] = trimesters_wages_regime
                to_other.update(to_other_regime)
                
            trimesters_wages = sum_by_regime(trimesters_wages, to_other)
            trimesters_wages = update_all_regime(trimesters_wages, dict_to_check)
            self.trimesters_wages = trimesters_wages
        if output == 'trimesters_wages':
            return self.trimesters_wages
        
        # 2 - Calcul des pensions brutes par régime (de base et complémentaire)
        pensions = self.pensions
        trim_decote = dict()
        if len(pensions) == 0:
            for reg in base_regimes:
                reg.set_config(**config)
                pension_reg, decote_reg = reg.calculate_pension(data, trimesters_wages[reg.name], trimesters_wages['all_regime'], 
                                                    dict_to_check)
                trim_decote[reg.name] = decote_reg
                pensions[reg.name] = pension_reg
        
            for reg in complementaire_regimes:
                reg.set_config(**config)
                regime_base = reg.regime_base
                pension_reg = reg.calculate_pension(data, trimesters_wages[regime_base], trimesters_wages['all_regime'], trim_decote[regime_base],
                                                    dict_to_check)
                pensions[reg.name] = pension_reg
                
            pensions['tot'] = sum(pensions.values())
            self.pensions = pensions
            
        # 3 - Application des minimums de pensions et majorations postérieures
        '''
        pension = 0
        pensions = dict()
        for reg in base_regimes:
            pension_brut_reg = pensions_brut[reg.name]
            pension_reg = reg.bonif_pension(data, trimesters_wages[reg.name], trimesters_wages['all_regime'], 
                                            pension_brut_reg, pension)
            pension += pension_reg
            pensions[reg.name] = pension_reg
        '''
            
        if to_check == True:
            output = dict_to_check
            for key, value in self.pensions.iteritems():
                output['pension_' + key] = value
            return DataFrame(output, index = self.data.info_ind.index)
        else:
            return self.pensions['tot'] # TODO: define the output : for the moment a dic with pensions by regime

    
    def profile_evaluate(self, time_step='year', to_check=False, output='pension'):
        prof = cProfile.Profile()
        result = prof.runcall(self.evaluate, *(time_step, to_check, output))
        #TODO: add a suffix, like yearleg : was + str(self.yearsim)
        prof.dump_stats("profile_pension" + str(self.legislation.date.liam))
        return result
        
    
    
yearsim = 2004
selection_id =  [186,7338]
func_to_print = {'calculate_coeff_proratisation': True}

