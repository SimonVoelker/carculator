from carculator import *
import os
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime

# Define variables
years = [2020, 2050]
battery_capacities = ['default', 40, 50, 60, 70, 80, 90, 100]  # 'default'
battery_production_countries = ["CN", "NO", "RER"]
methods = ["recipe", "ilcd"]
vehicle_type = "BEV"
vehicle_size = "Medium"

# Get current timestamp
datetime_timestamp = datetime.now()

# Load default car parameters
cip = CarInputParameters()
cip.static()
dcts, array = fill_xarray_from_input_parameters(cip)
array = array.interp(year=[2000, 2010, 2017, 2020, 2040, 2050],  kwargs={'fill_value': 'extrapolate'})

# Loop: years
interim_list = []

for year in years:

    for battery_capacity in battery_capacities:

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

        for battery_production_country in battery_production_countries:

            bc = {
                  'energy storage': {
                      'electric': {
                          'origin': battery_production_country
                      }
                  }
                 }

            for method in methods:

                ic = InventoryCalculation(cm.array, scope=scope, background_configuration=bc, method=method)

                results = ic.calculate_impacts()

                # To pandas dataframe
                impact_categories = ic.get_dict_impact_categories()[method]["midpoint"]

                for impact_category in impact_categories:

                    results_df = results.sel(impact_category=impact_category, size=vehicle_size,
                                             powertrain=vehicle_type, year=year, value=0)\
                        .to_dataframe('impact')

                    # Get number of rows
                    rows_results = results_df.shape[0]

                    # Rename columns
                    results_df.rename(columns={'size': 'vehicle_size'}, inplace=True)

                    # Delete columns
                    del results_df['value']

                    # Move columns
                    col = results_df.pop('year')
                    results_df.insert(0, col.name, col, allow_duplicates=True)

                    # Insert columns
                    results_df.insert(2, "carculator_category", results_df.index, allow_duplicates=True)
                    results_df.insert(1, "impact_method", [method] * rows_results, allow_duplicates=True)
                    results_df.insert(3, "impact_category_unit", ['???'] * rows_results, allow_duplicates=True)
                    results_df.insert(1, "Driving_range", [driving_range] * rows_results, allow_duplicates=True)
                    results_df.insert(1, "TtW_energy", [TtW_energy] * rows_results, allow_duplicates=True)
                    results_df.insert(1, "Battery_production_country", [battery_production_country] * rows_results, allow_duplicates=True)
                    results_df.insert(1, "Battery_cell_mass_share", [battery_cell_mass_share] * rows_results, allow_duplicates=True)
                    results_df.insert(1, "Battery_energy_density", [battery_cell_energy_density] * rows_results, allow_duplicates=True)
                    results_df.insert(1, "Battery_mass", [energy_battery_mass] * rows_results, allow_duplicates=True)
                    results_df.insert(1, "Battery_capacity", [electric_energy_stored] * rows_results, allow_duplicates=True)

                    # Add a row containing units
                    index_old = results_df.index
                    results_df.loc["unit"] = ['-', 'kWh', 'kg', 'kWh/kg', '%', '-', 'kWh/km', 'km', '-', '-', '-', '-', '-', '-', '-']
                    index_new = index_old.insert(0, "unit")
                    results_df = results_df.reindex(index_new)

                    # Print result
                    # print(results_df.to_string(index=False))

                    # Write to csv
                    impact_category_short = ''.join(w[0].upper() for w in impact_category.split())
                    folder_timestamp = datetime_timestamp.strftime("%Y%m%d-%H%M%S")
                    path = '_EXPORT\\' + folder_timestamp + '\\'
                    if not os.path.exists(path):
                        os.makedirs(path)
                    filename = str(year) + '_' + method + '_' + impact_category_short + '_' + vehicle_type + '_' + vehicle_size +\
                               '_BattCapacity_' + str(int(round(electric_energy_stored, 0))) + '_kWh_BattCountry_' + str(battery_production_country)
                    results_df.to_csv(path + filename + '.csv', index=False, header=True)
