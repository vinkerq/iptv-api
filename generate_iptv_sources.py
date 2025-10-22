#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_iptv_sources.py
增强版：支持请求超时跳过、直播源附加 IP/运营商、按节目名称分组输出
"""

import requests
import os
import json
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

IP_FILE = os.path.join("dey", "ip.txt")
OUTPUT_FILE = "iptv_sources.txt"
OUTPUT_M3U8 = "iptv_sources.m3u"
REQUEST_PATH = "/iptv/live/1000.json?key=txiptv"
TIMEOUT = 15   # 请求超时 15 秒
RETRY = 2
DELAY = 1

def read_ip_list(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"IP 文件不存在: {file_path}")
    ips = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                ips.append(line)
    return ips

def get_ip_info(ip):
    """
    获取 IP 信息（运营商/地区）
    这里可用真实 API 替换
    """
    # 示例，默认都返回“未知运营商”
    return "未知运营商"

def fetch_json(ipport):
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
    sources = []
    if not json_data or "data" not in json_data:
        return sources
    ip, _ = ipport.split(":")
    isp = get_ip_info(ip)
    for item in json_data["data"]:
        name = item.get("name", "未知")
        url_path = item.get("url", "")
        if url_path:
            full_url = f"http://{ipport}{url_path}"
            # 附加 IP 和运营商信息
            display_name = f"{name} [{ip} - {isp}]"
            sources.append((name, display_name, full_url))
    return sources

def save_txt_grouped(grouped_sources, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        for prog_name, items in grouped_sources.items():
            for display_name, url in items:
                f.write(f"{display_name},{url}\n")

def save_m3u_grouped(grouped_sources, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for prog_name, items in grouped_sources.items():
            for display_name, url in items:
                f.write(f"#EXTINF:-1,{display_name}\n{url}\n")

def main():
    try:
        ip_list = read_ip_list(IP_FILE)
    except Exception as e:
        print(f"[错误] {e}")
        return

    all_sources = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_ip = {executor.submit(fetch_json, ip): ip for ip in ip_list}
        for future in as_completed(future_to_ip):
            ipport = future_to_ip[future]
            try:
                json_data = future.result(timeout=TIMEOUT)
                sources = parse_data(json_data, ipport)
                if sources:
                    all_sources.extend(sources)
                    for _, display_name, url in sources:
                        print(f"{display_name},{url}")
                else:
                    print(f"[提示] 未获取到数据: {ipport}")
            except Exception as e:
                print(f"[提示] 跳过 {ipport}，原因: {e}")

    # 按节目名称分组
    grouped = defaultdict(list)
    for name, display_name, url in all_sources:
        grouped[name].append((display_name, url))

    if grouped:
        save_txt_grouped(grouped, OUTPUT_FILE)
        save_m3u_grouped(grouped, OUTPUT_M3U8)
        print(f"\n✅ 全部完成，生成文件：\n- {OUTPUT_FILE}（文本）\n- {OUTPUT_M3U8}（M3U8 播放列表）")
        total = sum(len(v) for v in grouped.values())
        print(f"共 {total} 条 IPTV 源")
    else:
        print("\n⚠️ 未获取到任何 IPTV 源")

if __name__ == "__main__":
    main()
