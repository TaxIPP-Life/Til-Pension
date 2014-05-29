# -*- coding: utf-8 -*-
from datetime import date as classic_date

class DateTil(object):
    
    def __init__(self, date):
        if isinstance(date, DateTil):
            self.datetime = date.datetime
            self.year = date.year
            self.liam = date.liam
        elif isinstance(date, classic_date):
            self.datetime = date
            self.year = date.year
            self.liam = 100*date.year + date.month
        elif len(str(date)) == 4:
            self.year = date
            self.datetime = classic_date(date, 1,1)
            self.liam = 100*date + 1
        elif len(str(date)) == 6:
            self.liam = date
            self.year = date//100
            self.datetime = classic_date(date // 100, date % 100, 1)
        else:
            raise('Format de la date invalide')
