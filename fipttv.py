#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_iptv_sources.py
从 dey/ip.txt 中 IP 列表获取 IPTV 数据，并生成完整播放源列表
"""

import requests
import os
import json

# 输入 IP 文件
IP_FILE = os.path.join("dey", "ip.txt")
# 输出 IPTV 源文件
OUTPUT_FILE = "iptv_sources.txt"

# IPTV 请求路径
REQUEST_PATH = "/iptv/live/1000.json?key=txiptv"
TIMEOUT = 20  # 请求超时秒数

def read_ip_list(file_path):
    """读取 IP 列表，每行一个 IP:PORT"""
    ips = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                ips.append(line)
    return ips

def fetch_json(ipport):
    """请求 IPTV JSON"""
    url = f"http://{ipport}{REQUEST_PATH}"
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[错误] 请求失败: {url}  -> {e}")
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
            sources.append(f"{name},{full_url}")
    return sources

def main():
    if not os.path.exists(IP_FILE):
        print(f"[错误] IP 文件不存在: {IP_FILE}")
        return

    ip_list = read_ip_list(IP_FILE)
    all_sources = []

    for ipport in ip_list:
        print(f"正在请求：{ipport}{REQUEST_PATH}")
        json_data = fetch_json(ipport)
        sources = parse_data(json_data, ipport)
        if sources:
            all_sources.extend(sources)
            for s in sources:
                print(s)
        else:
            print(f"[提示] 未获取到数据: {ipport}")

    # 保存到文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for line in all_sources:
            f.write(line + "\n")

    print(f"\n✅ 全部完成，生成文件: {OUTPUT_FILE}，共 {len(all_sources)} 条 IPTV 源")

if __name__ == "__main__":
    main()