"""
SF133 Data Processing Code Modules
==================================

Processing pipeline modules in execution order:
1. download_sf133_data.py - Download Excel files from MAX.gov
2. parse_sf133_raw_data.py - Parse Raw Data sheets from Excel files  
3. sf133_processor.py - Main processor with integrity tests
4. generate_summary.py - Generate website data files
5. serve.py - Development web server
"""