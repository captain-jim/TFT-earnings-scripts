# Requires 'requests' and 'openpyxl' packages - install these with pip. 
# Script makes use of concurrent threading to increase data retrieval efficiency - default value is 4 which should be enough for almost any circumstance. 
# Run the script with: python {script_name.py} {farm_ID} {month.year} for single month or {farm_ID} {month.year}-{month.year} for a range.
# month can be input as one or two digits, year can be input as two or four digits.
# Example call - python farm_earnings_xlsx-output 1234 01.23-12.23
# xlsx file will be output to the directory where the script is located. Each month will create its own sheet within the workbook.
# It should be noted that the uptime numbers for Feburary 2023 are broken server-side and will result in those cells being formatted in scientific notation.
# The script is only able to access data tied to alpha.minting.tfchain.grid.tf which means any bonus payments will not be included in the output.

import sys
import requests
from datetime import datetime, timedelta
from openpyxl import Workbook
from concurrent.futures import ThreadPoolExecutor, as_completed

def parse_month_year(month_year_str):
    parts = month_year_str.split('.')
    if len(parts) == 2:
        month_str, year_str = parts
        month = int(month_str)
        
        if len(year_str) == 2:
            year = int(year_str) + 2000
        elif len(year_str) == 4:
            year = int(year_str)
        else:
            raise ValueError("Invalid year format. Please provide the year in two or four digits.")
        
        if not 1 <= month <= 12:
            raise ValueError("Invalid month. Please provide a month between 1 and 12.")
        
        current_year = datetime.now().year
        if not 2015 <= year <= current_year:
            raise ValueError(f"Invalid year. Please provide a year between 2015 and {current_year}.")
        
        return month, year
    else:
        raise ValueError("Invalid date format. Please provide the date in month.year format.")

def format_float(num, precision):
    return round(float(num), precision)

def fetch_farm_nodes(farm_id):
    url = f'https://gridproxy.grid.tf/nodes?farm_ids={farm_id}'
    response = requests.get(url)
    return [node['nodeId'] for node in response.json()]

def fetch_node_minting_history(session, node_id, month, year):
    url = f'https://alpha.minting.tfchain.grid.tf/api/v1/node/{node_id}'
    response = session.get(url)
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
                uptime_percentage = (uptime_days / 30.45) * 100
                data.append([
                    minting_info['node_id'],
                    format_float(minting_info['reward']['tft'] / 1e7, 7),
                    30.45,
                    format_float(uptime_days, 2),
                    format_float(uptime_percentage, 2),
                    item['hash']
                ])
    return data

def create_workbook(farm_id, dates):
    wb = Workbook()
    wb.remove(wb.active)

    session = requests.Session()
    with ThreadPoolExecutor(max_workers=4) as executor:
        for date_arg in dates:
            month, year = parse_month_year(date_arg)
            ws = wb.create_sheet(title=f"{month:02d}.{year}")
            ws.append(['Node ID', 'TFT Earned', 'Total Period (Days)', 'Uptime (Days)', 'Uptime (%)', 'Receipt Hash'])
            
            node_ids = fetch_farm_nodes(farm_id)
            futures = [executor.submit(fetch_node_minting_history, session, node_id, month, year) for node_id in node_ids]
            all_data = []
            for future in as_completed(futures):
                data = future.result()
                all_data.extend(data)

            all_data.sort(key=lambda x: x[0])
            
            for row in all_data:
                ws.append(row)
    return wb

if len(sys.argv) < 3:
    print("Usage: python script.py <farm_id> <month.year> or <farm_id> <start_month.year-end_month.year>")
    sys.exit(1)

farm_id = sys.argv[1]
dates = sys.argv[2:]

try:
    if '-' in dates[0]:
        start_date, end_date = dates[0].split('-')
        start_month, start_year = parse_month_year(start_date)
        end_month, end_year = parse_month_year(end_date)
        dates = []
        while start_year < end_year or (start_year == end_year and start_month <= end_month):
            dates.append(f"{start_month:02d}.{start_year}")
            start_month += 1
            if start_month > 12:
                start_month = 1
                start_year += 1
        wb = create_workbook(farm_id, dates)
        filename = f"{farm_id}_farm_earnings_{dates[0]}_to_{dates[-1]}.xlsx"
    else:
        wb = create_workbook(farm_id, [dates[0]])
        filename = f"{farm_id}_farm_earnings_{dates[0]}.xlsx"

    wb.save(filename)
    print(f"Workbook saved as {filename}")
except Exception as e:
    print(f"An error occurred: {e}")
