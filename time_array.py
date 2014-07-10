# -*- coding: utf-8 -*-
from pandas import DataFrame
import numpy as np
from numpy import ndarray, array, tile, divide, around, in1d, repeat, sort, apply_along_axis, zeros, minimum, subtract

def determine_frequency(dates):
    if (array(dates) % 100 == 1).all() :
        frequency = 'year' 
    else: 
        frequency = 'month' 
    return frequency

class TimeArray(np.ndarray):
    ''' numpy array with dates '''
    def __new__(cls, input_array, dates, name=None):
        obj = np.asarray(input_array).view(cls)
        obj.dates = dates
        obj.frequency = determine_frequency(dates)
        obj.name = name
        return obj

    def __array_finalize__(self, obj):
        # see InfoArray.__array_finalize__ for comments
        if obj is None: return
        self.dates = getattr(obj, 'dates', None)
        self.frequency = getattr(obj, 'frequency', None)
        self.name = getattr(obj, 'name', None)
        
    def __array_wrap__(self, out_arr, context=None):
        if not isinstance(out_arr, TimeArray):
            assert out_arr.shape == self.shape
            assert isinstance(out_arr, np.ndarray) #could be extend to pandas, but we don't want pandas    
        if isinstance(out_arr, TimeArray):
            assert out_arr.shape == self.shape
            assert out_arr.dates == self.dates
            assert out_arr.frequency == self.frequency
        # then just call the parent
        return np.ndarray.__array_wrap__(self, out_arr, context)
    
#     def __repr__(self):
#         return self.__repr__() + self.dates.__repr__() 
#     
#     def copy(self):
#         return TimeArray(self.copy(), self.dates)
#     
    def isin(self, code):
        array_selection = in1d(self.copy(), code).reshape(self.shape)
        return TimeArray(array_selection, self.dates)
         
#     def sum(self, axis=1):
#         ''' Cette fonction renvoie un vecteur (de longueur le nb de ligne de l'array)
#         donnant :
#         - axis = 1 : la somme des colonnes de l'array
#         - axis = 0 : la somme des lignes de l'array '''
#         return self.sum(axis=axis)
    
    def selected_dates(self, first=None, last=None, date_type='year', inplace=False):
        ''' La table d'input dont les colonnes sont des dates est renvoyées amputée 
            des années postérieures à first (first incluse) 
            et antérieures strictement à last 
            date_type est month ou year
            '''
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
        if inplace:
            self = self[:,array_dates]
            self.dates = dates
        else:
            return TimeArray(self[:,array_dates], dates, self.name)
    
    def translate_frequency(self, output_frequency='month', method=None, inplace=False):
        '''method should eventually control how to switch from month based table to year based table
            so far we assume year is True if January is True 
            idea : format_table as an argument instead of testing with isinstance
            '''
        input_frequency = self.frequency
        if input_frequency == output_frequency:
            if inplace == True:
                return 'rien'
            else:
                return TimeArray(self, self.dates)
        if output_frequency == 'year': # if True here, input_frequency=='month'
            assert len(self.dates) % 12 == 0 #TODO: to remove eventually
            nb_years = len(self.dates) // 12
            output_dates = [date for date in self.dates if date % 100 == 1]
            output_dates_ix = [self.dates.index(output_date) for output_date in output_dates]
            #here we could do more complex
            if method is None: #first month of each year
                output = self[:, output_dates_ix]
            if method is 'sum':
                output = self[:, output_dates_ix]
                for month in range(1,12):
                    month_to_add = [year*12 + month for year in xrange(nb_years)]
                    output += self[:, month_to_add]
        elif output_frequency == 'month': # if True here, input_frequency=='year'
            output_dates = [year + month for year in self.dates for month in range(12)]
            output = repeat(self, 12, axis=1)
            if method == 'divide':
                output = around(divide(output, 12), decimals=3)
        if inplace == True:
            self = output
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
        
        array_ = zeros((self.shape[0], self.shape[1]+1))
        array_[:,:-1] = self
        array_[:,-1] = nb_best_dates
        return apply_along_axis(mean_best_dates_row, axis=1, arr=array_)

#     def __add__(self, other):
#         initial_dates = self.dates
#         array = self
#         other_dates = other.dates
#         if initial_dates == other_dates:
#             return TimeArray(self + other, initial_dates)
#         
#         assert self.shape[0] == other.shape[0] # Même nombre de lignes
#         other_in_initial = [date for date in other_dates if date in initial_dates] 
#         initial_in_other = [date for date in initial_dates if date in other_dates]
#         assert other_in_initial == other_dates or initial_in_other == initial_dates #les dates de l'une sont un sous ensemble de l'autre
#         if other_in_initial == other_dates:
#             sum_array = self.copy()
#             list_ix_col = [list(initial_dates).index(date) for date in other_dates]
#             sum_array[:,list_ix_col] += other
#             dates = initial_dates
#         if initial_in_other == initial_dates:
#             sum_array = other.copy()
#             list_ix_col = [list(other_dates).index(date) for date in initial_dates]
#             sum_array[:,list_ix_col] += self
#             dates = other_dates
#         return TimeArray(sum_array, dates)
#         
#     def subtract(self, other, inplace=False):
#         initial_dates = self.dates
#         other_dates = other.dates
#         if initial_dates == other_dates:
#             return TimeArray(self - other, initial_dates)
#         
#         assert self.shape[0] == other.shape[0] # Même nombre de lignes
#         other_in_initial = [date for date in other_dates if date in initial_dates] 
#         initial_in_other = [date for date in initial_dates if date in other_dates]
#         assert other_in_initial == other_dates or initial_in_other == initial_dates #les dates de l'une sont un sous ensemble de l'autre
#         if other_in_initial == other_dates:
#             sub_array = self.copy()
#             list_ix_col = [list(initial_dates).index(date) for date in other_dates]
#             sub_array[:,list_ix_col] = subtract(sub_array[:,list_ix_col], other)
#             dates = initial_dates
#         if initial_in_other == initial_dates:
#             sub_array = other.copy()
#             list_ix_col = [list(other_dates).index(date) for date in initial_dates]
#             sub_array[:,list_ix_col] = subtract(sub_array[:,list_ix_col], self)
#             dates = other_dates
#         if inplace == True:
#             self = sub_array
#         else:
#             return TimeArray(array, dates)
#         
#     def ceil(self, plaf=None, inplace=False):
#         array = self.copy()
#         if plaf is not None:
#             array = minimum(array, plaf)
#         if inplace == True:
#             self = array
#         else:
#             return TimeArray(array, self.dates)
        
    def idx_last_time_in(self, in_what):
        ''' Retourne les coordonnées de la dernière fois que l'individu a été dans l'état in_what :
        Il s'agit en fait de deux listes de même taille :
        - la première renvoie les nméros des lignes (qui s'apparentent aux ident individuels) des personnes ayant au
        moins eu un état in_what au cours de leur vie
        - la seconde renvoit les numéros de colonnes (qui s'apparentent aux années) permetant d'identifier la dernière
        année où l'individu est dans l'état in_what'''       
        selection = self.isin(in_what)
        
        nrows = selection.shape[0]
        output = zeros(nrows)
        for date in reversed(range(len(self.dates))):
            cond = selection[:,date] != 0
            cond = cond & (output == 0)
            output[cond] = date
            
#             # some ideas to optimize the calculation
#         output = selection.argmax(axis=1) 
#         obvious_case1 = (selection.max(axis=1) == 0) | (selection.max(axis=1) == min(self.code_regime)) #on a directement la valeur 
                                                                                                            # et avec argmac l'indice
#         obvious_case2 = selection[:,-1] != 0 # on sait que c'est le dernier
#         output[obvious_case2] = len_dates - 1 #-1 because it's the index of last column

#         not_yet_selected = (~obvious_case1) & (~obvious_case2)
#         output[not_yet_selected] = -1 # si on réduit, on va peut-être plus vite
#         subset = selection[not_yet_selected,:-1] #we know from obvious case2 condition that there are zero on last column
#         for date in reversed(range(len_dates-1)):
#             cond = subset[:,date] != 0
#             output[not_yet_selected[cond]] = date     

        selected_output = output[output != 0].astype(int)
        selected_rows = array(range(nrows))[output != 0].astype(int)
        return selected_rows.tolist(), selected_output.tolist()
    
    def last_time_in(self, in_what):
        ''' Return les coordonnées de la dernière fois que l'individu a été dans l'état in_what '''       
        last_fp_idx = self.idx_last_time_in(in_what)
        last_fp = zeros(self.shape[0])
        last_fp[last_fp_idx[0]] = self[last_fp_idx]
        return last_fp
       
    def select_code_after_period(self, code1, code2):
        ''' returns values value in code2 if the period before was in code1
        usefull for unemployment
        Rq : don't consider True in t=0'''
        output = zeros(self.shape)
#         output[:,0] = (self[:,0] == code2)
        previous = in1d(self[:,:-1], [code1, code2]).reshape(self[:,:-1].shape)
        in_code2 = (self[:,1:] == code2)
        selected = previous*in_code2
        output[:,1:] = selected
        return output
