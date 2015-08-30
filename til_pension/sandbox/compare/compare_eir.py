# -*- coding: utf-8 -*-
import pandas as pd
from numpy import nan
from til_pension.simulation import PensionSimulation
from til_pension.pension_legislation import PensionParam, PensionLegislation
from til_pension.sandbox.eic.load_eic import load_eic_eir_data
from til_pension.sandbox.tri.compute_TRI import revalo_pension


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
    regimes = ['RG', 'agirc', 'arrco'] #, 'FP'
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
        for var in ['naiss', 'n_enf', 'findet', 'sexe', 'anaiss', 'date_liquidation_eir', 'duree_assurance_tot_RG', 'year_liquidation_RG']:
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


def coeff_inverse_revalo(row):
    year_dep = row['year_liquidation_RG']
    eir_year = row['eir']
    coeff_revalo = revalo_pension(year_dep, eir_year).product()
    return 1 / coeff_revalo


def compare_eir(path_file_h5_eic):
    result_til = pensions_decomposition_eic(path_file_h5_eic, contribution=False)
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
                  'trim_tot', 'trim_cot_til', 'trim_tot_til', 'anaiss', 'duree_assurance_tot_RG', 'year_liquidation_RG',
                  'nb_point', 'nb_point_maj', 'nb_point_anc_arrco', 'nb_point_grat_arrco', 'eir']
    result.loc[:, 'year_liquidation_RG'] = result.groupby('noind')['year_liquidation_RG'].fillna(method='bfill')
    result.loc[:, 'year_liquidation_RG'] = result.groupby('noind')['year_liquidation_RG'].fillna(method='ffill')
    coeff_inverse = result[['year_liquidation_RG', 'eir']].apply(coeff_inverse_revalo, axis = 1)
    for var_eir in ['pension_mini', 'pension_direct', 'pension_tot', 'pension_bonif_enf']:
        result.loc[:, var_eir] = result[var_eir] * coeff_inverse
    delta_equivalent = {'minimum': ('minimum_pension_m', 'pension_mini'),
                        'brute': ('pension_brute_m', 'pension_direct'),
                        'final': ('pension_m', 'pension_tot'),
                        'majo': ('majoration_pension_m', 'pension_bonif_enf'),
                        'sam': ('salref', 'sam'),
                        'taux': ('taux', 'taux_avantmico'),
                        'surcote': ('surcote', 'taux_surcote'),
                        'trim_cot': ('trim_cot_til', 'trim_cot'),
                        'trim_tot': ('trim_tot_til', 'trim_tot'),
                        'nb_points': ('nb_point_til', 'nb_point'),
                        'nb_points_maj': ('nb_point_maj_til', 'nb_point_maj')}
    for delta, vars in delta_equivalent.iteritems():
        result.loc[:, 'delta_' + delta] = result[vars[0]] - result[vars[1]]
        to_compare += ['delta_' + delta]
    return result[to_compare]


if __name__ == '__main__':
    test = False
    if test:
        path_file_h5_eic = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\test_modified.h5'
    else:
        path_file_h5_eic = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\modified.h5'
    result = compare_eir(path_file_h5_eic)
    result = result.loc[result['regime'].isin(['RG', 'agirc', 'arrco']), :]
    result.to_csv('result.csv', sep=";", decimal='.')
    if test:
        result.to_csv('result_test.csv', sep=";", decimal='.')
    else:
        result.to_csv('result.csv', sep=";", decimal='.')
    data = load_eic_eir_data(path_file_h5_eic, to_return=True)
