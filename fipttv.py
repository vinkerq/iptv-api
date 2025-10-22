#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_iptv_sources.py
从 dey/ip.txt 中 IP 列表获取 IPTV 数据，并生成完整播放源列表
支持普通文本输出和 M3U8 播放列表输出
"""

import requests
import os
import json
import time

# 输入 IP 文件
IP_FILE = os.path.join("dey", "ip.txt")
# 输出 IPTV 源文件（普通文本）
OUTPUT_FILE = "iptv_sources.txt"
# 输出 IPTV M3U8 文件（可直接导入播放器）
OUTPUT_M3U8 = "iptv_sources.m3u"

# IPTV 请求路径
REQUEST_PATH = "/iptv/live/1000.json?key=txiptv"
TIMEOUT = 20  # 请求超时秒数
RETRY = 2     # 请求失败重试次数
DELAY = 1     # 每次请求延迟秒数，避免被封

def read_ip_list(file_path):
    """读取 IP 列表，每行一个 IP:PORT"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"IP 文件不存在: {file_path}")
    ips = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                ips.append(line)
    return ips

def fetch_json(ipport):
    """请求 IPTV JSON，失败可重试"""
    url = f"http://{ipport}{REQUEST_PATH}"
    for attempt in range(RETRY + 1):
        try:
            resp = requests.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[错误] 请求失败: {url} -> {e} (重试 {attempt}/{RETRY})")
            time.sleep(DELAY)
    return None

def parse_data(json_data, ipport):
    """从 JSON 提取 name 和 url，拼接成完整 IPTV 源"""
    sources = []
    if not json_data or "data" not in json_data:
        return sources
    for item in json_data["data"]:
        name = item.get("name", "未知")
        url_path = item.get("url", "")
        if url_path:
            full_url = f"http://{ipport}{url_path}"
            sources.append((name, full_url))
    return sources

def save_txt(sources, file_path):
    """保存普通文本格式"""
    with open(file_path, "w", encoding="utf-8") as f:
        for name, url in sources:
            f.write(f"{name},{url}\n")

def save_m3u(sources, file_path):
    """保存 M3U8 播放列表"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for name, url in sources:
            f.write(f"#EXTINF:-1,{name}\n{url}\n")

def main():
    try:
        ip_list = read_ip_list(IP_FILE)
    except Exception as e:
        print(f"[错误] {e}")
        return

    all_sources = []

    for ipport in ip_list:
        print(f"正在请求：{ipport}{REQUEST_PATH}")
        json_data = fetch_json(ipport)
        sources = parse_data(json_data, ipport)
        if sources:
            all_sources.extend(sources)
            for name, url in sources:
                print(f"{name},{url}")
        else:
            print(f"[提示] 未获取到数据: {ipport}")

    if all_sources:
        save_txt(all_sources, OUTPUT_FILE)
        save_m3u(all_sources, OUTPUT_M3U8)
        print(f"\n✅ 全部完成，生成文件：\n- {OUTPUT_FILE}（文本）\n- {OUTPUT_M3U8}（M3U8 播放列表）")
        print(f"共 {len(all_sources)} 条 IPTV 源")
    else:
        print("\n⚠️ 未获取到任何 IPTV 源")

if __name__ == "__main__":
    main()
