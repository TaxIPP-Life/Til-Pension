# -*- coding: utf-8 -*-

class ArrayAttributes(object):
    
    def __init__(self, array, dates):
        self.array = array
        self.dates = dates
        
    def array_selected_dates(self, first_year=None, last_year=None, first_month=1,
                              last_month=12, inplace=False):
        ''' La table d'input dont les colonnes sont des dates est renvoyées amputée 
            des années postérieures à last_year (last_year incluse) 
            et antérieures à first_year (first_year incluse) '''
        array = self.array
        dates = self.dates
        first_date = 100*first_year + first_month
        last_date = 100*last_year + last_month
        array_dates = [i  
                       for i in range(len(dates))
                            if first_date <= dates[i] and dates[i] < last_date
                        ]
        if inplace == True:
            self.array = array[:,array_dates]
            self.dates = dates[array_dates]
        else:
            return (array[:,array_dates], dates[array_dates])
    