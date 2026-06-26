# -*- coding: utf-8 -*-
"""快照工具：所有 fetch 脚本把关键字段写入 data/latest_snapshot.json，
供 sanity_check.py 审核与 history/indicators.csv 落库使用。"""
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
# 支持环境变量覆盖快照路径：并行管线时每个 fetcher 写各自分片文件，避免读改写同一文件的竞态
SNAPSHOT_PATH = os.environ.get('SNAPSHOT_PATH_OVERRIDE') or os.path.join(DATA_DIR, 'latest_snapshot.json')
HISTORY_PATH = os.path.join(BASE_DIR, 'history', 'indicators.csv')


def load_snapshot():
    if os.path.exists(SNAPSHOT_PATH):
        try:
            with open(SNAPSHOT_PATH, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def reset_snapshot():
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(SNAPSHOT_PATH):
        try:
            os.remove(SNAPSHOT_PATH)
        except Exception:
            pass

def update_snapshot(fields: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    snap = load_snapshot()
    snap.update(fields)
    snap['_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(SNAPSHOT_PATH, 'w', encoding='utf-8') as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)
    return snap
