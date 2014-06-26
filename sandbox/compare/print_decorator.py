# -*- coding: utf-8 -*-
import sys


        
class print_decorator(object):
    def __init__(self, print_level):
        self._locals = {}
        self.print_level = print_level
    
    
    def __call__(self, func):
        name = func.__name__

        def call_func(*args):
            def tracer(frame, event, arg):
                if event=='return':
                    self._locals = frame.f_locals.copy()
                    
            sys.setprofile(tracer)
            try:
                # trace the function call
                res = func(*args)
            finally:
                # disable tracer and replace with old one
                sys.setprofile(None)
            for key, val in self._locals.iteritems():
                print "La variable intermédiaire {} vaut {}".format(key,val)
            return res
        
        def wrapper(*args, **kwargs):
            if name in self.print_level.keys() and self.print_level[name]:
                print "Pour la fonction {} \n    Les arguments appelés sont : ".format(name)
                for arg in args:
                    if hasattr(arg, '__name__'): 
                        to_print = arg.__name__
                    elif hasattr(arg, 'name'): 
                        to_print = arg.name
                    else:
                        to_print = arg
                    print "        -", to_print
                return call_func(*args,**kwargs)
            else:
                return func(*args, **kwargs)        
        return wrapper

print_level = {'calculate_coeff_proratisation': True}
intermediate_print = print_decorator(print_level)
    
if __name__ == '__main__':
        
    print_level = {'is_sum_lt_prod': True}
    test = print_decorator(print_level)
    
    @test
    def is_sum_lt_prod(a,b,c):
        sum = a+b+c
        prod = a*b*c
        return prod/sum
    
    print_level = {'is_sum_lt_prod': True}
    
    test = is_sum_lt_prod(13,7,4)
    print test