# -*- coding: utf-8 -*-

import pandas as pd

from til_pension.sandbox.compare.CONFIG_compare import pensipp_comparison_path as pensipp_data_path 
from til_pension.simulation import PensionSimulation
from til_pension.pension_legislation import PensionParam, PensionLegislation
from til_pension.sandbox.compare.load_pensipp import load_pensipp_data
first_year_sal = 1949

def compute_TRI(yearmin, yearmax):
    depart = dict()
    
    # Define dates du taux plein
    already_retired = []
    for yearsim in range(yearmin, yearmax):
        print "Depart", yearsim
        data_bounded = load_pensipp_data(pensipp_data_path, yearsim, first_year_sal, selection_naiss = [1948,1949,1950,1951,1952])
        print("Data loaded")
        param = PensionParam(yearsim, data_bounded)
        legislation = PensionLegislation(param)
        simul_til = PensionSimulation(data_bounded, legislation)
        dates_taux_plein = simul_til.evaluate(output="dates_taux_plein")
        to_select = (dates_taux_plein == (yearsim - 1)*100 + 1) # vont partir en retraite à yearsim (=t) car ont satisfaits les conditions de taux plein à yearsim - 1 (=t-1)
        ident_depart = simul_til.data.info_ind['index'][to_select]
        ident_depart = [ident for ident in ident_depart if ident not in already_retired]
        depart[yearsim] = ident_depart
        already_retired += ident_depart
        print "Nb of retired people for ",yearsim, len(ident_depart) 
        
    all_dates = [str(year*100 + 1) for year in range(first_year_sal, yearmax)]
    regimes = ['FP', 'RG', 'agirc', 'arrco', 'RSI']
    nb_reg = len(regimes)
    ident_index= [ident for ident in already_retired for i in range(nb_reg)]
    reg_index = regimes*len(already_retired)
    #index = pd.MultiIndex.from_arrays([ident_index, reg_index], names=['ident', 'regime'])
    pensions_contributions = pd.DataFrame(0, index = ident_index, columns = ['ident', 'year_dep', 'regime', 'pension'] + all_dates )
    pensions_contributions['ident'] = ident_index
    pensions_contributions['regime'] = reg_index
    
    for yearsim in range(yearmin, yearmax):
        print(yearsim)
        ident_depart = [int(ident) for ident in depart[yearsim]]
        data_bounded = load_pensipp_data(pensipp_data_path, yearsim, first_year_sal, selection_id = ident_depart)
        print("Data loaded")
        param = PensionParam(yearsim, data_bounded)
        legislation = PensionLegislation(param)
        simul_til = PensionSimulation(data_bounded, legislation)
        pensions_year, cotisations_year = simul_til.evaluate(output="pensions and contributions")
        assert len(pensions_year['FP']) ==  len(cotisations_year['FP']['sal']) == len(depart[yearsim])
        dates_yearsim =  [str(year*100 + 1) for year in range(first_year_sal, yearsim)]
        pensions_contributions['year_dep'][pensions_contributions['ident'].isin(ident_depart)] = yearsim
        for reg in pensions_year.keys():
            cond = (pensions_contributions['regime'] == reg) * (pensions_contributions['ident'].isin(ident_depart))
            pensions_contributions.loc[cond, 'pension'] = pensions_year[reg]
            if 'sal' in cotisations_year[reg].keys() and 'pat' in cotisations_year[reg].keys():
                pensions_contributions.loc[cond, dates_yearsim] = cotisations_year[reg]['sal'] + cotisations_year[reg]['pat']
            else:
                pensions_contributions.loc[cond, dates_yearsim] = cotisations_year[reg]['tot']
                
    pensions_contrib = pensions_contributions[~(pensions_contributions['pension'] == 0)]
    return pensions_contrib
        
if __name__ == '__main__':
    '''# Exemple :
    already_retired = [1,55,7]
    regimes = ['RG', 'FP']
    nb_reg = len(regimes)
    ident_index= [ident for ident in already_retired for i in range(nb_reg)]
    print ident_index
    reg_index = regimes*len(already_retired)
    all_dates = ['194801','194901']
    pensions_contributions = pd.DataFrame(0, index = ident_index, columns = ['ident', 'year_dep', 'regime', 'pension'] + all_dates)
    pensions_contributions['ident'] = ident_index
    pensions_contributions['regime'] = reg_index
    print pensions_contributions.to_string()
    ident_depart = [1,55]
    reg = 'FP'
    pensions_FP =[10,22]
    pensions_contributions['year_dep'][pensions_contributions['ident'].isin(ident_depart)] = 2004
    print pensions_contributions.to_string()
    cond = (pensions_contributions['regime'] == reg) * (pensions_contributions['ident'].isin(ident_depart))
    print cond
    from numpy import array
    cot_FP = pd.DataFrame({'194801':[1,2],'194901':[3,4]}, index = ident_depart)
    print cot_FP.to_string()
    cot_FP = array(cot_FP)
    pensions_contributions.loc[cond, 'pension']= pensions_FP
    pensions_contributions.loc[cond,all_dates]= cot_FP
    print pensions_contributions.loc[cond,all_dates]
    print pensions_contributions.to_string()
    '''
    pension_contrib = compute_TRI(2009,2019)
