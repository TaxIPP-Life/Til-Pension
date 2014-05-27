# -*- coding: utf-8 -*-
from pandas import DataFrame
from numpy import array, tile, divide, around, in1d, repeat, sort, apply_along_axis, zeros

def determine_frequency(dates):
    if (array(dates) % 100 == 1).all() :
        frequency = 'year' 
    else: 
        frequency = 'month' 
    return frequency

class TimeArray(object):
    
    def __init__(self, array, dates, name=None):
        self.array = array
        self.dates = dates
        self.frequency = determine_frequency(dates)
        self.name = name
    
    def copy(self):
        return TimeArray(self.array.copy(), self.dates)
    
    def isin(self, code):
        array_selection = in1d(self.array.copy(), code).reshape(self.array.shape)
        return TimeArray(array_selection, self.dates)
        
    def sum(self, axis=1):
        ''' Cette fonction renvoie un vecteur (de longueur le nb de ligne de l'array)
        donnant :
        - axis = 1 : la somme des colonnes de l'array
        - axis = 0 : la somme des lignes de l'array '''
        return self.array.sum(axis=axis)
    
    def selected_dates(self, first=None, last=None, date_type='year', inplace=False):
        ''' La table d'input dont les colonnes sont des dates est renvoyées amputée 
            des années postérieures à first (first incluse) 
            et antérieures strictement à last 
            date_type est month ou year
            '''
        array = self.array.copy()
        dates = self.dates
        if first is None:
            first = min(dates)
        if last is None:
            last = max(dates)
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
    
    def translate_frequency(self, output_frequency='month', method=None, inplace=False):
        '''method should eventually control how to switch from month based table to year based table
            so far we assume year is True if January is True 
            idea : format_table as an argument instead of testing with isinstance
            '''
        array = self.array.copy()
        input_frequency = self.frequency
        if input_frequency == output_frequency:
            if inplace == True:
                return 'rien'
            else:
                return TimeArray(array, self.dates)
        if output_frequency == 'year': # if True here, input_frequency=='month'
            assert len(self.dates) % 12 == 0 #TODO: to remove eventually
            nb_years = len(self.dates) // 12
            output_dates = [date for date in self.dates if date % 100 == 1]
            output_dates_ix = [self.dates.index(output_date) for output_date in output_dates]
            #here we could do more complex
            if method is None: #first month of each year
                output = self.array[:, output_dates_ix]
            if method is 'sum':
                output = array[:, output_dates_ix]
                for month in range(1,12):
                    month_to_add = [year*12 + month for year in xrange(nb_years)]
                    output += array[:, month_to_add]
        elif output_frequency == 'month': # if True here, input_frequency=='year'
            output_dates = [year + month for year in self.dates for month in range(12)]
            output = repeat(array, 12, axis=1)
            if method == 'divide':
                output = around(divide(output, 12), decimals=3)
        if inplace == True:
            self.array = output
            self.dates = output_dates
            self.frequency = output_frequency
        else:
            return TimeArray(output, output_dates)
    
    def best_dates_mean(self, nb_best_dates):
        ''' Cette fonction renvoie le vecteur de la moyenne des 'nb_best_dates' 
        meilleures états de la matrice associée au TimeArray'''
        def mean_best_dates_row(row):
            nb_best = row[-1]
            if nb_best == 0 :
                return 0
            row = sort(row[:-1])
            row = row[-nb_best:]
            return row.sum()/nb_best
        
        array = self.array
        array_ = zeros((array.shape[0], array.shape[1]+1))
        array_[:,:-1] = array
        array_[:,-1] = nb_best_dates
        return apply_along_axis(mean_best_dates_row, axis=1, arr=array_)
    
    
    def add(self, other_time_array, inplace=False):
        array = self.array.copy()
        dates = self.dates
        other_dates = other_time_array.dates
        test_dates = [date for date in other_dates if date in dates]
        assert test_dates == other_dates
        assert array.shape[0] == other_time_array.array.shape[0]
        list_ix_col = [list(dates).index(date) for date in other_dates]
        array[:,list_ix_col] += other_time_array.array
        if inplace == True:
            self.array = array
        else:
            return TimeArray(array, dates)
        
    
    def __add__(self, other):
        assert isinstance(other, TimeArray)
        assert other.dates == self.dates
        sum_array = self.array + other.array
        return TimeArray(sum_array, self.dates)
        
        #more permissive :
        dates = self.dates
        other_dates = other.dates
        test_dates = [date for date in other_dates if date in dates]
        assert test_dates == other_dates
        array = self.array
        assert array.shape[0] == other.array.shape[0]
        list_ix_col = [list(dates).index(date) for date in other_dates]
        array[:,list_ix_col] += other.array
        return TimeArray(array, dates)
        
    def substract(self, other_time_array, inplace=False):
        array = self.array.copy()
        dates = self.dates
        other_dates = other_time_array.dates
        test_dates = [date for date in other_dates if date in dates]
        assert test_dates == other_dates
        assert array.shape[0] == other_time_array.array.shape[0]
        list_ix_col = [list(dates).index(date) for date in other_dates]
        array[:,list_ix_col] -= other_time_array.array
        if inplace == True:
            self.array = array
        else:
            return TimeArray(array, dates)