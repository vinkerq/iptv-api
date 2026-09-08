@echo off
chcp 65001 >nul
title 咪咕M3U真实地址生成器

cd /d I:\node\migu_video

echo.
echo ==============================================
echo          咪咕M3U真实地址生成器
echo ==============================================
echo.
echo 当前目录：
echo I:\node\migu_video
echo.
echo 正在获取咪咕频道真实播放地址...
echo 请等待全部频道处理完成。
echo.

node export_m3u.js

echo.
echo ==============================================
echo                  已完成
echo ==============================================
echo.
echo M3U文件：
echo I:\node\migu_video\migu.m3u
echo.
echo TXT文件：
echo I:\node\migu_video\migu.txt
echo.
echo 可以关闭此窗口。
echo.

pause