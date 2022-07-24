import os
import sys
import ssl
import json
import time
import pandas as pd
import datetime
import requests
from typing import Dict
from kaggle.api.kaggle_api_extended import KaggleApi

context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

# Discordメッセージ送信先:
URL = 'https://discord.com/api/webhooks/<webhook URL>'

# 監視対象コンペティション: kaggle competitions download -c xxxx (xxxx部分を指定)
COMPETITION = 'xxxx'

# メトリック
# 大きい方がよければ True
MAXIMIZE = True

# デバッグ処理用
DEBUG = False

def sender(message: str) -> None:
    """
    Discordにメッセージ送信を行う処理
    """
    req_head = {
        'Content-Type': 'application/json',
    }
    req_data = json.dumps({
        'content' : message
    })
    _ = requests.post(URL, data=req_data, headers=req_head)

def to_float(value) -> float:
    if value is None:
        return 0
    if type(value) == float and np.isnan(value):
        return 0
    if type(value) == str and len(value) == 0:
        return 0
    return float(value)

def watch(api, data) -> Dict:
    """
    コンペティションリーダーボードを監視する処理
    """
    result = {
        'post' : [ ],
        'data' : None
    }
    submissions = api.competition_submissions(COMPETITION)
    for desc in submissions:
        submitID = str(desc.ref)
        if submitID not in data:
            tm = datetime.datetime.strptime(str(desc.date) + '+0000', "%Y-%m-%d %H:%M:%S%z")
            data[submitID] = {
                'submitID' : submitID,
                'publicLB' : desc.publicScore if desc.publicScore is not None and desc.publicScore != 'None' else None,
                'describe' : desc.description if desc.description is not None else None,
                'set_time' : tm,
                'end_time' : None,
                'run_stat' : desc.status
            }
        if desc.status != 'pending' and data[submitID]['run_stat'] == 'pending':
            data[submitID]['publicLB'] = desc.publicScore
            data[submitID]['end_time'] = datetime.datetime.now(datetime.timezone.utc)
            data[submitID]['run_stat'] = desc.status
            data[submitID]['describe'] = desc.description
            # LB更新したか
            update = False
            errmsg = False
            if desc.publicScore is None or len(data[submitID]['publicLB']) == 0:
                # エラー(ex. Submission Scoring Error)
                errmsg = True
                scores = (data['BestLB'], data[submitID]['publicLB'])
            else:
                # 成功
                if data['BestLB'] is not None:
                    data['BestLB'] = data[submitID]['publicLB']
                scores = (data['BestLB'], data[submitID]['publicLB'])
                pvalue = to_float(data['BestLB'])
                cvalue = to_float(data[submitID]['publicLB'])
                if MAXIMIZE and cvalue > pvalue:
                    update = True
                    data['BestLB'] = data[submitID]['publicLB']
                if not MAXIMIZE and cvalue < pvalue:
                    update = True
                    data['BestLB'] = data[submitID]['publicLB']
            # 送信メッセージの作成:
            result['post'].append(buildMessage(data[submitID], '失敗' if errmsg else '成功', update, scores))
    result['data'] = data
    return result

def buildMessage(info: Dict, status: str, update: bool, scores) -> str:
    submitID = info['submitID']
    publicLB = info['publicLB']
    describe = info['describe']
    execTime = None
    if info['end_time'] is not None and info['set_time'] is not None:
        execTime = info['end_time'] - info['set_time']
        execTime = int(execTime.seconds / 60)
    # メッセージ作成
    message  = 'サブミットが{}しました:\n'.format(status)
    message += '```\n'
    message += 'submitID: {}\n'.format(submitID)
    if execTime is not None and len(execTime) > 0:
        message += 'execTime: {}min\n'.format(execTime)
    else:
        message += 'execTime: N/A\n'
    if publicLB is not None and len(publicLB) > 0:
        message += 'publicLB: {}\n'.format(publicLB)
    else:
        message += 'publicLB: N/A\n'
    if describe is not None and len(describe) > 0:
        message += 'comments: {}\n'.format(describe)
    message += '```\n'
    if update:
        message += 'リーダーボードを更新しました ({}⇒{})\n'.format(scores[0], scores[1])
    return message

def setup() -> Dict:
    dat = {
        'BestLB' : None,
    }
    if os.path.exists(COMPETITION + '_logger.csv'):
        csv = pd.read_csv(COMPETITION + '_logger.csv', dtype=str, encoding='utf8')
        for i in range(len(csv)):
            submitID = csv.iat[i, 0]
            publicLB = to_float(csv.iat[i, 1])
            run_stat = csv.iat[i, 2]
            set_time = datetime.datetime.strptime(str(csv.iat[i, 3]) + '+0000', '%Y/%m/%d %H:%M:%S%z') if type(csv.iat[i, 3]) == str else None
            end_time = datetime.datetime.strptime(str(csv.iat[i, 4]) + '+0000', '%Y/%m/%d %H:%M:%S%z') if type(csv.iat[i, 4]) == str else None
            describe = csv.iat[i, 5]
            dat[submitID] = {
                'submitID' : submitID,
                'publicLB' : publicLB,
                'describe' : describe,
                'set_time' : set_time,
                'end_time' : end_time,
                'run_stat' : run_stat
            }
    return dat

def write(data) -> None:
    os.makedirs('report', exist_ok=True)
    with open('report/' + COMPETITION + '_logger.csv', mode='w', encoding='utf-8') as f:
        f.write('submitID,publicLB,status,set_time,end_time,description\n')
        if data is not None:
            for k, v in data.items():
                if k == 'BestLB':
                    continue
                submitID = v['submitID']
                publicLB = v['publicLB'] if v['publicLB'] is not None else ''
                run_stat = v['run_stat']
                set_time = v['set_time'].strftime('%Y/%m/%d %H:%M:%S') if v['set_time'] is not None else ''
                end_time = v['end_time'].strftime('%Y/%m/%d %H:%M:%S') if v['end_time'] is not None else ''
                describe = v['describe'] if v['describe'] is not None else ''
                f.write('{},{},{},{},{},{}\n'.format(submitID, publicLB, run_stat, set_time, end_time, describe))

def getSend():
    return sender if not DEBUG else print

# エントリポイント:
if __name__ == '__main__':
    nop = not DEBUG
    dat = setup()
    api = KaggleApi()
    api.authenticate()
    send_fn = getSend()
    print('モニター開始: quitファイルを作成するとモニターを終了します')
    last_auth = time.time()
    while not os.path.exists('quit'):
        try:
            if time.time() - last_auth >= 3600:
                api.authenticate()
                print('[{}] (警告) 例外検知'.format(datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')))
            ret = watch(api, dat)
            msg = ret['post']
            dat = ret['data']
            write(dat)
            if not nop:
                for m in msg:
                    send_fn(m)
                # 実行状況の表示:
                # print('[{}] message={}'.format(datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S'), len(msg)))
            # 無視フラグ: 起動していない際の処理は時間が正しく取れないため送信しないための措置
            nop = False
            # 終了監視:
            # 待機は 20 x 3sec で約60秒ごとに検査する
            for i in range(20):
                if os.path.exists('quit'):
                    break
                time.sleep(3)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print('[{}] (警告) 例外検知'.format(datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')))
            print(e)
            print('[{}] (警告) --------------------'.format(datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')))
    print('モニター終了')
