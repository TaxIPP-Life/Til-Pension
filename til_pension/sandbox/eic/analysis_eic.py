# -*- coding: utf-8 -*-

from til_pension.sandbox.eic.load_eic import compute_pensions_eic, load_eic_eir_data



if __name__ == '__main__':
    test = False
    if test:
        path_file_h5_eic = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\test_final.h5'
        path_file_h5_eic2 = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\test_final2.h5'
    else:
        path_file_h5_eic = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\final.h5'
        path_file_h5_eic2 = 'C:\\Users\\l.pauldelvaux\\Desktop\\MThesis\\Data\\final2.h5'
    data = load_eic_eir_data(path_file_h5_eic, to_return=True)
    result = compute_pensions_eic(path_file_h5_eic, contribution=False, yearmin=2004, yearmax=2009)
