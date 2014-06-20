# -*- coding: utf-8 -*-
from pandas import DataFrame
from numpy import array, tile, divide, around, in1d, repeat, sort, apply_along_axis, zeros, minimum, subtract

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
    
    def __repr__(self):
        return self.array.__repr__() + self.dates.__repr__() 
    
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
        if inplace:
            self.array = array[:,array_dates]
            self.dates = dates
        else:
            return TimeArray(array[:,array_dates], dates, self.name)
    
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

    def __add__(self, other):
        initial_dates = self.dates
        array = self.array
        other_dates = other.dates
        if initial_dates == other_dates:
            return TimeArray(array + other.array, initial_dates)
        
        assert array.shape[0] == other.array.shape[0] # Même nombre de lignes
        other_in_initial = [date for date in other_dates if date in initial_dates] 
        initial_in_other = [date for date in initial_dates if date in other_dates]
        assert other_in_initial == other_dates or initial_in_other == initial_dates #les dates de l'une sont un sous ensemble de l'autre
        if other_in_initial == other_dates:
            sum_array = array.copy()
            list_ix_col = [list(initial_dates).index(date) for date in other_dates]
            sum_array[:,list_ix_col] += other.array
            dates = initial_dates
        if initial_in_other == initial_dates:
            sum_array = other.array.copy()
            list_ix_col = [list(other_dates).index(date) for date in initial_dates]
            sum_array[:,list_ix_col] += array
            dates = other_dates
        return TimeArray(sum_array, dates)
        
    def subtract(self, other, inplace=False):
        initial_dates = self.dates
        array = self.array
        other_dates = other.dates
        if initial_dates == other_dates:
            return TimeArray(array - other.array, initial_dates)
        
        assert array.shape[0] == other.array.shape[0] # Même nombre de lignes
        other_in_initial = [date for date in other_dates if date in initial_dates] 
        initial_in_other = [date for date in initial_dates if date in other_dates]
        assert other_in_initial == other_dates or initial_in_other == initial_dates #les dates de l'une sont un sous ensemble de l'autre
        if other_in_initial == other_dates:
            sub_array = array.copy()
            list_ix_col = [list(initial_dates).index(date) for date in other_dates]
            sub_array[:,list_ix_col] = subtract(sub_array[:,list_ix_col], other.array)
            dates = initial_dates
        if initial_in_other == initial_dates:
            sub_array = other.array.copy()
            list_ix_col = [list(other_dates).index(date) for date in initial_dates]
            sub_array[:,list_ix_col] = subtract(sub_array[:,list_ix_col], array)
            dates = other_dates
        if inplace == True:
            self.array = sub_array
        else:
            return TimeArray(array, dates)
        
    def ceil(self, plaf=None, inplace=False):
        array = self.array.copy()
        if plaf is not None:
            array = minimum(array, plaf)
        if inplace == True:
            self.array = array
        else:
            return TimeArray(array, self.dates)
        
    def idx_last_time_in(self, in_what):
        ''' Retourne les coordonnées de la dernière fois que l'individu a été dans l'état in_what :
        Il s'agit en fait de deux listes de même taille :
        - la première renvoie les nméros des lignes (qui s'apparentent aux ident individuels) des personnes ayant au
        moins eu un état in_what au cours de leur vie
        - la seconde renvoit les numéros de colonnes (qui s'apparentent aux années) permetant d'identifier la dernière
        année où l'individu est dans l'état in_what'''       
        selection = self.isin(in_what).array
        
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
        last_fp = zeros(self.array.shape[0])
        last_fp[last_fp_idx[0]] = self.array[last_fp_idx]
        return last_fp
       
    def select_code_after_period(self, code1, code2):
        ''' returns values value in code2 if the period before was in code1
        usefull for unemployment
        Rq : don't consider True in t=0'''
        array = self.array
        output = zeros(array.shape)
#         output[:,0] = (array[:,0] == code2)
        previous = in1d(array[:,:-1], [code1, code2]).reshape(array[:,:-1].shape)
        in_code2 = (array[:,1:] == code2)
        selected = previous*in_code2
        output[:,1:] = selected
        return output
