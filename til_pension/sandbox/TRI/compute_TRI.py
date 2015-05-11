# -*- coding: utf-8 -*-


import pandas as pd
from numpy import nan, array, around, double
from til_pension.sandbox.compare.CONFIG_compare import pensipp_comparison_path as pensipp_data_path
from til_pension.simulation import PensionSimulation
from til_pension.pension_legislation import PensionParam, PensionLegislation
from til_pension.sandbox.compare.load_pensipp import load_pensipp_data
from math import pow
try:
    from scipy.optimize import fsolve, newton_krylov
except:
    pass
first_year_sal = 1949


def flow(x, pensions_contrib):
        ''' fonction individuelle de calcul de la partie cotisation du TRI '''
        year_naiss = int(str(pensions_contrib['naiss'])[0:4])
        year_dep = int(pensions_contrib['year_dep'])
        year_death = pensions_contrib['death']
        findet = int(pensions_contrib.loc['findet'])
        pension = pensions_contrib['pension']
        dates_contrib = [year * 100 + 1 for year in range(year_naiss + findet, year_dep)]
        nb_contrib = len(dates_contrib)
        nb_pensions = year_death - year_dep + 1
        flow_contrib = [- pensions_contrib.loc[str(year * 100 + 1)] for year in range(year_naiss + findet, year_dep)]
        flow_pensions = [pension] * nb_pensions
        flows = flow_contrib + flow_pensions
        actual = array([pow(x, p) for p in range(0, nb_contrib + nb_pensions)])
        return sum(flows * actual)


def TRI(pensions_contrib, val0 = 1.3):
    sol = fsolve(flow, val0, args=(pensions_contrib),
                 maxfev = 400)
    try:
        rate = [s for s in sol  if s > 1 / 2 and s < 1][0]
    except:
        rate = -1
    if rate > 1:
        rate = -1
    return 1 / rate - 1


def compute_TRI(yearmin, yearmax):
    depart = dict()
    # Define dates du taux plein
    already_retired = []
    for yearsim in range(yearmin, yearmax):
        print "Depart", yearsim
        data_bounded = load_pensipp_data(
            pensipp_data_path, yearsim, first_year_sal, selection_naiss = [1948, 1949, 1950, 1951, 1952])
        print("Data loaded")
        param = PensionParam(yearsim, data_bounded)
        legislation = PensionLegislation(param)
        simul_til = PensionSimulation(data_bounded, legislation)
        regimes = ['RG']  # TODO:, 'agirc', 'arrco', 'FP', 'RSI']
        for regime in regimes:
            dates_taux_plein = simul_til.calculate("pension", regime_name = regime)

        to_select = (dates_taux_plein == (yearsim - 1) * 100 + 1)
        # vont partir en retraite à yearsim (=t) car ont satisfaits les conditions de taux plein à yearsim - 1 (=t-1)
        ident_depart = simul_til.data.info_ind['index'][to_select]
        ident_depart = [ident for ident in ident_depart if ident not in already_retired]
        depart[yearsim] = ident_depart
        already_retired += ident_depart
        print "Nb of retired people for ", yearsim, len(ident_depart)

    all_dates = [str(year * 100 + 1) for year in range(first_year_sal, yearmax)]
    regimes = [ 'RG', 'agirc', 'arrco', 'FP', 'RSI']
    nb_reg = len(regimes)
    ident_index= [ident for ident in already_retired for i in range(nb_reg)]
    reg_index = regimes*len(already_retired)
    #index = pd.MultiIndex.from_arrays([ident_index, reg_index], names=['ident', 'regime'])
    pensions_contrib = pd.DataFrame(0, index = ident_index, columns = ['ident', 'age', 'naiss', 'n_enf', 'findet', 'sexe', 'year_dep', 'regime', 'pension'] + all_dates )
    pensions_contrib['ident'] = ident_index
    pensions_contrib['regime'] = reg_index
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
        for reg in pensions_year.keys():
            cond = (pensions_contrib['regime'] == reg) * (pensions_contrib['ident'].isin(ident_depart))
            pensions_contrib.loc[cond, 'pension'] = pensions_year[reg]
            if 'sal' in cotisations_year[reg].keys() and 'pat' in cotisations_year[reg].keys():
                pensions_contrib.loc[cond, dates_yearsim] = cotisations_year[reg]['sal'] + cotisations_year[reg]['pat']
            else:
                pensions_contrib.loc[cond, dates_yearsim] = cotisations_year[reg]['tot']
        pensions_contrib['year_dep'][pensions_contrib['ident'].isin(ident_depart)] = yearsim
        cond = (pensions_contrib['ident'].isin(ident_depart)) & (pensions_contrib['regime'] == 'RG')
        pensions_contrib.loc[cond,'age'] = data_bounded.info_ind['agem'][data_bounded.info_ind['index'] == ident_depart] // 12
        for var in ['naiss', 'n_enf', 'findet', 'sexe']:
                pensions_contrib.loc[cond,var] = data_bounded.info_ind[var][data_bounded.info_ind['index'] == ident_depart]
        pensions_contrib.index = range(len(ident_index))

    for var in ['age', 'naiss', 'n_enf', 'findet', 'sexe']:
        pensions_contrib.loc[:,var] = pensions_contrib.loc[:,var].replace(0,nan)
        pensions_contrib.loc[:,var] = pensions_contrib.groupby("ident")[var].fillna(method ='ffill')
    pensions_contrib.loc[:,'n_enf'] = pensions_contrib.loc[:,'n_enf'].fillna(0)
    pensions_contrib.loc[:,'sexe'] = pensions_contrib.loc[:,'sexe'].fillna(0)
    pensions_contrib = pensions_contrib[~(pensions_contrib['pension'] == 0)]
    #TODO: Arbitrary for the moment -> add differential life expenctancy
    pensions_contrib['death'] = (pensions_contrib['year_dep'] - (pensions_contrib['age'] - 60) + 22).astype(int)
    for var in ['pension'] + [str(year*100 + 1) for year in range(first_year_sal, yearmax)]:
        pensions_contrib.loc[:, var] = around(pensions_contrib[var].astype(double),2)
    pensions_contrib.loc[:,'age'] = pensions_contrib['age'] - 1

    pensions_contrib['TRI'] = pensions_contrib.apply(TRI, axis=1)
    return pensions_contrib

if __name__ == '__main__':

    first_year = 2009
    last_year = 2019
    result = compute_TRI(first_year, last_year)
    print result.groupby(['regime', 'sexe'])['TRI'].mean()
    print result.groupby(['regime', 'sexe'])['TRI'].median()
    print result.groupby(['regime', 'sexe'])['age'].mean()
    print result.groupby(['regime'])['age'].median()
    print result.groupby(['regime', 'naiss'])['age'].mean()
    print result.groupby(['regime', 'age'])['pension'].mean()
    #result.to_csv('result.csv')
