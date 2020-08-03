from carculator import *
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Define variables
method = "recipe"
vehicle_type = "BEV"
vehicle_size = "Medium"
year = 2020
battery_production_country = "CN"
battery_capacity = 'default'  # 70  # 'default'

# Load default car parameters
cip = CarInputParameters()
cip.static()
dcts, array = fill_xarray_from_input_parameters(cip)
array = array.interp(year=[2000, 2010, 2017, 2020, 2040, 2050],  kwargs={'fill_value': 'extrapolate'})

# Load CarModel without modifications
cm = CarModel(array, cycle='WLTC')
# cm.set_all()

# Load some default values from CarModel
energy_battery_mass_default = cm.array.sel(parameter="energy battery mass", powertrain=vehicle_type,
                                           year=year, size=vehicle_size).values[0]  # kg
battery_cell_energy_density_default = cm.array.sel(parameter="battery cell energy density", powertrain=vehicle_type,
                                                   year=year, size=vehicle_size).values[0]  # kWh/kg
battery_cell_mass_share_default = cm.array.sel(parameter="battery cell mass share", powertrain=vehicle_type,
                                               year=year, size=vehicle_size).values[0]  # -

# Modify battery capacity
'''energy_battery_mass = electric_energy_stored / (battery_cell_mass_share * battery_cell_energy_density)'''
if battery_capacity != 'default':
    new_battery_mass = battery_capacity / (battery_cell_mass_share_default * battery_cell_energy_density_default)  # kg

    dict_param = {('Energy Storage', vehicle_type, vehicle_size, 'energy battery mass', 'none'): {
        (year, 'loc'): new_battery_mass  # kg
        }
    }
    modify_xarray_from_custom_parameters(dict_param, array)

# Set up CarModel with modifications
cm.set_all()

# Get vehicle parameters
energy_battery_mass = cm.array.sel(parameter="energy battery mass", powertrain=vehicle_type,
                                   year=year, size=vehicle_size).values[0]  # kg
battery_cell_energy_density = cm.array.sel(parameter="battery cell energy density", powertrain=vehicle_type,
                                           year=year, size=vehicle_size).values[0]  # kWh/kg
battery_cell_mass_share = cm.array.sel(parameter="battery cell mass share", powertrain=vehicle_type,
                                       year=year, size=vehicle_size).values[0]  # -
TtW_energy = cm.array.sel(parameter="TtW energy", powertrain=vehicle_type,
                          year=year, size=vehicle_size).values[0] / 3600  # kWh/km
TtW_efficiency = cm.array.sel(parameter="TtW efficiency", powertrain=vehicle_type,
                              year=year, size=vehicle_size).values[0]  # -
driving_range = cm.array.sel(parameter="range", powertrain=vehicle_type,
                             year=year, size=vehicle_size).values[0]  # km
electric_energy_stored = cm.array.sel(parameter="electric energy stored", powertrain=vehicle_type,
                                      year=year, size=vehicle_size).values[0]  # kWh

# Calculate environmental impacts
scope = {
    "size": [vehicle_size],
    "powertrain": [vehicle_type],
    "year": [year]
}

bc = {
      'energy storage': {
          'electric': {
              'origin': battery_production_country
          }
      }
     }

ic = InventoryCalculation(cm.array, scope=scope, background_configuration=bc, method=method)

results = ic.calculate_impacts()

'''
results.sel(impact_category='particulate matter formation', size=vehicle_size, value=0)\
    .to_dataframe('impact')\
    .unstack(level=2)['impact']\
    .plot(kind='bar',
                stacked=True,
         figsize=(15,10))
plt.ylabel('kg CO2-eq./vkm')
plt.show()
'''

results_PMF = results.sel(impact_category='particulate matter formation', size=vehicle_size,
                          powertrain=vehicle_type, year=year, value=0)\
    .to_dataframe('impact')

# Get number of rows
rows_results = results_PMF.shape[0]

# Rename columns
results_PMF.rename(columns={'size': 'vehicle_size'}, inplace=True)

# Delete columns
del results_PMF['value']

# Move columns
col = results_PMF.pop('year')
results_PMF.insert(0, col.name, col, allow_duplicates=True)

# Insert columns
results_PMF.insert(2, "carculator_category", results_PMF.index, allow_duplicates=True)
results_PMF.insert(1, "impact_method", [method] * rows_results, allow_duplicates=True)
results_PMF.insert(3, "impact_category_unit", ['???'] * rows_results, allow_duplicates=True)
results_PMF.insert(1, "Driving_range", [driving_range] * rows_results, allow_duplicates=True)
results_PMF.insert(1, "TtW_energy", [TtW_energy] * rows_results, allow_duplicates=True)
results_PMF.insert(1, "Battery_production_country", [battery_production_country] * rows_results, allow_duplicates=True)
results_PMF.insert(1, "Battery_cell_mass_share", [battery_cell_mass_share] * rows_results,
                   allow_duplicates=True)
results_PMF.insert(1, "Battery_energy_density", [battery_cell_energy_density] * rows_results,
                   allow_duplicates=True)
results_PMF.insert(1, "Battery_mass", [energy_battery_mass] * rows_results, allow_duplicates=True)
results_PMF.insert(1, "Battery_capacity", [electric_energy_stored] * rows_results, allow_duplicates=True)

# Add a row containing units
index_old = results_PMF.index
results_PMF.loc["unit"] = ['-', 'kWh', 'kg', 'kWh/kg', '%', '-', 'kWh/km', 'km', '-', '-', '-', '-', '-', '-', '-']
index_new = index_old.insert(0, "unit")
results_PMF = results_PMF.reindex(index_new)

# Print result
print(results_PMF.to_string(index=False))
