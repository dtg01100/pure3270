import sys,os
import re,json

def poorly_formatted_function(x,y,z):
    """This function has poor formatting on purpose."""
    result=x+y+z
    if result>10:
        print("Result is big")
    else:print("Result is small")
    
    return result


class PoorlyFormattedClass:
    def __init__(self,value):
        self.value=value
    def get_double(self ):
        return self.value*2