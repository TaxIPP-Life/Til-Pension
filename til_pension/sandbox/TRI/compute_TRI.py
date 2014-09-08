# -*- coding: utf-8 -*-

import pandas as pd

from til_pension.sandbox.compare.CONFIG_compare import pensipp_comparison_path as pensipp_data_path 
from til_pension.simulation import PensionSimulation
from til_pension.pension_legislation import PensionParam, PensionLegislation
from til_pension.sandbox.compare.load_pensipp import load_pensipp_data
first_year_sal = 1949

def compute_TRI(yearmin, yearmax):
    depart = dict()
    pensions = dict()
    cotisations = dict()
    # Define dates du taux plein

    already_retired = []
    for yearsim in range(yearmin, yearmax):
        print(yearsim)
        data_bounded = load_pensipp_data(pensipp_data_path, yearsim, first_year_sal, behavior_depart = "taux_plein")
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
        
        all_dates = [year*100 + 1 for year in range(first_year_sal, yearmax)]
        pensions_table = pd.DataFrame(0, index = already_retired, columns = ['year_dep', 'RG', 'FP', 'RSI', 'agirc', 'arrco'])
        for reg in ['FP', 'RG', 'agirc', 'arrco', 'RSI']:
            contributions_reg = pd.DataFrame(0, index = already_retired, columns = all_dates)
            
            
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
        dates_yearsim =  [year*100 + 1 for year in range(first_year_sal, yearsim)]
        for reg in pensions_year.keys():
            pensions_table['year_dep'][ident_depart] = yearsim
            pensions_table.ix[ident_depart, reg] = pensions_year[reg]
            if 'sal' in cotisations_year[reg].keys() and 'pat' in cotisations_year[reg].keys():
                contributions_reg.ix[ident_depart, dates_yearsim] = cotisations_year[reg]['sal'] + cotisations_year[reg]['pat']
            else:
                contributions_reg.ix[ident_depart, dates_yearsim] = cotisations_year[reg]['tot']
            #if yearsim == yearmax - 1:
                #contributions_reg.to_csv('test_'+ reg + '.csv')
        #pensions_table.to_csv('test.csv')
if __name__ == '__main__':
    compute_TRI(2004,2006)
  