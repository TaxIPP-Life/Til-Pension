# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame

class TimeArray(object):
    
    def __init__(self, array, dates):
        self.array = array
        self.dates = dates
        
    def selected_dates(self, first, last, date_type='year', inplace=False):
        ''' La table d'input dont les colonnes sont des dates est renvoyées amputée 
            des années postérieures à first (first incluse) 
            et antérieures strictement à last 
            date_type est month ou year
            '''
        array = self.array
        dates = self.dates
        if date_type == 'year':
            if first:
                first = 100*first + 1
            if last:
                last = 100*last + 1
        array_dates = [i  
                       for i in range(len(dates))
                            if first <= dates[i] and dates[i] < last
                        ]
        dates = [dates[i] for i in array_dates]
        if inplace == True:
            self.array = array[:,array_dates]
            self.dates = dates
        else:
            return TimeArray(array[:,array_dates], dates)
        
    def translate_frequency(self, output_frequency='month', method=None, data_type='numpy', inplace=False):
        '''method should eventually control how to switch from month based table to year based table
            so far we assume year is True if January is True 
            idea : format_table as an argument instead of testing with isinstance
            '''
        if (np.array(self.dates) % 100 == 1).all() :
            input_frequency = 'year' 
        else : 
            input_frequency = 'month' 
        if input_frequency == output_frequency:
            return (self.array, self.dates) 
        if data_type == 'numpy':
            if output_frequency == 'year': # if True here, input_frequency=='month'
                assert len(self.dates) % 12 == 0 #TODO: to remove eventually
                nb_years = len(self.dates) // 12
                output_dates = [date for date in self.dates if date % 100 == 1]
                output_dates_ix = self.dates.index(output_dates)
                #here we could do more complex
                if method is None: #first month of each year
                    output = self.array[:, output_dates_ix]
                if method is 'sum':
                    output = self.array[:, output_dates_ix].copy()
                    for month in range(1,12):
                        month_to_add = [year*12 + month for year in xrange(nb_years)]
                        output += self.array[:, month_to_add]
            elif output_frequency == 'month': # if True here, input_frequency=='year'
                output_dates = [year + month for year in self.dates for month in range(12)]
                output = np.repeat(self.array, 12, axis=1)
                if method == 'divide':
                    output = np.around(np.divide(output, 12), decimals=3)
            if inplace == True:
                self.array = output
                self.dates = output_dates
            else:
                return (output, output_dates)
                
        else:
            # TODO : fix this part if running with pandas DataFrame
            import pdb
            pdb.set_trace()
            assert data_type == 'pandas'
            if output_frequency == 'year': # if True here, input_frequency=='month'
                detected_years = set([date // 100 for date in table.columns])
                output_dates = [100*x + 1 for x in detected_years]
                #here we could do more complex
                if method is None:
                    return table.loc[:, output_dates]
                if method is 'sum':
                    pdb.set_trace()
            if output_frequency == 'month': # if True here, input_frequency=='year'
                output_dates = [x + k for k in range(12) for x in table.columns ]
                output_table1 = DataFrame(np.tile(table, 12), index=table.index, columns=output_dates)
                return output_table1.reindex_axis(sorted(output_table1.columns), axis=1)  
    