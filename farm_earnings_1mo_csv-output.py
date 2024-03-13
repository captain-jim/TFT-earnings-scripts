# Requires 'requests' package - install this with pip.
# Run the script with: python {script_name.py} {farm_ID} {month.year}
# month can be input as one or two digits, year can be input as two or four digits.
# Example call - python farm_earnings_1mo_csv-output.py 1234 01.23
# csv file will be output to the directory where the script is located.
# It should be noted that the uptime numbers for Feburary 2023 are broken server-side and will result in those cells being formatted in scientific notation.
# The script is only able to access data tied to alpha.minting.tfchain.grid.tf which means any bonus payments will not be included in the output.

import sys
import requests
import csv
from datetime import datetime, timedelta

def format_float(num, precision=7):
    if precision == 2:
        return "{:.2f}".format(num)
    else:
        return "{:.7f}".format(num)

def fetch_farm_nodes(farm_id):
    url = f'https://gridproxy.grid.tf/nodes?farm_ids={farm_id}&size=1000'
    response = requests.get(url)
    nodes = response.json()
    return [node['nodeId'] for node in nodes]

def fetch_node_minting_history(node_id, month, year):
    url = f'https://alpha.minting.tfchain.grid.tf/api/v1/node/{node_id}'
    response = requests.get(url)
    receipts = response.json()
    data = []
    for item in receipts:
        if 'Minting' in item['receipt']:
            minting_info = item['receipt']['Minting']
            period_start_unix = minting_info['period']['start']
            start_date = datetime.fromtimestamp(period_start_unix)
            
            adjusted_start_date = start_date + timedelta(days=2)
            
            if adjusted_start_date.year == year and adjusted_start_date.month == month:
                uptime_days = minting_info['measured_uptime'] / (24 * 3600)
                uptime_percentage = (minting_info['measured_uptime'] / (24 * 3600 * 30.45)) * 100
                
                data.append([
                    minting_info['node_id'],
                    format_float(minting_info['reward']['tft'] / 1e7),
                    30.45,
                    format_float(uptime_days, precision=2),
                    format_float(uptime_percentage, precision=2),
                    item['hash'],
                ])
    return data

def process_farm(farm_id, month, year):
    node_ids = fetch_farm_nodes(farm_id)
    all_data = []
    for node_id in node_ids:
        node_data = fetch_node_minting_history(node_id, month, year)
        all_data.extend(node_data)
    
    csv_filename = f"{farm_id}_farm_earnings_{month:02d}.{year}.csv"
    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Node ID', 'TFT Earned', 'Total Period (Days)', 'Uptime (Days)', 'Uptime (%)', 'Receipt Hash'])
        writer.writerows(all_data)
    
    print(f"Data for farm {farm_id} for {month:02d}/{year} has been written to {csv_filename}")

if len(sys.argv) < 3:
    print("Usage: python script.py <farm_id> <month.year>")
    sys.exit(1)

farm_id = sys.argv[1]
month_year = sys.argv[2].split('.')
month = int(month_year[0])
year_input = month_year[1]

if len(year_input) == 2:
    year = int(year_input) + 2000
elif len(year_input) == 4:
    year = int(year_input)
else:
    print("Invalid year format. Please provide the year in two or four digits.")
    sys.exit(1)
    
if not 1 <= month <= 12:
    print("Invalid month. Please provide a month between 1 and 12.")
    sys.exit(1)

current_year = datetime.now().year
if not 2015 <= year <= current_year:
    print(f"Invalid year. Please provide a year between 2015 and {current_year}.")
    sys.exit(1)

process_farm(farm_id, month, year)

