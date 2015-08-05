# -*- coding: utf-8 -*-

import pandas as pd
from numpy import nan
from til_pension.simulation import PensionSimulation
from til_pension.pension_legislation import PensionParam, PensionLegislation
from til_pension.sandbox.eic.load_eic import load_eic_eir_data, load_eic_eir_table


def compute_pensions_eic(path_file_h5_eic, contribution=True, yearmin=2004, yearmax=2009):
    depart_by_yearsim = dict()
    # Define dates du taux plein -> already defined in individual info
    # Data contains 4 type of information: info_ind, pension_eir, salbrut, workstate
    already_retired = []
    for yearsim in range(yearmin, yearmax):
        df = load_eic_eir_table(path_file_h5_eic, 'info_ind', columns=['year_retired'])
        ident_depart = list(df.loc[df['year_retired'] == yearsim].index)
        depart_by_yearsim[yearsim] = ident_depart
        already_retired += ident_depart
        print "Nb of retired people for ", yearsim, len(ident_depart)
    workstate = load_eic_eir_table(path_file_h5_eic, 'workstate')
    first_year_sal = int(min(workstate.columns) // 100)

    regimes = ['RG', 'agirc', 'arrco', 'FP']
    nb_reg = len(regimes)
    ident_index = [ident for ident in already_retired for i in range(nb_reg)]
    reg_index = regimes * len(already_retired)
    if contribution:
        all_dates = [str(year * 100 + 1) for year in range(first_year_sal, yearmax)]
        pensions_contrib = pd.DataFrame(
            0,
            index = ident_index,
            columns = ['ident', 'age', 'naiss', 'n_enf', 'findet', 'sexe', 'year_dep', 'regime', 'pension', 'pcs'] + all_dates,
            )
    else:
        pensions_contrib = pd.DataFrame(
            0,
            index = ident_index,
            columns = ['ident', 'age', 'naiss', 'n_enf', 'findet', 'sexe', 'year_dep', 'regime', 'pension', 'pcs'],
            )
    pensions_contrib['ident'] = ident_index
    pensions_contrib['regime'] = reg_index
    depart_by_yearsim = dict([(k, v) for k, v in depart_by_yearsim.iteritems() if v != []])
    for yearsim in depart_by_yearsim.keys():
        print(yearsim)
        ident_depart = [int(ident) for ident in depart_by_yearsim[yearsim]]
        data_bounded = load_eic_eir_data(path_file_h5_eic, yearsim, id_selected=ident_depart)
        print("Data loaded")
        param = PensionParam(yearsim, data_bounded)
        legislation = PensionLegislation(param)
        simul_til = PensionSimulation(data_bounded, legislation)
        simul_til.set_config()
        print("Simulation initialized")
        # pensions_year = simul_til.calculate("pension")
        # assert len(pensions_year['FP']) == len(cotisations_year['FP']['sal']) == len(depart_by_yearsim[yearsim])
        dates_yearsim = [str(year * 100 + 1) for year in range(first_year_sal, yearsim)]
        pensions_year = dict()
        cotisations_year = dict()
        for reg in regimes:
            pensions_year[reg] = simul_til.calculate("pension", regime_name = reg)
            cond = (pensions_contrib['regime'] == reg) * (pensions_contrib['ident'].isin(ident_depart))
            pensions_contrib.loc[cond, 'pension'] = pensions_year[reg]
            pensions_contrib.loc[cond, 'regime'] = reg
            if contribution:
                cotisations_year[reg] = simul_til.calculate("cotisations", regime_name = reg)
                if 'sal' in cotisations_year[reg].keys() and 'pat' in cotisations_year[reg].keys():
                    pensions_contrib.loc[cond, dates_yearsim] = cotisations_year[reg]['sal'] + \
                                                                cotisations_year[reg]['pat']
                else:
                    pensions_contrib.loc[cond, dates_yearsim] = cotisations_year[reg]['tot']
        pensions_contrib['year_dep'][pensions_contrib['ident'].isin(ident_depart)] = yearsim
        cond = (pensions_contrib['ident'].isin(ident_depart)) & (pensions_contrib['regime'] == 'RG')
        pensions_contrib.loc[cond, 'age'] = \
            yearsim - data_bounded.info_ind['anaiss'][data_bounded.info_ind['noind'] == ident_depart]
        # TODO:
        for var in ['naiss', 'n_enf', 'findet', 'sexe', 'pcs']:
                pensions_contrib.loc[cond, var] = \
                    data_bounded.info_ind[var][data_bounded.info_ind['noind'] == ident_depart]
        pensions_contrib.index = range(len(ident_index))
        print(" Pensions and contributions have been calculated for year {}".format(yearsim))
    for var in ['age', 'naiss', 'n_enf', 'findet', 'sexe', 'pcs']:
        pensions_contrib.loc[:, var] = pensions_contrib.loc[:, var].replace(0, nan)
        pensions_contrib.loc[:, var] = pensions_contrib.groupby("ident")[var].fillna(method = 'ffill')
    pensions_contrib.loc[:, 'n_enf'] = pensions_contrib.loc[:, 'n_enf'].fillna(0)
    pensions_contrib.loc[:, 'sexe'] = pensions_contrib.loc[:, 'sexe'].fillna(0)
    pensions_contrib = pensions_contrib[~(pensions_contrib['pension'] == 0)]
    pensions_contrib.loc[:, 'age'] = pensions_contrib['age'] - 1
    pensions_contrib.loc[:, 'pension_m'] = pensions_contrib.loc[:, 'pension'] / 12
    return pensions_contrib


if __name__ == '__main__':
    test = True
    if test:
        path_file_h5_eic = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\test_final.h5'
        path_file_h5_eic2 = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\test_final2.h5'
    else:
        path_file_h5_eic = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\final.h5'
        path_file_h5_eic2 = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\final2.h5'
    data = load_eic_eir_data(path_file_h5_eic, to_return=True)
    pensions = compute_pensions_eic(path_file_h5_eic)
