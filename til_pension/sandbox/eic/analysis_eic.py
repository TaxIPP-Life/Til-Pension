# -*- coding: utf-8 -*-
import pandas as pd
from numpy import nan
from til_pension.simulation import PensionSimulation
from til_pension.pension_legislation import PensionParam, PensionLegislation
from til_pension.sandbox.eic.load_eic import load_eic_eir_data
from pensions_eic import compute_pensions_eic


def pensions_decomposition_eic(path_file_h5_eic, contribution=False, yearmin=2002, yearmax=2011):
    depart_by_yearsim = dict()
    # Define dates du taux plein -> already defined in individual info
    # Data contains 4 type of information: info_ind, pension_eir, salbrut, workstate
    already_retired = []
    for yearsim in range(yearmin, yearmax):
        df = load_eic_eir_data(path_file_h5_eic, to_return = True)
        idents = df['individus'].loc[df['individus']['year_liquidation_RG'] == yearsim, :].index
        ident_depart = list(idents)
        depart_by_yearsim[yearsim] = ident_depart
        already_retired += ident_depart
        print "Nb of retired people for ", yearsim, len(ident_depart)
    regimes = ['RG', 'agirc', 'arrco']  # , 'FP'
    nb_reg = len(regimes)
    ident_index = [ident for ident in already_retired for i in range(nb_reg)]
    reg_index = regimes * len(already_retired)
    pensions = pd.DataFrame(
        0,
        index = ident_index,
        columns = ['ident', 'age', 'naiss', 'n_enf', 'findet', 'sexe', 'year_dep', 'regime', 'pension'],
        )
    pensions['ident'] = ident_index
    pensions['regime'] = reg_index
    depart_by_yearsim = dict([(k, v) for k, v in depart_by_yearsim.iteritems() if v != []])
    for yearsim in depart_by_yearsim.keys():
        print(yearsim)
        ident_depart = [int(ident) for ident in depart_by_yearsim[yearsim]]
        data_bounded = load_eic_eir_data(path_file_h5_eic, yearsim, id_selected=ident_depart)
        param = PensionParam(yearsim, data_bounded)
        legislation = PensionLegislation(param)
        simul_til = PensionSimulation(data_bounded, legislation)
        simul_til.set_config()
        pensions_year = dict()
        majo = dict()
        minimum = dict()
        for reg in regimes:
            print reg
            pensions_year[reg] = simul_til.calculate("pension", regime_name = reg)
            majo[reg] = simul_til.calculate("majoration_pension", regime_name = reg)
            if reg in ['RG']:  # 'FP'
                minimum[reg] = simul_til.calculate("minimum_pension", regime_name = reg)
            if reg in ['agirc', 'arrco']:
                minimum[reg] = simul_til.calculate("minimum_points", regime_name = reg)
            cond = (pensions['regime'] == reg) * (pensions['ident'].isin(ident_depart))
            pensions.loc[cond, 'pension'] = pensions_year[reg]
            pensions.loc[cond, 'majoration_pension'] = majo[reg]
            pensions.loc[cond, 'minimum_pension'] = minimum[reg]
            if reg in ['RG']:
                pensions.loc[cond, 'pension_brute'] = simul_til.calculate("pension_brute_b", regime_name = reg)
                pensions.loc[cond, 'taux'] = simul_til.calculate("taux", regime_name = reg) * 100
                pensions.loc[cond, 'surcote'] = simul_til.calculate("surcote", regime_name = reg) * 100
                pensions.loc[cond, 'decote'] = simul_til.calculate("decote", regime_name = reg) * 100
                pensions.loc[cond, 'trim_surcote'] = simul_til.calculate("trimestres_excess_taux_plein",
                                                                         regime_name = reg)
                pensions.loc[cond, 'salref'] = simul_til.calculate("salref", regime_name = reg)
                pensions.loc[cond, 'trim_cot_til'] = simul_til.calculate("trim_cot_by_year",
                                                                         regime_name = reg).sum(axis=1)
                pensions.loc[cond, 'trim_tot_til'] = (simul_til.calculate("nb_trimesters", regime_name = reg) +
                                                      simul_til.calculate("trim_maj", regime_name = reg))
            if reg in ['agirc', 'arrco']:
                pensions.loc[cond, 'nb_point_til'] = simul_til.calculate("nb_points", regime_name = reg)
                pensions.loc[cond, 'nb_point_enf'] = simul_til.calculate("nb_points_enf", regime_name = reg)
                pensions.loc[cond, 'nb_point_maj_til'] = (pensions.loc[cond, 'nb_point_til'] +
                                                          pensions.loc[cond, 'nb_point_enf'])
        pensions['year_dep'][pensions['ident'].isin(ident_depart)] = yearsim
        cond = (pensions['ident'].isin(ident_depart)) & (pensions['regime'] == 'RG')
        pensions.loc[cond, 'age'] = \
            yearsim - data_bounded.info_ind['anaiss'][data_bounded.info_ind['noind'] == ident_depart]
        for var in ['naiss', 'n_enf', 'findet', 'sexe', 'anaiss',
                    'date_liquidation_eir', 'duree_assurance_tot_RG', 'year_liquidation_RG']:
                pensions.loc[cond, var] = data_bounded.info_ind[var][data_bounded.info_ind['noind'] == ident_depart]
        pensions.index = range(len(ident_index))

    for var in ['age', 'naiss', 'n_enf', 'findet', 'sexe']:
        pensions.loc[:, var] = pensions.loc[:, var].replace(0, nan)
        pensions.loc[:, var] = pensions.groupby("ident")[var].fillna(method = 'ffill')
    pensions.loc[:, 'n_enf'] = pensions.loc[:, 'n_enf'].fillna(0)
    pensions.loc[:, 'sexe'] = pensions.loc[:, 'sexe'].fillna(0)
    pensions = pensions[~(pensions['pension'] == 0)]
    pensions.loc[:, 'age'] = pensions['age'] - 1
    for var in ['pension', 'majoration_pension', 'minimum_pension', 'pension_brute']:
        pensions.loc[:, var + '_m'] = pensions.loc[:, var] / 12
    return pensions


def descriptive_statistics_data(data):
    salbrut = data['salbrut']
    workstate = data['workstate']
    individus = data['individus']
    pensions = data['pension_eir']
    descriptive_statistics_individus(individus)
    descriptive_statistics_career(workstate, salbrut)
    descriptive_statistics_pension(pensions)


def descriptive_statistics_individus(table):
    print table['sexe'].value_counts()
    print table['nb_obs_career'].value_counts()
    print table.groupby(['sexe'])['year_liquidation_RG'].value_counts()
    print table.groupby(['sexe'])['year_liquidation_RG'].mean()
    print table.groupby(['naiss', 'sexe'])['year_liquidation_RG'].mean()
    print table.groupby(['sexe'])['n_enf'].mean()
    print table.groupby(['sexe'])['first_year_RG'].mean()
    print table.groupby(['sexe', 'naiss'])['findet'].mean()
    table['age_retraite'] = 'year_liquidation_RG'


def descriptive_statistics_career(workstate, salbrut):
    # nb of years as an executive and number of years as a non-executive
    print " Main occupational position"
    print workstate.mode(axis=1)[0].value_counts()
    print " Nb of years in the private schemes per indiv"
    print workstate.count(axis=1).value_counts()
    print salbrut.count(axis=1).value_counts()
    # nb of wages available per year and mean of wages
    print " Nb of available wages per year"
    print pd.concat([salbrut.count(axis=0), salbrut.mean(axis=0), salbrut.median(axis=0)], axis=1)
    print " Nb each states per year"
    test = []
    for year in workstate.columns:
        add = workstate.groupby(year)[year].value_counts(dropna=False)
        add = add.reset_index()[[year, 0]].rename(columns={year: 'idx', 0: year}).set_index('idx')
        test += [add]
    to_print = pd.concat(test, axis=1)
    to_print.to_csv('stat_workstate.csv')
    print to_print


def descriptive_statistics_pension(pensions):
   print pensions.groupby('regime')['age_retraite'].mean()
   # print pensions.groupby('regime')['age_retraite'].describe()

if __name__ == '__main__':
    test = False
    if test:
        path_file_h5_eic = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\test_final.h5'
    else:
        path_file_h5_eic = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\modified.h5'
    data = load_eic_eir_data(path_file_h5_eic, to_return=True)
    descriptive_statistics_data(data)
    for dataset in data.keys():
        data[dataset].to_csv('C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\' + dataset + '.csv')
    #result = compute_pensions_eic(path_file_h5_eic, contribution=False, yearmin=2004, yearmax=2009)
