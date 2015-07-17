# -*- coding: utf-8 -*-
import pandas as pd
from numpy import nan
from til_pension.simulation import PensionSimulation
from til_pension.pension_legislation import PensionParam, PensionLegislation
from til_pension.sandbox.eic.load_eic import load_eic_eir_data, load_eic_eir_table


def pensions_decomposition_eic(path_file_h5_eic, contribution=False, yearmin=2004, yearmax=2009):
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
    regimes = ['RG', 'agirc', 'arrco', 'FP']
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
            if reg in ['FP', 'RG']:
                minimum[reg] = simul_til.calculate("minimum_pension", regime_name = reg)
            if reg in ['agirc', 'arrco']:
                minimum[reg] = simul_til.calculate("minimum_points", regime_name = reg)
            cond = (pensions['regime'] == reg) * (pensions['ident'].isin(ident_depart))
            pensions.loc[cond, 'pension'] = pensions_year[reg]
            pensions.loc[cond, 'majoration_pension'] = majo[reg]
            pensions.loc[cond, 'minimum_pension'] = minimum[reg]
            pensions.loc[cond, 'pension_brute'] = simul_til.calculate("pension_brute_b", regime_name = reg)
            if reg in ['FP', 'RG']:
                pensions.loc[cond, 'taux'] = simul_til.calculate("taux", regime_name = reg) * 100
                pensions.loc[cond, 'surcote'] = simul_til.calculate("surcote", regime_name = reg) * 100
                pensions.loc[cond, 'surcote'] = simul_til.calculate("decote", regime_name = reg) * 100
                pensions.loc[cond, 'trim_surcote'] = simul_til.calculate("trimestres_excess_taux_plein",
                                                                         regime_name = reg)
                pensions.loc[cond, 'salref'] = simul_til.calculate("salref", regime_name = reg)
                pensions.loc[cond, 'trim_cot_til'] = simul_til.calculate("trim_cot_by_year",
                                                                         regime_name = reg).sum(axis=1)
                pensions.loc[cond, 'trim_tot_til'] = simul_til.calculate("nb_trimesters", regime_name = reg)
        pensions['year_dep'][pensions['ident'].isin(ident_depart)] = yearsim
        cond = (pensions['ident'].isin(ident_depart)) & (pensions['regime'] == 'RG')
        pensions.loc[cond, 'age'] = \
            yearsim - data_bounded.info_ind['anaiss'][data_bounded.info_ind['noind'] == ident_depart]
        for var in ['naiss', 'n_enf', 'findet', 'sexe']:
                pensions.loc[cond, var] = \
                    data_bounded.info_ind[var][data_bounded.info_ind['noind'] == ident_depart]
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


def compare_eir(path_file_h5_eic):
    result_til = pensions_decomposition_eic(path_file_h5_eic, contribution=False, yearmin=2004, yearmax=2009)
    result_til = result_til.rename(columns = {'ident': 'noind'})
    data = load_eic_eir_data(path_file_h5_eic, to_return=True)
    result_eir = data['pension_eir']
    result_eir['noind'] = result_eir.index
    result_eir['regime'] = result_eir['regime'].replace({'Agirc': 'agirc',
                                                         'Arcco': 'arrco', 'FP_a': 'FP', 'FP_s': 'FP'})
    result = result_til.merge(result_eir, on = ['noind', 'regime'], suffixes=('_til', '_eir'))
    to_compare = ['noind', 'naiss', 'n_enf', 'regime', 'age_retraite', 'pension_brute_m', 'pension_m',
                  'majoration_pension_m', 'minimum_pension_m', 'pension_direct',
                  'pension_bonif_enf', 'pension_tot', 'pension_mini', 'salref', 'sam', 'surcote',
                   'taux', 'taux_avantmico', 'taux_surcote', 'trim_surcote', 'trimsur', 'trimdec', 'trim_cot',
                  'trim_tot', 'trim_cot_til', 'trim_tot_til', 'typdd']
    delta_equivalent = {'minimum': ('minimum_pension_m', 'pension_mini'),
                        'brute': ('pension_brute_m', 'pension_direct'),
                        'final': ('pension_m', 'pension_tot'),
                        'majo': ('majoration_pension_m', 'pension_bonif_enf'),
                        'sam': ('salref', 'sam'),
                        'taux': ('taux', 'taux_avantmico'),
                        'surcote': ('surcote', 'taux_surcote'),
                        'trim_cot': ('trim_cot_til', 'trim_cot'),
                        'trim_tot': ('trim_tot_til', 'trim_tot')}
    for delta, vars in delta_equivalent.iteritems():
        result.loc[:, 'delta_' + delta] = result[vars[0]] - result[vars[1]]
        to_compare += ['delta_' + delta]
    return result[to_compare]

if __name__ == '__main__':
    test = True
    if test:
        path_file_h5_eic = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\test_final.h5'
        path_file_h5_eic2 = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\test_final2.h5'
    else:
        path_file_h5_eic = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\final.h5'
        path_file_h5_eic2 = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\final2.h5'
    result = compare_eir(path_file_h5_eic)
    result.to_csv('result.csv', sep=";", decimal=',')
    data = load_eic_eir_data(path_file_h5_eic, to_return=True)