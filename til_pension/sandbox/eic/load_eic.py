# -*- coding: utf-8 -*-

import datetime as dt
import pandas as pd
from numpy import maximum
from matching_patrimoine_eic.matching.databases_builder import build_data_eic_eir_til
from til_pension.pension_data import PensionData


def index_by_noind(df):
    if df.index.name != 'noind':
            df[['noind']] = df.sort(['noind'])[['noind']].astype(int)
            df = df.set_index(['noind'])
    return df


def column_to_int(df, yearsim=None):
    df.columns = [int(col) for col in df.columns]
    if yearsim:
        col_to_keep = [col for col in df.columns if col // 100 < yearsim]
        df = df.loc[:, col_to_keep]
    return df


def load_eic_eir_data(path_file_h5_eic, yearsim = None, id_selected=None, to_return=False):
    ''' This functions load eir and eic data from the .h5 cerated
    thanks the 'matching_eic_patrimoine' package.'''
    # Initial check of the accuracy of the file
    hdf = pd.HDFStore(path_file_h5_eic)
    datasets_in_hdf = [dataset for dataset in hdf.keys()]
    no_reload = (('/individus' in datasets_in_hdf) * ('/salbrut' in datasets_in_hdf) *
                ('/workstate' in datasets_in_hdf) * ('/pension_eir' in datasets_in_hdf))
    hdf.close()
    if not no_reload:
        print "EIC/EIR Data has to be rebuilt"
        build_data_eic_eir_til(test=False, selection='eir and eic')

    # Load of needed data
    hdf = pd.HDFStore(path_file_h5_eic)
    if not id_selected:
        id_selected = hdf.select('/individus', columns = ['noind']).index

    info_ind = index_by_noind(hdf.select('/individus'))
    info_ind = info_ind.ix[id_selected, :]
    info_ind.loc[:, 'naiss'] = info_ind['anaiss'].apply(lambda x: dt.date(int(x), 1, 1))
    if yearsim:
        info_ind.loc[:, 'agem'] = (yearsim - info_ind['anaiss'].astype(int)) * 12
    info_ind.loc[:, 'tauxprime'] = 0
    info_ind.loc[:, 'nb_enf_RG'] = 0

    salbrut = index_by_noind(hdf.select('/salbrut'))
    salbrut = column_to_int(salbrut, yearsim)
    salbrut = salbrut.ix[id_selected, :]

    workstate = index_by_noind(hdf.select('/workstate'))
    workstate = column_to_int(workstate, yearsim)
    workstate = workstate.ix[id_selected, :]

    pension_eir = index_by_noind(index_by_noind(hdf.select('/pension_eir')))
    pension_eir = pension_eir.ix[id_selected, :]
    hdf.close()
    assert info_ind.shape[0] == workstate.shape[0] == salbrut.shape[0]

    # Format data to get info_child
    # info_child_ = _child_by_age(info_child, yearsim, id_selected)
    # nb_pac = count_enf_pac(info_child_, info.index)
    # info_ind = info.iloc[ix_selected,:]
    # t_naiss, n_enf, sexe, findet, tauxprime, naiss, id
    for regime in ['FP', 'RG']:
        info_ind.loc[:, 'nb_enf_' + regime] = pension_eir.loc[pension_eir['regime'] == regime, 'nenf']
        info_ind.loc[:, 'nb_enf_' + regime] = info_ind.loc[:, 'nb_enf_' + regime].fillna(0)
    info_ind.loc[:, 'nb_enf_RSI'] = 0
    for var in ['nb_pac', 'nb_enf_all', 'n_enf']:
        info_ind.loc[:, var] = maximum(info_ind.loc[:, 'nb_enf_RG'], info_ind.loc[:, 'nb_enf_FP'])
    info_ind.loc[:, 'findet'] = info_ind['min_year_career'] - info_ind['anaiss']
    info_ind.loc[:, 'date_liquidation_eir'] = pension_eir.groupby(pension_eir.index)['date_liquidation'].min()
    info_ind.loc[:, 'date_jouissance_eir'] = pension_eir.groupby(pension_eir.index)['date_jouissance'].min()
    if not to_return:
        data = PensionData.from_arrays(workstate, salbrut, info_ind)
        return data
    if to_return:
        to_return = dict()
        for table in ['workstate', 'salbrut', 'info_ind', 'pension_eir']:
            to_return[table] = eval(table)
        to_return['individus'] = to_return.pop('info_ind')
        return to_return


def load_eic_eir_table(path_file_h5_eic, table_name, id_selected=None, columns=None):
    # Load of needed data
    hdf = pd.HDFStore(path_file_h5_eic)
    if not id_selected:
        id_selected = hdf.select('/individus', columns = ['noind']).index

    if table_name == 'info_ind':
        info_ind = index_by_noind(hdf.select('/individus', columns = columns))
        hdf.close()
        info_ind = info_ind.ix[id_selected, :]
        return info_ind

    elif table_name == 'salbrut':
        salbrut = index_by_noind(hdf.select('/salbrut', columns = columns))
        hdf.close()
        salbrut = column_to_int(salbrut)
        salbrut = salbrut.ix[id_selected, :]
        return salbrut

    elif table_name == 'workstate':
        workstate = index_by_noind(hdf.select('/workstate', columns = columns))
        hdf.close()
        workstate = column_to_int(workstate)
        workstate = workstate.ix[id_selected, :]
        return workstate
    else:
        print "No name table named {}".format(table_name)


if __name__ == '__main__':
    test = True
    if test:
        path_file_h5_eic = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\test_final.h5'
        path_file_h5_eic2 = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\test_final2.h5'
    else:
        path_file_h5_eic = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\final.h5'
        path_file_h5_eic2 = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\final2.h5'
    data = load_eic_eir_data(path_file_h5_eic, to_return=True)
