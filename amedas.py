#!/usr/bin/env python
# -*- coding: utf-8 -*-
import aiohttp
import asyncio
import datetime
import os
import sys

import requests

# codes format:
#
#       spotname code [region]
#
# 札幌 14163
# 東京 44132
# 清水 50261 静岡
# 清水 65121 和歌山
# 清水 74516 高知
#
# from
#       http://www.jma.go.jp/jma/kishou/know/amedas/kaisetsu.html
#       http://www.jma.go.jp/jma/kishou/know/amedas/ame_master.zip
basename = os.path.splitext(os.path.basename(sys.argv[0]))[0]
codes = []
with open(f"{os.environ.get('HOME', '.')}/.{basename}") as fd:
    for line in fd.read().strip().split('\n'):
        t = f'{line} '.split(' ')
        codes.append([t[0], t[1], t[2]])

# wind directions
WD = '静穏 北北東 北東 東北東 東 東南東 南東 南南東 南 南南西 南西 西南西 西 西北西 北西 北北西 北'.split()

# AQC (Automatic Quality Control) 識別符号
# https://www.data.jma.go.jp/stats/data/mdrr/man/remark.html
# https://www.data.jma.go.jp/suishin/shiyou/pdf/no13301
# 0 正常
# 1 準正常 (やや疑わしい)
# 2 非常に疑わしい
# 3 利用に適さない
# 4 観測値は期間内で資料数が不足している
# 5 点検又は計画休止のため欠測
# 6 障害のため欠測
# 7 この要素の観測はしていない
AQC_INFO = {
    0: '',
    1: ')',
    2: '#',
    3: '#',
    4: ']',
    5: '休止中',
    6: '✕',
    None: '　',
}

# get latest time
with requests.get('https://www.jma.go.jp/bosai/amedas/data/latest_time.txt') as r:
    latest_time = r.content.decode('utf-8')
    dt = datetime.datetime.strptime(latest_time, '%Y-%m-%dT%H:%M:%S%z')
    # print(dt.strftime('%Y-%m-%d %H:%M:%S'))
    yyyymmdd = dt.strftime('%Y%m%d')
    HH = dt.strftime('%H')
    hh = f'{int(HH) // 3 * 3:02d}'

# print(yyyymmdd, HH, hh)

# parse arguments
AMEDAS = os.environ.get('AMEDAS', '44132').split()
if len(sys.argv) > 1:
    _args = []
    for arg in sys.argv[1:]:
        for _arg in arg.split():
            if _arg:
                _args.append(_arg)
    if _args:
        AMEDAS = _args

# translate loc to code
locs = []
errs = []
for arg in AMEDAS:
    if arg.isdigit():
        locs.append(arg)
    else:
        count = 0
        for loc, code, pref in codes:
            if loc == arg:
                locs.append(code)
                count += 1
        if not count:
            errs.append(arg)

# print(AMEDAS)
# print(locs)
# print(errs)


async def fetch_data(session, loc, code, url, lines):
    global yyyymmdd, HH
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                base_key = f'{yyyymmdd}{HH}0000'        # 積雪は1時間毎
                last_key = list(data.keys())[-1]
                _vars = data.get(base_key)
                # 存在しない時がある
                if _vars is None:
                    return
                for k in data[last_key]:
                    _vars[k] = data[last_key][k]
                    h = last_key[8:10]
                if h == '00':
                    h = '24'
                m = last_key[10:12]
                _lines = [f'{loc} {h}:{m}']
                for x in [
                        '気温 temp 度',
                        '降水量 precipitation1h mm/h',
                        '風向 windDirection -',
                        '風速 wind m/s',
                        '積雪 snow cm',
                        '降雪 snow1h cm/h',
                        '湿度 humidity %',
                        '気圧 pressure hPa',
                        '最低気温 minTemp 度',
                        '最高気温 maxTemp 度',
                ]:
                    t, k, u = x.split()
                    if k in _vars:
                        v, aqc = _vars[k]
                        if isinstance(v, float):
                            if v == int(v):
                                v = int(v)
                        # 0: 正常 1: 准正常
                        if aqc != 0 and aqc != 1:
                            continue
                        else:
                            if k == 'windDirection':
                                _lines.append(f'{t} {WD[v]}')
                            elif 'Temp' in k:
                                h, m = _vars[f'{k}Time'].values()
                                if (h or m) is not None:
                                    _lines.append(f"{t} {v}{u} ({(h + 9) % 24:02d}:{m:02d})")
                                else:
                                    _lines.append(f"{t} {v}{u}")
                            else:
                                _lines.append(f'{t} {v}{u}')
                lines[code] = ' '.join(_lines)
            else:
                print(f"Error: {response.status} for URL: {url}")
    except aiohttp.ClientError as e:
        print(f"aiohttp error for URL {url}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred for URL {url}: {e}")


async def prequests(loc, code, lines):
    async with aiohttp.ClientSession() as session:
        tasks = []
        url = f'https://www.jma.go.jp/bosai/amedas/data/point/{code}/{yyyymmdd}_{hh}.json'
        task = asyncio.create_task(fetch_data(session, loc, code, url, lines))
        tasks.append(task)

        await asyncio.gather(*tasks)


# lines :  {key: code, value: amedas}
lines = {}
for code in locs:
    loc = None
    for _loc, _code, _pref in codes:
        if code == _code:
            if _pref and _pref != '東京':
                loc = f'{_loc}({_pref})'
            else:
                loc = _loc
    if loc:
        asyncio.run(prequests(loc, code, lines))

for code in lines:
    print(lines[code])
if errs:
    print(f"{' '.join(errs)} が見つかりませんでした。https://www.jma.go.jp/bosai/map.html#contents=amedas から観測地点を指定してください。")
