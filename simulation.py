# -*- coding: utf-8 -*-

from pandas import DataFrame
from pension_functions import select_regime_base, sum_by_regime, update_all_regime
import cProfile



class PensionSimulation(object):
    ''' class qui permet de simuler un système de retraite :
            a besoin d'une data et d'une legislation
          La méthode evaluate renvoie un vecteur qui est le montant de pension calculé
    '''
        
    def __init__(self, data, legislation):
        self.yearsim = None
        self.data = data
        #TODO: base_to_complementaire n'est pas vraiment de la législation
        self.legislation = legislation

    def evaluate(self, time_step='year', to_check=False):
        if self.legislation.param is None:
            raise Exception("you should give parameter to PensionData before to evaluate")
        dict_to_check = dict()
        P = self.legislation.param
        P_longit = self.legislation.param_long
        dates_start = self.legislation.dates_start
        yearleg = self.legislation.date.year
        #TODO: remove yearleg
        config = {'dateleg' : yearleg, 'P': P, 'P_longit': P_longit, 'datesleg_start': dates_start,
                  'time_step': time_step}
        
        data = self.data
        regimes = self.legislation.regimes
        base_regimes = regimes['bases']
        complementaire_regimes = regimes['complementaires']
        base_to_complementaire = regimes['base_to_complementaire']
        ### get trimesters (only TimeArray with trim by year), wages (only TimeArray with wage by year) and trim_maj (only vector of majoration): 
        trimesters_wages = dict()
        to_other = dict()
        for reg in base_regimes:
            reg.set_config(**config)
            trimesters_wages_regime, to_other_regime = reg.get_trimesters_wages(data)
            trimesters_wages[reg.name] = trimesters_wages_regime
            to_other.update(to_other_regime)
            
        trimesters_wages = sum_by_regime(trimesters_wages, to_other)
        trimesters_wages = update_all_regime(trimesters_wages, dict_to_check)
        
        pension = None
        for reg in base_regimes:
            reg.set_config(**config)
            pension_reg = reg.calculate_pension(data, trimesters_wages[reg.name], trimesters_wages['all_regime'], dict_to_check)
            if pension is None:
                pension = pension_reg
            else: 
                pension = pension + pension_reg
            if to_check == True:
                dict_to_check['pension_' + reg.name] = pension_reg
    
        for reg in complementaire_regimes:
            reg.set_config(**config)
            regime_base = select_regime_base(trimesters_wages, reg.name, base_to_complementaire)
            pension_reg = reg.calculate_pension(data, regime_base['trimesters'], dict_to_check)
            pension = pension + pension_reg
            if to_check == True:
                dict_to_check['pension_' + reg.name] = pension_reg

        if to_check == True:
            #pd.DataFrame(to_check).to_csv('resultat2004.csv')
            return DataFrame(dict_to_check)
        else:
            return pension # TODO: define the output
        
        
    def profile_evaluate(self, time_step='year', to_check=False):
        prof = cProfile.Profile()
        result = prof.runcall(self.evaluate, *(time_step, to_check))
        prof.dump_stats("profile_pension" + str(self.yearsim))
        return result
        
