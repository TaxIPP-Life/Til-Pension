# -*- coding: utf-8 -*-

class ArrayAttributes(object):
    
    def __init__(self, array, dates):
        self.array = array
        self.dates = dates
        
    def array_selected_dates(self, first, last, date_type='year', inplace=False):
        ''' La table d'input dont les colonnes sont des dates est renvoyées amputée 
            des années postérieures à first (first incluse) 
            et antérieures strictement à last 
            date_type est month ou year
            '''
        array = self.array
        dates = self.dates
        if first is None:
            first = 0
        if last is None:
            last = 3000
        if date_type == 'year':
            first = 100*first + 1
            last = 100*last + 1
        array_dates = [i  
                       for i in range(len(dates))
                            if first <= dates[i] and dates[i] < last
                        ]
        if inplace == True:
            self.array = array[:,array_dates]
            self.dates = dates[array_dates]
        else:
            return (array[:,array_dates], dates[array_dates])
    