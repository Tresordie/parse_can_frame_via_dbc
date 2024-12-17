# parse_can_frame_via_dbc
parse SCUD CAN data log according to dbc file

# Notes
1. generally SCUD used 2 types of application to capture CAN log
    - CANTest
    - CANas
2. SCUD captured CAN logs used different encoded csv file
    - GB2312 code
    - UTF8 code
3. SCUD captured CAN logs sometimes used different csv title row(head row)

# Usage
1. please install library of python(pandas, chardet, tqdm, cantools)
    pip install pandas
    pip install chardet
    pip install tqdm
    pip install cantools

2. make sure your .dbc file in the file path you specified

3. make sure CAN log csv files in the file path you specified

4. confirm with SCUD that what kind of CAN application tool used for CAN log capture(CANTest? CANas?)

5. sometimes SCUD split CAN logs to several parts because long time capture, we need to combine all parts CAN logs to one

6. how many CAN logs captured need to be combined as one, add these CAN log csv files name into the raw_log_list. for example, I want to combine 'pack1.csv', 'pack2.csv', 'pack3.csv' in current folder
    raw_log_list = [
        "pack1.csv",
        'pack2.csv',
        'pack3.csv',
    ]

7. create a class for can log parse, for example as below:
    scud_can_log_convert = scud_can_log_convert(
        dbc_file_full_path="./maple_202424100.dbc",     # specify dbc file path used
        raw_log_file_path="./",                         # CAN log folder path(e.g., current folder)
        raw_logs_list=raw_log_list,                     # CAN log csv files list which we need to combined(it can be only one CAN log)
        file_name_combined_logs="pack_cb.csv",          # specify combined CAN log file name
        file_path_parsed="./pack_PARSED.csv",           # parsed CAN log file path
        can_application_tool="CANas",                   # CAN application tool used (CANTest, CANas), time stamp different
    )
