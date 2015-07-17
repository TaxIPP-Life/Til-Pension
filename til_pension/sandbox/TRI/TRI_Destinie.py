# -*- coding: utf-8 -*-


import pandas as pd
from numpy import nan, around, double
from til_pension.sandbox.compare.CONFIG_compare import pensipp_comparison_path as pensipp_data_path
from til_pension.simulation import PensionSimulation
from til_pension.pension_legislation import PensionParam, PensionLegislation
from til_pension.sandbox.compare.load_pensipp import load_pensipp_data
from til_pension.sandbox.TRI.compute_TRI import TRI
import numpy as np
try:
    from scipy.optimize import fsolve
except:
    pass
first_year_sal = 1949


def depart_taux_plein(yearmin, yearmax):
    ''' This functions gives individuals who retire (value, 'depart à taux plein') by year of retirement (key) '''
    already_retired = []
    depart_by_yearsim = dict()
    for yearsim in range(yearmin, yearmax):
        print "Depart", yearsim
        data_bounded = load_pensipp_data(
            pensipp_data_path, yearsim, first_year_sal, selection_naiss = [1948, 1949, 1950, 1951, 1952])
        print("Data loaded")
        param = PensionParam(yearsim, data_bounded)
        legislation = PensionLegislation(param)
        simul_til = PensionSimulation(data_bounded, legislation)
        simul_til.set_config()
        regimes = ['RG', 'FP', 'RSI']  # 'agirc', 'arrco',
        for regime in regimes:
            dates_taux_plein = simul_til.calculate("date_start_taux_plein", regime_name = regime)

        dates_taux_plein = [
            simul_til.calculate("date_start_taux_plein", regime_name = regime) for regime in regimes
            ]

        dates_taux_plein = reduce(np.minimum, dates_taux_plein)

        # Selection des individus qui partent en retraite à yearsim (=t)
        # car ils ont satisfaits les conditions de taux plein à yearsim - 1 (=t-1)
        is_taux_plein = (dates_taux_plein == (yearsim - 1) * 100 + 1)
        ident_depart = [
            ident
            for ident in simul_til.data.info_ind['index'][is_taux_plein]
            if ident not in already_retired
            ]
        depart_by_yearsim[yearsim] = ident_depart
        already_retired += ident_depart
        print "Nb of retired people for ", yearsim, len(ident_depart)
    return depart_by_yearsim, already_retired


def compute_TRI(yearmin, yearmax):
    depart_by_yearsim = dict()
    # Define dates du taux plein
    depart_by_yearsim, already_retired = depart_taux_plein(yearmin, yearmax)
    all_dates = [str(year * 100 + 1) for year in range(first_year_sal, yearmax)]
    regimes = ['RG', 'agirc', 'arrco', 'FP', 'RSI']

    nb_reg = len(regimes)
    ident_index = [ident for ident in already_retired for i in range(nb_reg)]
    reg_index = regimes * len(already_retired)
    # index = pd.MultiIndex.from_arrays([ident_index, reg_index], names=['ident', 'regime'])

    pensions_contrib = pd.DataFrame(
        0,
        index = ident_index,
        columns = ['ident', 'age', 'naiss', 'n_enf', 'findet', 'sexe', 'year_dep', 'regime', 'pension'] + all_dates,
        )
    pensions_contrib['ident'] = ident_index
    pensions_contrib['regime'] = reg_index

    for yearsim in range(yearmin, yearmax):
        print(yearsim)

        ident_depart = [int(ident) for ident in depart_by_yearsim[yearsim]]
        data_bounded = load_pensipp_data(pensipp_data_path, yearsim, first_year_sal, selection_id = ident_depart)
        print("Data loaded")

        param = PensionParam(yearsim, data_bounded)
        legislation = PensionLegislation(param)

        simul_til = PensionSimulation(data_bounded, legislation)
        simul_til.set_config()
        # pensions_year = simul_til.calculate("pension")
        # assert len(pensions_year['FP']) == len(cotisations_year['FP']['sal']) == len(depart_by_yearsim[yearsim])
        dates_yearsim = [str(year * 100 + 1) for year in range(first_year_sal, yearsim)]

        pensions_year = dict()
        cotisations_year = dict()

        for reg in regimes:
            pensions_year[reg] = simul_til.calculate("pension", regime_name = reg)
            cotisations_year[reg] = simul_til.calculate("cotisations", regime_name = reg)
            cond = (pensions_contrib['regime'] == reg) * (pensions_contrib['ident'].isin(ident_depart))
            pensions_contrib.loc[cond, 'pension'] = pensions_year[reg]
            if 'sal' in cotisations_year[reg].keys() and 'pat' in cotisations_year[reg].keys():
                pensions_contrib.loc[cond, dates_yearsim] = cotisations_year[reg]['sal'] + cotisations_year[reg]['pat']
            else:
                pensions_contrib.loc[cond, dates_yearsim] = cotisations_year[reg]['tot']
        pensions_contrib['year_dep'][pensions_contrib['ident'].isin(ident_depart)] = yearsim
        cond = (pensions_contrib['ident'].isin(ident_depart)) & (pensions_contrib['regime'] == 'RG')
        pensions_contrib.loc[cond, 'age'] = \
            data_bounded.info_ind['agem'][data_bounded.info_ind['index'] == ident_depart] // 12
        for var in ['naiss', 'n_enf', 'findet', 'sexe']:
                pensions_contrib.loc[cond, var] = \
                    data_bounded.info_ind[var][data_bounded.info_ind['index'] == ident_depart]
        pensions_contrib.index = range(len(ident_index))

    for var in ['age', 'naiss', 'n_enf', 'findet', 'sexe']:
        pensions_contrib.loc[:, var] = pensions_contrib.loc[:, var].replace(0, nan)
        pensions_contrib.loc[:, var] = pensions_contrib.groupby("ident")[var].fillna(method = 'ffill')
    pensions_contrib.loc[:, 'n_enf'] = pensions_contrib.loc[:, 'n_enf'].fillna(0)
    pensions_contrib.loc[:, 'sexe'] = pensions_contrib.loc[:, 'sexe'].fillna(0)
    pensions_contrib = pensions_contrib[~(pensions_contrib['pension'] == 0)]
    # TODO: Arbitrary for the moment -> add differential life expenctancy
    pensions_contrib['death'] = (pensions_contrib['year_dep'] - (pensions_contrib['age'] - 60) + 22).astype(int)
    for var in ['pension'] + [str(year * 100 + 1) for year in range(first_year_sal, yearmax)]:
        pensions_contrib.loc[:, var] = around(pensions_contrib[var].astype(double), 2)
    pensions_contrib.loc[:, 'age'] = pensions_contrib['age'] - 1
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
    # result.to_csv('result.csv')
