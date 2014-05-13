# -*- coding: utf-8 -*-

class ArrayAttributes(object):
    def __init__(self, array, dates):
        self.array = array
        self.dates = dates
        
    def array_selected_dates(self, first_year=None, last_year=None, first_month=1, last_month=12, inplace=False):
        ''' La table d'input dont les colonnes sont des dates est renvoyées emputée des années postérieures à last_year (last_year incluse) 
        et antérieures à first_year (first_year incluse) '''
        array = self.array.copy()
        dates = self.dates
        first_date = 100*first_year + first_month
        last_date = 100*last_year + last_month
        array_dates = [date 
                       for date in dates
                            if first_date <= date and date <= last_date
                        ]
        try:
            idx_first = dates.index(first_date)
        except:
            idx_first = 0
        try:
            idx_last = dates.index(last_date)
        except:
            idx_last = len(dates)
        idx_to_take = xrange(idx_first, idx_last)
        if inplace == True:
            self.array = array[:,idx_to_take]
            self.dates = array_dates
        else:
            return (array[:,idx_to_take], array_dates)
    