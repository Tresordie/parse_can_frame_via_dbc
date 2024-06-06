# -*- coding: utf-8 -*-
'''
@File    :   can_parse_via_dbc.py
@Time    :   2024/06/02 20:31:29
@Author  :   SimonYuan 
@Version :   1.0
@Site    :   https://tresordie.github.io/
@Desc    :   None
'''

import cantools
import pandas

raw_data = b'\x04\x0E\x02\x0E\x01\x0E\x01\x0E'

db = cantools.database.load_file('./maple.dbc')

messages = db.messages

# print(messages)

message = messages[0]
signals = message.signals

signal = signals[0]
name = signal.name
start_bit = signal.start
length = signal.length

decode_data = signal.decode(raw_data)
print(decode_data)

# message = db.get_message_by_name('BMS_CellVoltage_1')
# signal_value = message.decode(raw_data)
# print(signal_value)
