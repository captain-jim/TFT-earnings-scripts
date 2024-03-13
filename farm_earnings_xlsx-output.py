# Requires 'requests' and 'openpyxl' packages - install these with pip. 
# Script makes use of concurrent threading to increase data retrieval efficiency - default value is 4 which should be enough for almost any circumstance. 
# Run the script with: python {script_name.py} {farm_ID} {month.year} for single month or {farm_ID} {month.year}-{month.year} for a range.
# month can be input as one or two digits, year can be input as two or four digits.
# Example call - python farm_earnings_xlsx-output.py 1234 01.23-12.23
# xlsx file will be output to the directory where the script is located. Each month will create its own sheet within the workbook.
# It should be noted that the uptime numbers for Feburary 2023 are broken server-side and will result in those cells being formatted in scientific notation.
# The script is only able to access data tied to alpha.minting.tfchain.grid.tf which means any bonus payments will not be included in the output.

import sys
import requests
from datetime import datetime, timedelta
from openpyxl import Workbook
from concurrent.futures import ThreadPoolExecutor, as_completed

def parse_month_year(month_year_str):
    month, year = month_year_str.split('.')
    month = int(month)
    year = int(year) + 2000 if len(year) == 2 else int(year)
    if not 1 <= month <= 12:
        raise ValueError("Month must be between 1 and 12")
    if not 2015 <= year:
        raise ValueError("Year must be 2015 or later")
    return month, year

def get_months_range(start, end):
    start_month, start_year = parse_month_year(start)
    end_month, end_year = parse_month_year(end)
    current_date = datetime(start_year, start_month, 1)
    end_date = datetime(end_year, end_month, 1)

    months = []
    while current_date <= end_date:
        months.append(f"{current_date.month:02d}.{current_date.year}")
        next_month = (current_date.month % 12) + 1
        next_year = current_date.year + (current_date.month + 1) // 13
        current_date = datetime(next_year, next_month, 1)
    return months

def format_float(num, precision=7):
    return f"{num:.{precision}f}" if precision == 7 else f"{num:.2f}"

def fetch_farm_nodes(farm_id):
    url = f'https://gridproxy.grid.tf/nodes?farm_ids={farm_id}&size=1000'
    response = requests.get(url)
    if response.status_code == 200:
        return [node['nodeId'] for node in response.json()]
    else:
        raise ValueError(f"Failed to fetch nodes for farm ID {farm_id}.")

def fetch_node_minting_history(session, node_id, month, year):
    url = f'https://alpha.minting.tfchain.grid.tf/api/v1/node/{node_id}'
    response = session.get(url)
    if response.status_code == 200:
        receipts = response.json()
        data = []
        for item in receipts:
            if 'Minting' in item['receipt']:
                minting_info = item['receipt']['Minting']
                period_start_unix = minting_info['period']['start']
                start_date = datetime.fromtimestamp(period_start_unix)
                adjusted_start_date = start_date + timedelta(days=2)
                if adjusted_start_date.year == year and adjusted_start_date.month == month:
                    uptime_days = format_float(minting_info['measured_uptime'] / (24 * 3600), 2)
                    uptime_percentage = format_float((minting_info['measured_uptime'] / (24 * 3600 * 30.45)) * 100, 2)
                    data.append([
                        minting_info['node_id'],
                        format_float(minting_info['reward']['tft'] / 1e7),
                        30.45,
                        uptime_days,
                        uptime_percentage,
                        item['hash']
                    ])
        return data
    else:
        print(f"Failed to fetch minting history for node {node_id}")
        return []

def create_workbook(farm_id, dates):
    wb = Workbook()
    wb.remove(wb.active)

    session = requests.Session()
    with ThreadPoolExecutor(max_workers=4) as executor:
        for date_str in dates:
            month, year = parse_month_year(date_str)
            ws = wb.create_sheet(title=f"{month:02d}.{year}")
            ws.append(['Node ID', 'TFT Earned', 'Total Period (Days)', 'Uptime (Days)', 'Uptime (%)', 'Receipt Hash'])

            node_ids = fetch_farm_nodes(farm_id)
            futures = [executor.submit(fetch_node_minting_history, session, node_id, month, year) for node_id in node_ids]
            all_data = []
            for future in as_completed(futures):
                all_data.extend(future.result())

            # Sort data by Node ID before appending
            all_data.sort(key=lambda x: x[0])
            for row in all_data:
                ws.append(row)
    return wb

if len(sys.argv) < 3:
    print("Usage: python script.py <farm_id> <month.year> or <farm_id> <start_month.year-end_month.year>")
    sys.exit(1)

farm_id = sys.argv[1]
date_input = sys.argv[2]
dates = get_months_range(date_input.split('-')[0], date_input.split('-')[-1]) if '-' in date_input else [date_input]

wb = create_workbook(farm_id, dates)
filename = f"{farm_id}_farm_earnings_{dates[0]}{'_to_' + dates[-1] if len(dates) > 1 else ''}.xlsx"
wb.save(filename)
print(f"Workbook saved as {filename}")

