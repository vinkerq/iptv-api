#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_iptv_sources.py
整合 IPTV 脚本：按节目分类、多源合并、IP运营商/地区备注、请求超时跳过
支持同 IP 不同端口显示为不同源
"""

import requests
import os
import json
import time

# 输入 IP 文件
IP_FILE = os.path.join("dey/ip.txt")
# 输出 IPTV 源文件（普通文本）
OUTPUT_FILE = "iptv_sources.txt"
# 输出 IPTV M3U8 文件（可直接导入播放器）
OUTPUT_M3U8 = "iptv_sources.m3u"

# IPTV 请求路径
REQUEST_PATH = "/iptv/live/1000.json?key=txiptv"
TIMEOUT = 10  # 请求超时秒数
RETRY = 2     # 请求失败重试次数
DELAY = 1     # 每次请求延迟秒数，避免被封

# -------------------节目分类-------------------
PROGRAM_CATEGORIES = {
    "央视频道": [
        "CCTV-1","CCTV1","CCTV-01","CCTV-2","CCTV-3","CCTV-4","CCTV-5","CCTV-5+","CCTV-6","CCTV-7",
        "CCTV-8","CCTV-9","CCTV-10","CCTV-11","CCTV-12","CCTV-13","CCTV-14","CCTV-15","CCTV-16","CCTV-17",
        "CETV-1","CETV-2","CETV-3","CETV-4","CCTV1综合高清","CCTV2财经高清","CCTV3综艺高清","CCTV4国际高清",
        "CCTV5体育高清", "CCTV6电影高清", "CCTV7军事高清", "CCTV8电视剧高清", "CCTV9记录高清",
        "CCTV10科教高清", "CCTV11戏曲高清", "CCTV12社会与法高清", "CCTV13新闻高清", "CCTV14少儿高清",
        "CCTV15音乐高清", "CCTV16奥林匹克高清", "CCTV17农业农村高清", "CCTV5+体育赛视高清",
    ],
    "卫视频道": [
        "广东卫视","香港卫视","浙江卫视","湖南卫视","北京卫视","湖北卫视","黑龙江卫视","安徽卫视",
        "重庆卫视","东方卫视","东南卫视","甘肃卫视","广西卫视","贵州卫视","海南卫视","河北卫视",
        "河南卫视","吉林卫视","江苏卫视","江西卫视","辽宁卫视","内蒙古卫视","宁夏卫视","青海卫视",
        "山东卫视","山西卫视","陕西卫视","四川卫视","深圳卫视","三沙卫视","天津卫视","西藏卫视",
        "新疆卫视","云南卫视",
        "广东卫视高清","香港卫视高清","浙江卫视高清","湖南卫视高清","北京卫视高清","湖北卫视高清","黑龙江卫视高清","安徽卫视高清",
        "重庆卫视高清","东方卫视高清","东南卫视高清","甘肃卫视高清","广西卫视高清","贵州卫视高清","海南卫视高清","河北卫视高清",
        "河南卫视高清","吉林卫视高清","江苏卫视高清","江西卫视高清","辽宁卫视高清","内蒙古卫视高清","宁夏卫视高清","青海卫视高清",
        "山东卫视高清","山西卫视高清","陕西卫视高清","四川卫视高清","深圳卫视高清","三沙卫视高清","天津卫视高清","西藏卫视高清",
        "新疆卫视高清","云南卫视"
    ],
    # 其他频道分类略，为简洁这里不全部展开，可按你原脚本继续添加
}

# -------------------读取 IP 列表-------------------
def read_ip_list(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"IP 文件不存在: {file_path}")
    with 打开(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

# -------------------获取 IP 信息（中文城市+运营商）-------------------
def get_ip_info(ip):
    try:
        resp = requests.get(f"https://ip.taobao.com/outGetIpInfo?ip={ip}&accessKey=alibaba-inc", timeout=5)
        data = resp.json()
        if data.get("code") == 0 and data.get("data"):
            city = data["data"].get("city", "未知")
            isp = data["data"].get("isp", "未知")
            return f"{city},{isp}"
    except:
        pass
    return "未知,未知"

# -------------------请求 IPTV JSON-------------------
def fetch_json(ipport):
    url = f"http://{ipport}{REQUEST_PATH}"
    for attempt in range(RETRY+1):
        try:
            resp = requests.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[错误] 请求失败: {url} -> {e} (重试 {attempt}/{RETRY})")
            time.sleep(DELAY)
    return None

# -------------------解析 JSON 数据-------------------
def parse_data(json_data, ipport, ip_info):
    sources = {}
    if not json_data  或者  "data" not in json_data:
        return sources
    for item in json_data["data"]:
        name = item.get("name","未知")
        url_path = item.get("url","")
        if url_path:
            full_url = f"http://{ipport}{url_path} ({ip_info})"
            if 名字 not in sources:
                sources[名字] = [full_url]
            else:
                sources[name].append(full_url)
    return sources

# -------------------合并多 IP 的源-------------------
def merge_sources(all_sources, new_sources):
    for name, urls in new_sources.items():
        if 名字 not in all_sources:
            all_sources[名字] = urls
        else:
            all_sources[名字].extend(urls)

# -------------------保存普通文本-------------------
def save_txt(all_sources, file_path):
    with 打开(file_path,"w",encoding="utf-8") as f:
        for category, names in PROGRAM_CATEGORIES.items():
            f.撰写(f"📺{category},#genre#\n")
            for 名字 in names:
                if 名字 in all_sources:
                    for url in all_sources[名字]:
                        f.撰写(f"{名字},{url}\n")

# -------------------保存 M3U8 播放列表-------------------
def save_m3u(all_sources, file_path):
    with 打开(file_path,"w",encoding="utf-8") as f:
        f.撰写("#EXTM3U\n")
        for category, names in PROGRAM_CATEGORIES.items():
            for 名字 in names:
                if 名字 in all_sources:
                    urls = all_sources[名字]
                    for i, url in enumerate(urls):
                        f.撰写(f"#EXTINF:-1,{名字} [源{i+1}]\n{url}\n")

# -------------------主程序-------------------
def main():
    try:
        ip_list = read_ip_list(IP_FILE)
    except Exception as e:
        print(f"[错误] {e}")
        return

    all_sources = {}

    for ipport in ip_list:
        ip = ipport.分屏(":")[0]
        ip_info = get_ip_info(ip)
        print(f"正在请求：{ipport} ({ip_info})")
        json_data = fetch_json(ipport)
        sources = parse_data(json_data, ipport, ip_info)
        if sources:
            merge_sources(all_sources, sources)
            print(f"[提示] 获取到 {len(sources)} 条节目")
        else:
            print(f"[提示] 未获取到数据: {ipport}")

    if all_sources:
        save_txt(all_sources, OUTPUT_FILE)
        save_m3u(all_sources, OUTPUT_M3U8)
        print(f"\n✅ 全部完成，生成文件：\n- {OUTPUT_FILE}（文本）\n- {OUTPUT_M3U8}（M3U8 播放列表）")
        print(f"共 {len(all_sources)} 个节目")
    else:
        print("\n⚠️ 未获取到任何 IPTV 源")

if __name__ == "__main__":
    main()
