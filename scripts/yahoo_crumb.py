# -*- coding: utf-8 -*-
"""
yahoo_crumb.py — Yahoo Finance Crumb 管理器
解决 401 Unauthorized 报错。提取并自动挂载 crumb 至 requests.Session。
为了兼容 yfinance，可以将会话直接传递给 yfinance。
"""
import requests

_yahoo_session = None

def get_yahoo_session() -> requests.Session:
    """获取带 crumb 的 Yahoo Finance session（自动缓存）"""
    global _yahoo_session
    if _yahoo_session and hasattr(_yahoo_session, '_crumb'):
        return _yahoo_session
    
    s = requests.Session()
    s.headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    
    try:
        # Step 1: 获取 cookie
        s.get('https://fc.yahoo.com', timeout=10)
        
        # Step 2: 获取 crumb
        r = s.get('https://query2.finance.yahoo.com/v1/test/getcrumb', timeout=10)
        r.raise_for_status()
        s._crumb = r.text
        
        _yahoo_session = s
    except Exception as e:
        print(f"⚠️ Yahoo Crumb 获取失败: {e}，将使用普通 Session")
        s._crumb = ""
        _yahoo_session = s

    return _yahoo_session
