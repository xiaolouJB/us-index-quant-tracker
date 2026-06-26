# -*- coding: utf-8 -*-
"""
clear_snapshot.py — 每次巡检第一步，强制清空上期快照。
防止旧数据在部分抓取脚本崩溃时残留，欺骗下游的门禁检查。
"""
from snapshot_util import reset_snapshot

if __name__ == '__main__':
    reset_snapshot()
    print("🧹 快照数据已清空，准备开始新的抓取流水线。")
