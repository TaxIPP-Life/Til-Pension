# -*- coding: utf-8 -*-

from CONFIG_compare import pensipp_comparison_path
from simulation import PensionSimulation
from pension_legislation import PensionParam, PensionLegislation
from load_pensipp import load_pensipp_data

def print_details(data, yearsim, loggerlevel):
    param = PensionParam(yearsim, data)
    legislation = PensionLegislation(param)
    simul_til = PensionSimulation(data, legislation)
    simul_til.profile_evaluate(to_check=False, logger=loggerlevel)
    
if __name__ == '__main__':    

    var_to_check_montant = [ u'pension_RG', u'salref_RG', u'DA_RG', u'DA_RSI', 
                            u'nb_points_arrco', u'nb_points_agirc', u'pension_arrco', u'pension_agirc',
                            u'DA_FP', u'pension_FP',
                            u'n_trim_RG', 'N_CP_RG', 'n_trim_FP'
                            ] 
    var_to_check_taux = [u'taux_RG', u'surcote_RG', u'decote_RG', u'CP_RG',
                         u'taux_FP'
                          ]
    threshold = {'montant' : 1, 'taux' : 0.05}
    import logging
    import sys
    yearsim = 2004
    logging.basicConfig(format='%(message)s', level = logging.INFO, stream = sys.stdout) #%(funcName)s(%(levelname)s): 
    data_to_print = load_pensipp_data(pensipp_comparison_path,
                                     yearsim, 
                                     first_year_sal=1949, 
                                     selection_id = [7338])
    
    loggerlevel = {'evaluate': 'info', 'decote':'error', 'surcote': 'error'}
    print_details(data_to_print, 2004, loggerlevel)