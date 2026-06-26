@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
echo ========================================================
echo  美国宽基指数巡检 - 数据确定性管线 v1.1
echo ========================================================
echo.
echo [步骤1] 一键跑完数据管线 + 体检 (run_inspection.py)
python scripts\run_inspection.py
echo.
echo ========================================================
echo  接下来手动两步：
echo   2) 模型按 references\narrative_schema.md WebSearch人工字段
echo      并写 data\narrative.json
echo   3) python scripts\build_report.py  生成报告
echo ========================================================
pause
