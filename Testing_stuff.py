from carculator import *
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

cip = CarInputParameters()

cip.static()

dcts, array = fill_xarray_from_input_parameters(cip)

array = array.interp(year=[2000, 2010, 2017, 2020, 2040, 2050],  kwargs={'fill_value': 'extrapolate'})
list(array.year.values)

cm = CarModel(array, cycle='WLTC')
#cm.set_all()

scope = {
    "size": ["Medium"],
    "powertrain": ["BEV", "ICEV-d"],
    "year": [2020]
}

bc = {
      'energy storage': {
          'electric': {
              'origin': 'CN'
          }
      }
     }

ic = InventoryCalculation(cm.array, scope = scope, background_configuration = bc)

print(ic.categories_midpoint)

results = ic.calculate_impacts()

results.sel(impact_category='particulate matter formation', size='Medium', value=0)\
    .to_dataframe('impact')\
    .unstack(level=2)['impact']\
    .plot(kind='bar',
                stacked=True,
         figsize=(15,10))
plt.ylabel('kg CO2-eq./vkm')
plt.show()

results_PMF = results.sel(impact_category='particulate matter formation', size='Medium', powertrain='BEV', year=[2020], value=0)\
.to_dataframe('impact')
print(results_PMF)