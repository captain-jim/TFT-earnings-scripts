# TFT-earnings-scripts
Python scripts tailored for Threefold blockchain farming data analysis. 

The scripts fetch earnings data from a Threefold grid, organizing the information into either CSV or XLSX formats. Designed with user flexibility in mind, these scripts support single month queries or range based data retrieval, outputting well-structured and easily navigable reports.

farm_earnings_xlsx-output:
This Python script is designed to extract and organize node performance and earnings data from the Threefold grid into a well-structured Excel workbook broken into multiple sheets, one per month. It supports data extraction for either a single month or a specified range of months. The output is sorted by node ID in ascending order, and data is presented with the standardized period duration while precisely tracking TFT earnings and uptime statistics. The use of concurrent threads optimizes the data retrieval process, ensuring efficient execution for farms with numerous nodes.
Requires Python packages 'requests' and 'openpyxl' - these can be installed with pip.
