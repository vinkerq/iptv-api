#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_iptv_sources.py
Integrate IPTV sources: categorize programs, merge multiple sources, add IP info, skip on timeout.
Supports multiple sources on same IP with different ports.
"""

import requests
import os
import time

# Input IP file
IP_FILE = os.path.join("dey/ip.txt")
# Output IPTV sources (plain text)
OUTPUT_FILE = "iptv_sources.txt"
# Output IPTV M3U8 file (for players)
OUTPUT_M3U8 = "iptv_sources.m3u"

# IPTV request path
REQUEST_PATH = "/iptv/live/1000.json?key=txiptv"
TIMEOUT = 10  # request timeout in seconds
RETRY = 2     # retry times if request fails
DELAY = 1     # delay between requests

# -------------------Program categories (complete, with Chinese names)-------------------
PROGRAM_CATEGORIES = {
    "央视频道": [
        "CCTV-1","CCTV1","CCTV-01","CCTV-2","CCTV-3","CCTV-4","CCTV-5","CCTV-5+","CCTV-6","CCTV-7",
        "CCTV-8","CCTV-9","CCTV-10","CCTV-11","CCTV-12","CCTV-13","CCTV-14","CCTV-15","CCTV-16","CCTV-17",
        "CETV-1","CETV-2","CETV-3","CETV-4","CCTV1综合高清","CCTV2财经高清","CCTV3综艺高清","CCTV4国际高清",
        "CCTV5体育高清","CCTV6电影高清","CCTV7军事高清","CCTV8电视剧高清","CCTV9记录高清",
        "CCTV10科教高清","CCTV11戏曲高清","CCTV12社会与法高清","CCTV13新闻高清","CCTV14少儿高清",
        "CCTV15音乐高清","CCTV16奥林匹克高清","CCTV17农业农村高清","CCTV5+体育赛视高清",
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
        "新疆卫视高清","云南卫视高清"
    ],
    "广东频道": [
        "广东珠江","广东体育","广东新闻","广东卫视","广东民生","大湾区卫视","广州综合",
        "广州影视","广州竞赛","江门综合","江门侨乡生活","佛山综合","深圳卫视","汕头综合",
        "汕头经济","汕头文旅","茂名综合","茂名公共",
        "广东珠江高清","广东体育高清","广东新闻高清","广东卫视高清","广东民生高清","大湾区卫视高清","广州综合高清",
        "广州影视高清","广州竞赛高清","江门综合高清","江门侨乡生活高清","佛山综合高清","深圳卫视高清","汕头综合高清",
        "汕头经济高清","汕头文旅高清","茂名综合高清","茂名公共高清"
    ],
    "浙江频道": [
        "浙江钱江","浙江钱江都市","浙江钱江台","浙江生活","浙江经济生活","浙江教育","浙江民生",
        "浙江新闻","浙江少儿"
    ],
    "北京频道": [
        "北京卡酷少儿","北京影院","北京新闻","北京生活","北京科教","北京财经","北京青年",
        "BTV纪实","清华大学电视台","石景山有线","通州电视台"
    ],
    "辽宁频道": [
        "朝阳教育","朝阳新闻综合","辽宁北方","辽宁影视剧","辽宁教育青少","辽宁生活",
        "辽宁经济","辽宁都市","锦州一套新闻综合","锦州二套教育"
    ],
    "湖南频道": [
        "湖南都市","湖南视剧","湖南经视","湖南电视剧","湖南电影","湖南爱晚","湖南教育",
        "湖南娱乐","湖南国际","湖南公共","金鹰纪实","湖南金鹰纪实","长沙新闻综合","长沙新闻",
        "长沙政法","长沙影视","长沙女性","醴陵综合","衡阳新闻综合","衡阳公共","茶陵新闻综合",
        "益阳新闻综合","益阳教育","益阳公共","湘潭新闻综合","湘潭县综合","湘潭公共",
        "湘潭公共都市","洪江市综合","泸溪电视台","汨罗新闻综合","江华综合","汝城综合",
        "永顺综合","桑植新闻综合","新化新闻综合","屈原综合","宁乡综合","娄底综合","保靖时政",
        "云溪新闻综合"
    ],
    "湖北频道": [
        "湖北新闻综合","湖北综合","湖北经视","湖北生活","湖北教育","湖北影视","湖北公共新闻",
        "湖北公共","湖北经济","湖北垄上","武汉一台新闻综合","武汉二台电视剧","武汉三台科技生活",
        "武汉四台经济","武汉五台文体","武汉六台外语","武汉1新闻综合","武汉2电视剧","武汉3科技生活",
        "武汉教育","湖北武汉教育","武汉经济","武汉新闻综合","武汉文体","武汉外语","江夏经济生活",
        "江夏新闻综合","建始综合","崇阳新闻综合","十堰新闻","十堰公共","保康新闻综合",
        "仙桃生活文体","仙桃新闻综合","麻城综合","郧阳新闻综合","荆门新闻综合","云梦综合",
        "云梦党建农业","武汉生活","武汉新闻","武汉经济","荆门新闻综合","崇阳综合",
        "十堰新闻","潜江综合","湖北生活","湖北教育","湖北影视","湖北垄上"
    ],
    "广西频道": [
        "乐业综合","凌云综合","凭祥综合","北海新闻综合","北海经济科教","南宁公共","南宁影娱乐",
        "南宁新闻综合","南宁都市生活","博白综合","天等综合","宾阳综合","岑溪综合","崇左综合",
        "巴马综合","昭平综合","来宾综合","桂平综合","灌阳新闻综合","灵川综合","田东综合",
        "田阳综合","罗城综合","融水综合","西林综合","贺州综合","资源电视台","那坡综合",
        "都安综合","钦州公共","钦州综合","靖西综合","龙州综合","广西新闻","罗城综合",
        "北海新闻","桂林新闻","广西贺州","广西国际","广西乐思购","南宁新闻综合","南宁都市生活",
        "南宁影视娱乐","南宁公共"
    ],
    "天津频道": [
        "宁河新闻","滨海新闻","滨海综艺","滨海影院","津南一套","武清综合","天津都市","天津新闻",
        "天津文艺","天津卫视"
    ],
    "福建频道": [
        "三明公共","三明新闻综合","云霄综合","厦门卫视","宁化电视一套","将乐综合","建宁综合",
        "德化新闻综合","新罗电视一套","晋江电视台","永安综合","永泰综合","泰宁新闻","漳州新闻综合",
        "漳浦综合","石狮综合","福州少儿","福州影院","福州生活","福州综合","霞浦综合","龙岩公共",
        "龙岩新闻综合","福建文体","福建新闻","福建电视剧","福建经济","福建综合","福建公共",
        "福建影剧","福建教育","福建生活"
    ],
    "港澳台频道": [
        "香港卫视","澳门卫视","凤凰卫视中文台","凤凰卫视资讯台","东森新闻台","东森财经台","中天综合台","中视经济台",
        "台湾公共电视","台湾卫视中文台","台湾民视新闻台","台湾中视","台湾华视"
    ],
    "电影台": [
        "CCTV6电影","电影频道","华夏电影","金鹰电影","北京电影","东方电影","南方电影","电影世界",
        "经典电影","经典影视","五星电影","五星高清电影"
    ],
    "咪咕直播": [
        "咪咕直播1","咪咕直播2","咪咕直播3","咪咕直播4","咪咕直播5"
    ],
    "动画/少儿": [
        "卡酷少儿","动漫世界","少儿频道","奥飞动漫","迪士尼频道","CCTV14少儿","CCTV15音乐"
    ],
    "经典剧场": [
        "CCTV8电视剧","经典电视剧","金鹰电视剧","影视经典","电影经典","电视剧频道"
    ]
}

# -------------------Read IP list-------------------
def read_ip_list(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"IP file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

# -------------------Get IP info (city + ISP)-------------------
def get_ip_info(ip):
    try:
        resp = requests.get(f"https://ip.taobao.com/outGetIpInfo?ip={ip}&accessKey=alibaba-inc", timeout=5)
        data = resp.json()
        if data.get("code") == 0 and data.get("data"):
            city = data["data"].get("city", "Unknown")
            isp = data["data"].get("isp", "Unknown")
            return f"{city},{isp}"
    except:
        pass
    return "Unknown,Unknown"

# -------------------Fetch IPTV JSON-------------------
def fetch_json(ipport):
    url = f"http://{ipport}{REQUEST_PATH}"
    for attempt in range(RETRY+1):
        try:
            resp = requests.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"[Error] Request failed: {url} -> {e} (retry {attempt}/{RETRY})")
            time.sleep(DELAY)
    return None

# -------------------Parse JSON data-------------------
def parse_data(json_data, ipport, ip_info):
    sources = {}
    if not json_data or "data" not in json_data:
        return sources
    for item in json_data["data"]:
        name = item.get("name", "未知")
        url_path = item.get("url", "")
        if url_path:
            full_url = f"http://{ipport}{url_path} ({ip_info})"
            if name not in sources:
                sources[name] = [full_url]
            else:
                sources[name].append(full_url)
    return sources

# -------------------Merge multiple sources-------------------
def merge_sources(all_sources, new_sources):
    for name, urls in new_sources.items():
        if name not in all_sources:
            all_sources[name] = urls
        else:
            all_sources[name].extend(urls)

# -------------------Save plain text-------------------
def save_txt(all_sources, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        for category, names in PROGRAM_CATEGORIES.items():
            f.write(f"📺{category},#genre#\n")
            for name in names:
                if name in all_sources:
                    for url in all_sources[name]:
                        f.write(f"{name},{url}\n")

# -------------------Save M3U8 playlist-------------------
def save_m3u(all_sources, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for category, names in PROGRAM_CATEGORIES.items():
            for name in names:
                if name in all_sources:
                    urls = all_sources[name]
                    for i, url in enumerate(urls):
                        f.write(f"#EXTINF:-1,{name} [源{i+1}]\n{url}\n")

# -------------------Main-------------------
def main():
    try:
        ip_list = read_ip_list(IP_FILE)
    except Exception as e:
        print(f"[Error] {e}")
        return

    all_sources = {}

    for ipport in ip_list:
        ip = ipport.split(":")[0]
        ip_info = get_ip_info(ip)
        print(f"Fetching: {ipport} ({ip_info})")
        json_data = fetch_json(ipport)
        sources = parse_data(json_data, ipport, ip_info)
        if sources:
            merge_sources(all_sources, sources)
            print(f"Got {len(sources)} programs")
        else:
            print(f"No data for: {ipport}")

    if all_sources:
        save_txt(all_sources, OUTPUT_FILE)
        save_m3u(all_sources, OUTPUT_M3U8)
        print(f"\nCompleted. Files generated:\n- {OUTPUT_FILE}\n- {OUTPUT_M3U8}\nTotal programs: {len(all_sources)}")
    else:
        print("\nNo IPTV sources found")

if __name__ == "__main__":
    main()
