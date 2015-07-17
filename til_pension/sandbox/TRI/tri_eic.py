# -*- coding: utf-8 -*-

from numpy import nan, around, double
from compute_TRI import TRI
from til_pension.sandbox.eic.load_eic import load_eic_eir_data
from til_pension.sandbox.eic.pensions_eic import compute_pensions_eic


def compute_tri_eic(path_file_h5_eic, yearmin_retired=2004, yearmax_retired=2009):
    pensions_contrib = compute_pensions_eic(path_file_h5_eic,
                                            contribution=True, yearmin=yearmin_retired,
                                            yearmax=yearmax_retired)
    # TODO: Arbitrary for the moment -> add differential life expenctancy
    pensions_contrib.loc[:, 'death'] = (pensions_contrib['year_dep'] -
                                        (pensions_contrib['age'] - 60) + 22).astype(float)
    for var in ['pension'] + [date for date in pensions_contrib.columns if date[:2] in ['19', '20']]:
        pensions_contrib.loc[:, var] = around(pensions_contrib[var].astype(double), 2)
    pensions_contrib.loc[:, 'TRI'] = pensions_contrib.apply(TRI, axis=1).replace(-2, nan)
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
    result = compute_tri_eic(path_file_h5_eic)
    print result.groupby(['regime', 'sexe'])['TRI'].mean()
    print result.groupby(['regime', 'sexe'])['TRI'].median()
    print result.groupby(['regime', 'sexe'])['age'].mean()
    print result.groupby(['regime'])['age'].median()
    print result.groupby(['regime', 'naiss'])['age'].mean()
    print result.groupby(['regime', 'age'])['pension'].mean()
    result.to_csv('result.csv')
