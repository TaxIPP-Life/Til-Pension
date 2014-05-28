# -*- coding: utf-8 -*-
from datetime import date

class DateTil(object):
    def __init__(self, datesim):
        self.liam = None
        self.datetime = None
        self.year = None
        self.set_attributes(datesim)
        
    def set_attributes(self, datesim):
        if isinstance(datesim, date):
            self.datetime = datesim
            self.year = datesim.year
            self.liam = 100*datesim.year + datesim.month
        elif len(str(datesim)) == 4:
            self.year = datesim
            self.datetime = date(datesim, 1,1)
            self.liam = 100*datesim + 1
        elif len(str(datesim)) == 6:
            self.liam = datesim
            self.year = datesim//100
            self.datetime = date(datesim // 100, datesim % 100, 1)
        else:
            raise('Format de la date invalide')
