# -*- coding: utf-8 -*-
'''
@File    :   can_parse_via_dbc.py
@Time    :   2024/06/02 20:31:29
@Author  :   SimonYuan 
@Version :   1.0
@Site    :   https://tresordie.github.io/
@Desc    :   convert scud can log, porting from Ion Buzdugan's script, fixed the bug "Unable to convert"
'''

import cantools
import pandas as pd
import can
from csv_operate import *
from tqdm import tqdm


class scud_can_log_convert(object):
    def __init__(
        self,
        dbc_file_full_path=None,
        raw_log_file_path=None,
        raw_logs_list=None,
        file_name_combined_logs=None,
        file_path_parsed=None,
    ):
        self.dbc_file_full_path = dbc_file_full_path

        self.raw_log_file_path = raw_log_file_path
        self.raw_logs_list = raw_logs_list

        self.file_name_combined_logs = file_name_combined_logs
        self.full_path_combined_logs = (
            self.raw_log_file_path + self.file_name_combined_logs
        )

        self.file_path_parsed = file_path_parsed
        self.dbc_message_list = []
        self.can_id_parsed_msg_dict = {}
        self.can_id_parsed_msg_dict_list = []

    # combined all raw logs to one
    def multiple_scud_logs_combine(self):
        combine_gb2312_csv_log_files(
            self.raw_log_file_path,
            self.raw_logs_list,
            self.full_path_combined_logs,
        )

    # convert Chinese to English
    def convert_can_log_to_en(self):
        df = pd.read_csv(self.full_path_combined_logs)

        for i in tqdm(range(df.shape[0])):
            if df.loc[i, '传输方向'] == "接收":
                df.loc[i, '传输方向'] = "Receive"

            if df.loc[i, '帧格式'] == "数据帧":
                df.loc[i, '帧格式'] = "Data"

            if df.loc[i, '帧类型'] == "标准帧":
                df.loc[i, '帧类型'] = "Standard"

            if df.loc[i, '帧类型'] == "扩展帧":
                df.loc[i, '帧类型'] = "Extended"

        df.to_csv(self.full_path_combined_logs, index=False)

        df = pd.read_csv(self.full_path_combined_logs, header=None)
        for j in tqdm(range(df.shape[1])):
            if df.iloc[0, j] == "序号":
                df.iloc[0, j] = "Index"
            elif df.iloc[0, j] == "传输方向":
                df.iloc[0, j] = "Direction"
            elif df.iloc[0, j] == "时间标识":
                df.iloc[0, j] = "Time Stamp"
            elif df.iloc[0, j] == "帧ID":
                df.iloc[0, j] = "Frame ID"
            elif df.iloc[0, j] == "帧格式":
                df.iloc[0, j] = "Format"
            elif df.iloc[0, j] == "帧类型":
                df.iloc[0, j] = "Type"
            elif df.iloc[0, j] == "数据长度":
                df.iloc[0, j] = "Data Length"
            elif df.iloc[0, j] == "数据(HEX)":
                df.iloc[0, j] = "Data(HEX)"

        df.to_csv(self.full_path_combined_logs, index=False, header=None)

    # todo: 根据dbc解析scud can log
    def parse_scud_can_log(self):
        db = cantools.database.load_file(self.dbc_file_full_path)
        df = pd.read_csv(self.full_path_combined_logs)

        df = df[df['Direction'] == 'Receive']
        df['Time Stamp'] = df['Time Stamp'].str[:-2]
        df['Time Stamp'] = pd.to_datetime(df['Time Stamp'], format='%H:%M:%S.%f')

        # 在原有data frame的基础上添加了df['Test Time (ms)']的新列，获取以ms为单位的时间，在最后添加了新列 ‘Test Time (ms)’
        # astype进行数据类型转换
        df['Test Time (ms)'] = (df['Time Stamp'] - df['Time Stamp'].iloc[0]).astype(
            'timedelta64[ms]'
        )

        # 将dbc文件中所有的messages的name组成一个list赋值给messages
        self.dbc_message_list = [msg.name for msg in db.messages]
        df_out = pd.DataFrame(columns=['Test Time (ms)'] + self.dbc_message_list)

        for row in range(df.shape[0]):
            try:
                self.can_id_parsed_msg_dict = db.decode_message(
                    frame_id_or_name=int(df['Frame ID'].iloc[row], 16),
                    data=bytearray.fromhex(df['Data(HEX)'].iloc[row]),
                )

                # 1. 如果decode_message失败，就不能添加时间
                # 2. 如果先添加时间到，decode_message内容赋值会覆盖Test Time (ms)的数据
                self.can_id_parsed_msg_dict['Test Time (ms)'] = df[
                    'Test Time (ms)'
                ].iloc[row]

                # print('can_id_parsed_msg_dict: row = %d' % row)
                # print(self.can_id_parsed_msg_dict)
                self.can_id_parsed_msg_dict_list.append(self.can_id_parsed_msg_dict)
                # print('can_id_parsed_msg_dict_list: row = %d' % row)
                # print(self.can_id_parsed_msg_dict_list)

            except:
                frame_id = df['Frame ID'].iloc[row]
                print(f'Unable to convert {frame_id}')

        df_out = pd.DataFrame(self.can_id_parsed_msg_dict_list)
        df_out.sort_values(by=['Test Time (ms)'], inplace=True)
        time_ms = df_out.pop('Test Time (ms)')
        df_out.insert(loc=0, column='Test Time (ms)', value=time_ms)
        df_out.to_csv(self.file_path_parsed, index=False)


if __name__ == '__main__':
    raw_log_list = [
        'semi_pack1.csv',
        # 'pack2.csv',
        # 'pack3.csv',
        # 'pack4.csv',
        # 'pack5.csv',
    ]

    scud_can_log_convert = scud_can_log_convert(
        dbc_file_full_path='./maple.dbc',
        raw_log_file_path='./',
        raw_logs_list=raw_log_list,
        file_name_combined_logs='pack_cb.csv',
        file_path_parsed='pack_cb_PARSED.csv',
    )

    scud_can_log_convert.multiple_scud_logs_combine()
    scud_can_log_convert.convert_can_log_to_en()
    scud_can_log_convert.parse_scud_can_log()
