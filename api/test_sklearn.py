import sys, traceback
try:
    import numpy as np
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import PolynomialFeatures
    print('OK.')
except Exception as e:
    with open('err.txt', 'w') as f:
        traceback.print_exc(file=f)
