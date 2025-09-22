import json
import os
import sys


def poorly_formatted(a, b, c):
    result = a + b + c
    if result > 0:
        print("positive")
    else:
        print("negative")
    return result
