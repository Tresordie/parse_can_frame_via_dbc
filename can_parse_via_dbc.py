# -*- encoding: utf-8 -*-
"""
@File    :   can_parse_via_dbc.py
@Time    :   2024/12/17 21:46:55
@Author  :   SimonYuan
@Version :   1.0
@Site    :   https://tresordie.github.io/
@Desc    :   
1. convert scud can log, porting from Ion Buzdugan's script, fixed the issue that standard frame "Unable to convert"
2. covered almost all kinds of SCUD CAN log files format so far
"""

import cantools
import chardet
from csv_operate import *
from tqdm import tqdm
import re
import os


class scud_can_log_convert(object):
    def __init__(
        self,
        dbc_file_full_path=None,
        raw_log_file_path=None,
        raw_logs_list=None,
        file_path_combined_logs=None,
        file_path_parsed=None,
        can_application_tool="CANTest",
    ):
        self.dbc_file_full_path = dbc_file_full_path

        self.raw_log_file_path = raw_log_file_path
        self.raw_logs_list = raw_logs_list

        self.file_path_combined_logs = file_path_combined_logs

        self.file_path_parsed = file_path_parsed
        self.can_application_tool = can_application_tool

        self.dbc_message_list = []
        self.can_id_parsed_msg_dict = {}
        self.can_id_parsed_msg_dict_list = []

    def detect_encoding(self):
        with open(self.raw_log_file_path + self.raw_logs_list[0], "rb") as f:
            data = f.read(1024)  # read 1KB data
        result = chardet.detect(data)
        encoding = result["encoding"]
        return encoding

    # combined all raw logs to one
    def multiple_scud_logs_combine(self):
        """
        1. sometimes REL logged multiple CAN log csv files, combine them into one
        2. SCUD captured CAN log in GB2312 or UTF8 format, please confirm by yourself
        """
        encoding = self.detect_encoding()

        if encoding == "GB2312" or encoding == "GBK":
            print("file encoing with GB2312(or GBK)")
            combine_gb2312_csv_log_files(
                self.raw_log_file_path,
                self.raw_logs_list,
                self.file_path_combined_logs,
            )
        elif encoding == "UTF-8":
            print("file encoing with UTF-8")
            combine_utf8_csv_log_files(
                self.raw_log_file_path,
                self.raw_logs_list,
                self.file_path_combined_logs,
            )
        elif encoding == "UTF-8-SIG":
            print("file encoing with UTF-8-SIG")
            combine_utf8_sig_csv_log_files(
                self.raw_log_file_path,
                self.raw_logs_list,
                self.file_path_combined_logs,
            )
        else:
            print("file encoing uncertain!")

    # convert Chinese to English
    def convert_can_log_to_en(self):
        df = pd.read_csv(self.file_path_combined_logs, header=None)
        for j in tqdm(range(df.shape[1])):
            if df.iloc[0, j] == "序号":
                df.iloc[0, j] = "Index"
            elif df.iloc[0, j] == "传输方向":
                df.iloc[0, j] = "Direction"
            elif (
                df.iloc[0, j] == "时间标识"
                or df.iloc[0, j] == "时间戳"
                or df.iloc[0, j] == "时间"
            ):
                df.iloc[0, j] = "Time Stamp"
            elif df.iloc[0, j] == "帧ID" or df.iloc[0, j] == "ID":
                df.iloc[0, j] = "Frame ID"
            elif df.iloc[0, j] == "帧格式":
                df.iloc[0, j] = "Format"
            elif df.iloc[0, j] == "帧类型":
                df.iloc[0, j] = "Type"
            elif df.iloc[0, j] == "数据长度" or df.iloc[0, j] == "长度":
                df.iloc[0, j] = "Data Length"
            elif df.iloc[0, j] == "数据(HEX)" or df.iloc[0, j] == "数据":
                df.iloc[0, j] = "Data(HEX)"
        df.to_csv(self.file_path_combined_logs, index=False, header=None)

        df = pd.read_csv(self.file_path_combined_logs)
        for i in tqdm(range(df.shape[0])):
            if df.loc[i, "Direction"] == "接收":
                df.loc[i, "Direction"] = "Receive"

            # SCUD captured CAN logs used different format csv file titles
            if df.loc[i, "Format"] == "数据帧":
                df.loc[i, "Format"] = "Data"

            if df.loc[i, "Format"] == "标准帧":
                df.loc[i, "Format"] = "Standard"

            if df.loc[i, "Format"] == "扩展帧":
                df.loc[i, "Format"] = "Extended"

            if df.loc[i, "Type"] == "标准帧":
                df.loc[i, "Type"] = "Standard"

            if df.loc[i, "Type"] == "数据帧":
                df.loc[i, "Type"] = "Data"

            if df.loc[i, "Type"] == "扩展帧":
                df.loc[i, "Type"] = "Extended"
        df.to_csv(self.file_path_combined_logs, index=False)

    def parse_scud_can_log(self):
        """
        parse SCUD CAN log via corresponding dbc file
        """
        db = cantools.database.load_file(self.dbc_file_full_path)
        df = pd.read_csv(self.file_path_combined_logs)

        df = df[df["Direction"] == "Receive"]

        # when SCUD used CANTest application, time stamp format is "14:29:57.690.0"
        if self.can_application_tool == "CANTest":
            df["Time Stamp"] = df["Time Stamp"].str[:-2]
            df["Time Stamp"] = pd.to_datetime(df["Time Stamp"], format="%H:%M:%S.%f")
            df["Test Time (ms)"] = (
                df["Time Stamp"] - df["Time Stamp"].iloc[0]
            ).dt.total_seconds() * 1000
        elif self.can_application_tool == "CANas":
            # when SCUD used CANas application, time stamp format is "2924.7805"(unit is Second)
            df["Time Stamp"] = df["Time Stamp"] * 1000
            df["Test Time (ms)"] = df["Time Stamp"] - df["Time Stamp"].iloc[0]

        # all dbc messages list as title of parsed csv file
        self.dbc_message_list = [msg.name for msg in db.messages]
        df_out = pd.DataFrame(columns=["Test Time (ms)"] + self.dbc_message_list)

        for row in range(df.shape[0]):
            try:
                self.can_id_parsed_msg_dict = db.decode_message(
                    frame_id_or_name=int(df["Frame ID"].iloc[row], 16),
                    data=bytearray.fromhex(df["Data(HEX)"].iloc[row]),
                )

                # 1. can't add test_time(ms) if failed to decode message
                # 2. test_time(ms) should be added at last, or it will be overwritten by other info of decode message
                self.can_id_parsed_msg_dict["Test Time (ms)"] = df[
                    "Test Time (ms)"
                ].iloc[row]
                self.can_id_parsed_msg_dict_list.append(self.can_id_parsed_msg_dict)
            except:
                frame_id = df["Frame ID"].iloc[row]
                print(f"Unable to convert {frame_id}")

        df_out = pd.DataFrame(self.can_id_parsed_msg_dict_list)
        df_out.sort_values(by=["Test Time (ms)"], inplace=True)
        time_ms = df_out.pop("Test Time (ms)")
        df_out.insert(loc=0, column="Test Time (ms)", value=time_ms)
        df_out.to_csv(self.file_path_parsed, index=False)


if __name__ == "__main__":
    #######################################################################################################################
    # single CAN log file parse

    # CAN log csv files list need to be combined
    raw_log_list = [
        "6#(8781824-8847359).csv",
        "6#(8847360-8912895).csv",
    ]

    raw_log_file_path = "./23 laps can log/6#/23cycles/"
    raw_log_file_parsed_path = raw_log_file_path + "parsed/"
    mkdir(raw_log_file_parsed_path)

    # fmt: off
    scud_can_log_convert = scud_can_log_convert(
        dbc_file_full_path="./maple_20243250.dbc",        # specify dbc file used
        raw_log_file_path=raw_log_file_path,              # CAN log folder path
        raw_logs_list=raw_log_list,                       # CAN log csv files list
        file_path_combined_logs=raw_log_file_parsed_path + (raw_log_list[0].split('.csv'))[0] + '_combined.csv',   # specify combined CAN log file name
        file_path_parsed=raw_log_file_parsed_path + (raw_log_list[0].split('.csv'))[0] + "_PARSED.csv",  # parsed CAN log file path
        can_application_tool="CANTest",                   # CAN application tool used (CANTest, CANas), time stamp different
    )
    # fmt: on

    scud_can_log_convert.multiple_scud_logs_combine()
    scud_can_log_convert.convert_can_log_to_en()
    scud_can_log_convert.parse_scud_can_log()
    #######################################################################################################################

    """
    #######################################################################################################################
    # multiple CAN log files, select 1pcs to parse each time
    raw_log_list = []
    # indicate raw_log_file_path and make dir for parsed file
    raw_log_file_path = "./12.31/3#/"
    raw_log_file_parsed_path = raw_log_file_path + "parsed/"
    mkdir(raw_log_file_parsed_path)

    # created list to store multiple class for CAN log parse
    file_name_list = os.listdir(raw_log_file_path)
    scud_can_log_convert_list = [0] * len(file_name_list)
    temp_raw_log_list = []

    # excluded the combined and parsed file
    for file_name in file_name_list:
        if re.search(r"\.csv", file_name):
            if "_combined" not in file_name and "_PARSED" not in file_name:
                raw_log_list.append(file_name)

    # created multiple class to parse each CAN log
    for i in range(len(raw_log_list)):
        temp_raw_log_list = []
        temp_raw_log_list.append(raw_log_list[i])
        print(temp_raw_log_list)
        # fmt: off
        scud_can_log_convert_list[i]= scud_can_log_convert(
            dbc_file_full_path="./maple_20243250.dbc",              # specify dbc file used
            raw_log_file_path=raw_log_file_path,                    # CAN log folder path
            raw_logs_list=temp_raw_log_list,                        # CAN log csv files list
            file_path_combined_logs=raw_log_file_parsed_path + (temp_raw_log_list[0].split('.csv'))[0] + '_combined.csv',   # specify combined CAN log file name
            file_path_parsed=raw_log_file_parsed_path + (temp_raw_log_list[0].split('.csv'))[0] + "_PARSED.csv",  # parsed CAN log file path
            can_application_tool="CANTest",                         # CAN application tool used (CANTest, CANas), time stamp different
        )
        # fmt: on
        scud_can_log_convert_list[i].multiple_scud_logs_combine()
        scud_can_log_convert_list[i].convert_can_log_to_en()
        scud_can_log_convert_list[i].parse_scud_can_log()
    #######################################################################################################################
    """
