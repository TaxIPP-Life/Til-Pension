# -*- coding: utf-8 -*-

from numpy import nan, around, double
from compute_TRI import TRI
from til_pension.sandbox.eic.load_eic import load_eic_eir_data
from til_pension.sandbox.eic.pensions_eic import compute_pensions_eic
from til_pension.sandbox.tri.compute_tri_vector import tri

def compute_tri_eic(path_file_h5_eic, yearmin_retired=2003, yearmax_retired=2011):
    pensions_contrib = compute_pensions_eic(path_file_h5_eic,
                                            contribution=True, yearmin=yearmin_retired,
                                            yearmax=yearmax_retired)
    pensions_contrib.loc[:, 'anaiss'] = pensions_contrib.loc[:, 'naiss'].apply(lambda x: int(str(x)[0:4]))
    esperances = [(1, 1942, 26), (1, 1946, 27), (1, 1950, 27),
              (0, 1942, 21), (0, 1946, 22), (0, 1950, 22)]
    max_anaiss = 0
    for sexe, anaiss, years in esperances:
        pensions_contrib.loc[(pensions_contrib['sexe'] == sexe) & (pensions_contrib['anaiss'] == anaiss),
                             'death'] = pensions_contrib['anaiss'] + years + 60
        max_anaiss = max(max_anaiss, anaiss)
    try:
        assert (pensions_contrib.death.isnull() == 0).all()
    except:
        assert (pensions_contrib.loc[pensions_contrib['death'].isnull(), 'anaiss'] > max_anaiss).all()
        pensions_contrib = pensions_contrib.loc[~pensions_contrib['death'].isnull(), :]
        assert (pensions_contrib.death.isnull() == 0).all()
    for var in ['pension'] + [date for date in pensions_contrib.columns if date[:2] in ['19', '20']]:
        pensions_contrib.loc[:, var] = around(pensions_contrib[var].astype(double), 2)
    # pensions_contrib.loc[:, 'TRI_b'] = pensions_contrib.apply(TRI, axis=1)
    # pensions_contrib.loc[:, 'TRI_b'] = pensions_contrib.loc[:, 'TRI_b'].replace(-2, nan)
    pensions_contrib.loc[:, 'TRI'] = tri(pensions_contrib, nominal = False)
    pensions_contrib.loc[:, 'TRI_nominal'] = tri(pensions_contrib, nominal = True)
    return pensions_contrib


if __name__ == '__main__':
    test = False
    if test:
        path_file_h5_eic = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\test_final.h5'
        path_file_h5_eic2 = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\test_final2.h5'
    else:
        path_file_h5_eic = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\modified.h5'
        path_file_h5_eic2 = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\final2.h5'
    data = load_eic_eir_data(path_file_h5_eic, to_return=True)
    result_tri = compute_tri_eic(path_file_h5_eic)
    # print result_tri.groupby(['regime', 'sexe'])['TRI_b'].mean()
    # print result_tri.groupby(['regime', 'sexe'])['TRI_b'].median()
    print result_tri.groupby(['regime', 'sexe'])['TRI'].mean()
    print result_tri.groupby(['regime', 'sexe'])['TRI'].median()
    print result_tri.groupby(['regime', 'sexe'])['TRI_nominal'].mean()
    print result_tri.groupby(['regime', 'sexe'])['TRI_nominal'].median()
    print result_tri.groupby(['regime', 'sexe'])['age'].mean()
    print result_tri.groupby(['regime'])['age'].median()
    print result_tri.groupby(['regime', 'naiss'])['age'].mean()
    print result_tri.groupby(['regime', 'age'])['pension'].mean()
    result_tri.to_csv('result.csv')
