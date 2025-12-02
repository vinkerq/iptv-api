import os
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from github import Github
import base64

# 仓库配置
REPO_OWNER = "vinkerq"
REPO_NAME = "iptv-api"
JIEMU_DIR = "jiemuyuan"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# 文件路径（输出到仓库根目录）
SOURCE_FILE = f"{JIEMU_DIR}/jiemuyuan.txt"
RESERVE_FILE = f"{JIEMU_DIR}/jiemubaoliu.txt"
EXCLUDE_FILE = f"{JIEMU_DIR}/jiemuyuanhmd.txt"
OUTPUT_TXT = "iptv4.txt"  # 根目录输出
OUTPUT_M3U = "iptv4.m3u"  # 根目录输出
LOG_FILE = "iptv4.log"

# URL黑名单
URL_BLACKLIST = [
    "https://stream1.freetv.fun/shan-tou-zong-he-14.m3u8",
    "https://stream1.freetv.fun/shan-tou-sheng-huo-1.m3u8"
]

# 节目分类配置
CHANNEL_GROUPS = {
    "汕头频道,#genre#": ["汕头经济生活","汕头经济生活","汕头综合","汕头新闻综合","揭阳公共频道","揭阳新闻综合"],
    "央视频道,#genre#": [
        "CCTV1","cctv01", "[BD]cctv1", "[HD]cctv1", "[SD]cctv1", "[BD]cctv-01", "[BD]cctv1-gq", "[BD]cctv1 8m1080",
        "CCTV2","cctv02", "[BD]cctv2", "[HD]cctv2", "[SD]cctv2", "[BD]cctv2-gq", "[BD]cctv2 4m1080", "[BD]cctv2 8m1080",
        "CCTV3","cctv03", "[BD]cctv3", "[HD]cctv3", "[SD]cctv3", "[BD]cctv-03", "[BD]cctv3-gq", "[BD]cctv3 8m1080",
        "CCTV4","cctv04", "[BD]cctv4", "[HD]cctv4", "[SD]cctv4", "[BD]cctv4k", "[BD]cctv4-gq", "[BD]cctv4 4m1080", "[BD]cctv4 8m1080", "[BD]cctv4-中央衛視", "[HD]cctv-4 中文国际",
        "CCTV5","cctv05", "[BD]cctv5", "[HD]cctv5", "[BD]cctv5-gq", "[BD]cctv5p", "[BD]cctv5 8m1080", "[BD]cctv5 plus *c", "[BD]cctv5 plus", "[BD]cctv5 plus -gq", "[BD]cctv5 plus 8m1080", "[BD]cctv-5 plus体育赛事",
        "CCTV6","cctv06", "[BD]cctv6", "[HD]cctv6", "[BD]cctv6-gq", "[BD]cctv6 *c", "[BD]cctv6 8m1080",
        "CCTV7","cctv07", "[BD]cctv7", "[HD]cctv7", "[BD]cctv7-gq", "[BD]cctv7hd", "[BD]cctv7 8m1080", "[BD]cctv7 4m1080",
        "CCTV8","cctv08", "[BD]cctv8", "[HD]cctv8", "[VGA]cctv8", "[BD]cctv8-gq", "[BD]cctv8 8m1080", "[SD]cctv8",
        "CCTV9","cctv09", "[BD]cctv9", "[HD]cctv9", "[SD]cctv9", "[VGA]cctv9", "[BD]cctv9-gq", "[BD]cctv9 4m1080", "[BD]cctv9 8m1080", "[BD]cctv9hd",
        "CCTV10", "cctv010","[BD]cctv10", "[SD]cctv10", "[BD]cctv-10", "[BD]cctv10-gq", "[BD]cctv10hd", "[BD]cctv10 8m1080", "[HD]cctv10",
        "CCTV11","cctv011", "[BD]cctv11", "[SD]cctv11", "[BD]cctv-11", "[BD]cctv11hd", "[BD]cctv11 3.5m1080", "[BD]cctv11 8m1080",
        "CCTV12","cctv012", "[BD]cctv12", "[HD]cctv12", "[VGA]cctv12", "[SD]cctv12", "[SD]cctv-12", "[BD]cctv12hd", "[BD]cctv12-gq", "[BD]cctv12 2.5m1080", "[BD]cctv12 8m1080",
        "CCTV13","cctv013", "[BD]cctv13", "[HD]cctv13", "[SD]cctv13", "[VGA]cctv13", "[BD]cctv13-gq", "[BD]cctv13 4m1080", "[SD]cctv-13",
        "CCTV14","cctv014", "[BD]cctv14", "[HD]cctv14", "[SD]cctv-14", "[BD]cctv14hd", "[BD]cctv14-gq", "[BD]cctv14 2.5m1080", "[BD]cctv14 8m1080", "[VGA]cctv14",
        "CCTV15","cctv015", "[BD]cctv15", "[HD]cctv15", "[SD]cctv-15", "[BD]cctv15-gq", "[BD]cctv15 1.5m1080", "[BD]cctv15 3.5m1080", "[BD]cctv15hd",
        "CCTV16","cctv016", "[BD]cctv16", "[BD]cctv-16", "[BD]cctv16hd", "[HD]cctv16",
        "CCTV17", "cctv017","[BD]cctv17", "[HD]cctv17", "[BD]cctv-17", "[BD]cctv17-gq", "[BD]cctv17hd", "[BD]cctv17 4m1080", "[BD]cctv17 8m1080",
        "CETV1", "CETV2", "CETV4", "CGTN英语", "CGTN西语", "CGTN俄语", "CGTN法语", "CGTN阿语", "CGTN纪录", "[SD]cctv第一剧场", "[BD]cctv风云足球"
    ],
    "广东频道,#genre#": [
        "[BD]东莞综合", "[HD]东莞新闻综合", "[BD]东莞新闻综合", "[BD]-汕头综合", "汕头综合", "[BD]-汕头生活", "汕头经济", "[BD]-揭阳综合",
        "[BD]广州南国都市", "广州南国都市", "[BD]广州法治", "广州法治", "[HD]广州法治", "[BD]广州竞赛", "广州竞赛", "[HD]广州竞赛",
        "[BD]广州新闻", "[SD]广州新闻", "[HD]广州新闻", "[HD]广州电视台新闻", "广州新闻", "[BD]广州综合", "[HD]广州综合", "广州综合",
        "[HD]广州影视", "广州影视", "[BD]佛山公共", "[BD]佛山综合", "佛山综合", "[BD]广西卫视", "[VGA]广西卫视", "[SD]广西卫视", "[HD]广西卫视",
        "[BD]广西国际", "广西影视", "南宁公共", "南宁新闻综合", "南宁文旅生活", "南宁影视娱乐", "[BD]广东少儿", "[BD]广东民生", "广东民生",
        "[BD]广东珠江", "广东珠江", "[HD]广东珠江", "[BD]广东经济科教", "广东经济科教", "[BD]广东综艺", "[BD]广东卫视", "[HD]广东卫视",
        "[BD]广东卫视 4m1080", "[BD]广东卫视 8m1080", "[BD]广东体育", "[HD]广东体育", "广东新闻", "[HD]广东新闻", "广东综艺", "嘉佳卡通",
        "广元综合", "[BD]广元综合", "[HD]广元综合"
    ],
    "港澳频道,#genre#": [
        "TVB Plus", "tvbplus", "TVB亚洲剧", "TVB亞洲劇", "tvbs亚洲", "tvbs亞洲", "tvbs-asia", "tvb asia", "tvb asia *c",
        "TVB星河(粤)", "TVB星河(粵)", "HD tvb星河", "TVB翡翠", "tvb翡翠", "翡翠", "翡翠台", "HD 翡翠", "BD 翡翠",
        "TVB黃金翡翠台[geo-blocked]", "TVB黃金翡翠台", "TVBS新闻HD", "now新聞", "Now 新聞臺", "无线新闻台", "HD 无线新闻", "BD 无线新闻", "無線新聞台", "無線新聞台[geo-blocked]",
        "TVBS欢乐台HD", "BD tvbs欢乐", "BD tvbs欢乐 *c", "明珠台(备)", "明珠臺(備)", "明珠", "明珠 *c", "HD 明珠", "SD 明珠",
        "星空卫视", "星空衛視國際頻道[geo-blocked]", "BD 星空国际", "凤凰卫视FHD", "凤凰卫视中文", "鳳凰衛視中文", "HD 凤凰中文", "SD 凤凰中文", "VGA 凤凰中文",
        "凤凰资讯HD", "凤凰资讯", "VGA 凤凰资讯", "SD 凤凰资讯", "HD 凤凰资讯", "鳳凰資訊HD", "凤凰电影", "鳳凰電影", "SD 凤凰电影",
        "凤凰香港", "鳳凰香港", "HD 凤凰香港", "BD 凤凰香港", "鳳凰香港[geo-blocked]", "澳视澳门", "澳視澳門", "BD 澳视澳门", "BD ช่อง 澳视澳门",
        "澳视综艺", "澳視綜藝", "BD 澳视综艺", "BD 澳門綜藝", "澳视资讯", "BD 澳视资讯", "BD ช่อง 澳视资讯", "澳视体育", "BD 澳视体育", "BD ช่อง 澳視體育", "BD 澳門體育",
        "澳门莲花", "澳門蓮花", "BD 澳门莲花", "澳门资讯", "澳門資訊", "BD 澳門資訊", "澳門MACAU", "澳门macau", "BD 澳门macau",
        "无线新闻台", "now 財經", "now財經", "now 財經臺", "HD viutv", "HD viutv 6", "BD viutv", "BD viutvsix", "HD viutvsix",
        "HD Now Sport 3 *sm", "BD now sports premier league 3", "BD now sports精選", "now Sports 2", "Sports Plus 1", "now Sports 3", "now Sports 3[geo-blocked]", "now Sports HD", "now Sports Prime",
        "BD movie music", "BD 悬疑movie", "HD 悬疑movie", "HD 剧集", "BD 剧集", "劇集1臺[geo-blocked]",
        "HD CCM *sm", "HD 爱奇艺 *c", "HD cgtn", "BD cgtn纪录", "BD cgtn西语", "BD cgtn阿语", "BD cgtn法语", "SD cgtn法语", "SD cgtn俄语", "BD cgtn", "SD cgtn", "BD cgtn俄语",
        "鳳凰香港", "鳳凰香港[geo-blocked]", "Animax(HK)", "Animax(HK)[geo-blocked]", "AXN(HK)", "AXN(HK)[geo-blocked]",
        "MOVIE MOVIE", "MOVIE MOVIE[geo-blocked]", "Popc[geo-blocked]", "CCTV1(RTHK33)", "CCTV1(RTHK33)[geo-blocked]",
        "HOY TV", "HOY TV[geo-blocked]", "snaap!", "BD snap", "甄子丹影視", "HD 甄子丹", "SD 甄子丹"
    ],
    "卫视频道,#genre#": [
        "北京卫视", "天津卫视", "HD 天津卫视", "SD 天津卫视", "BD 天津卫视", "BD 天津卫视 4m1080", "BD 天津卫视 8m1080",
        "东南卫视", "HD 东南卫视", "BD 东南卫视", "BD 东南卫视 8m1080", "东方卫视", "HD 东方卫视", "SD 东方卫视", "BD 东方卫视", "BD 东方卫视 8m1080", "BD 东方卫视 4m1080",
        "江苏卫视", "HD 江苏卫视", "BD 江苏卫视", "BD 江苏卫视 8m1080", "BD 江苏卫视 4m1080", "浙江卫视", "SD 浙江卫视", "VGA 浙江卫视", "HD 浙江卫视", "BD 浙江卫视 8m1080", "BD 浙江卫视 4m1080",
        "安徽卫视", "BD 安徽卫视", "HD 安徽卫视", "SD 安徽卫视", "BD 安徽卫视 8m1080", "河北卫视", "SD 河北卫视", "BD 河北卫视", "HD 河北卫视", "BD 河北卫视 8m1080",
        "河南卫视", "HD 河南卫视", "BD 河南卫视", "SD 河南卫视", "三沙卫视", "SD 三沙卫视", "HD 三沙卫视", "广东卫视",
        "深圳卫视", "HD 深圳卫视", "BD 深圳卫视", "BD 深圳卫视 8m1080", "BD 深圳卫视 4m1080", "湖北卫视", "HD 湖北卫视", "BD 湖北卫视", "BD 湖北卫视 8m1080", "BD 湖北卫视 4m1080",
        "湖南卫视", "HD 湖南卫视", "SD 湖南卫视", "BD 湖南卫视", "BD 湖南卫视 8m1080", "四川卫视", "HD 四川卫视", "SD 四川卫视", "BD 四川卫视",
        "重庆卫视", "HD 重庆卫视", "BD 重庆卫视", "江西卫视", "HD 江西卫视", "SD 江西卫视", "BD 江西卫视", "BD 江西卫视 4m1080",
        "山西卫视", "SD 山西卫视", "BD 山西卫视", "HD 山西卫视", "山东卫视", "HD 山东卫视", "BD 山东卫视", "BD 山东卫视 8m1080", "BD 山东卫视 4m1080",
        "山东教育卫视", "BD 山东教育卫视", "贵州卫视", "HD 贵州卫视", "SD 贵州卫视", "BD 贵州卫视", "BD 贵州卫视 8m1080",
        "海南卫视", "HD 海南卫视", "SD 海南卫视", "BD 海南卫视", "宁夏卫视", "HD 宁夏卫视", "SD 宁夏卫视", "BD 宁夏卫视",
        "陕西卫视", "SD 陕西卫视", "BD 陕西卫视", "VGA 陕西卫视", "HD 陕西卫视", "吉林卫视", "SD 吉林卫视", "HD 吉林卫视", "BD 吉林卫视",
        "辽宁卫视", "HD 辽宁卫视", "SD 辽宁卫视", "BD 辽宁卫视", "BD 辽宁卫视 8m1080", "黑龙江卫视", "HD 黑龙江卫视", "SD 黑龙江卫视", "BD 黑龙江卫视", "BD 黑龙江卫视 8m1080", "BD 黑龙江卫视 4m1080",
        "广西卫视", "云南卫视", "HD 云南卫视", "SD 云南卫视", "BD 云南卫视", "青海卫视", "HD 青海卫视", "SD 青海卫视", "BD 青海卫视",
        "新疆卫视", "HD 新疆卫视", "SD 新疆卫视", "BD 新疆卫视", "甘肃卫视", "HD 甘肃卫视", "SD 甘肃卫视", "BD 甘肃卫视",
        "西藏卫视", "SD 西藏卫视", "BD 西藏卫视", "内蒙古卫视", "SD 内蒙古卫视", "HD 内蒙古卫视", "BD 内蒙古卫视", "BD 内蒙古蒙语卫视",
        "兵团卫视", "SD 兵团卫视", "HD 兵团卫视", "BD 兵团卫视", "延边卫视", "SD 延边卫视", "BD 延边卫视",
        "厦门卫视", "SD 厦门卫视", "BD 厦门卫视", "康巴卫视", "大湾区卫视", "星空卫视", "海峡卫视", "VGA 海峡卫视",
        "香港卫视", "上海卫视", "BD 上海卫视"
    ],
    "数字频道,#genre#": [
        "CHC动作电影","CHC家庭影院","周星驰专辑[geo-blocked]","洪金宝[geo-blocked]","剧集1台[geo-blocked]","电影频道","淘电影","黑莓电影","黑莓动画","纪实人文","超级电视剧","超级电影",
        "哒啵赛事","金牌综艺","精品体育","咪咕体育","爱情喜剧","精品萌宠","睛彩竞技","睛彩篮球","睛彩青少",
        "卡酷少儿","金鹰卡通","优漫卡通","哈哈炫动","超级体育","超级综艺","潮妈辣婆","东北热剧","动作电影",
        "古装剧场","海外剧场","欢乐剧场","家庭剧场","惊悚悬疑","精品大剧","精品纪录","军旅剧场","军事评论",
        "明星大片","农业致富","武搏世界","炫舞未来","怡伴健康","中国功夫","纪实科教","宿州新闻综合","乌海新闻综合"
    ],
    "台湾频道,#genre#": [
        "三立戏剧", "三立戏剧 *c", "三立新聞", "三立新闻[geo-blocked]", "三立综合", "三立综合 *c",
        "三立台湾", "三立台灣", "三立台湾 *c", "三立都会", "三立都會", "中天亚洲FHD", "中天亚洲", "中天亚洲 *c",
        "中天娱乐HD", "中天娱乐HD[geo-blocked]", "中天娱乐", "中天娛樂", "中天娱乐 *c", "中天新闻FHD", "中天新闻FHD[geo-blocked]", "中天新闻", "中天新聞", "中天新闻 *c",
        "中天综合HD", "中天综合HD[geo-blocked]", "中天综合", "中天綜合", "中天综合 *c", "中视", "中視", "中视HD[geo-blocked]", "中视HD", "中视 *c", "中视新闻FHD", "中视新闻台", "中视新闻台[geo-blocked]", "中视新闻", "中视新闻 *c", "中视经典", "中视经典",
        "亚洲旅游台", "亚洲旅游", "亚洲旅游 *c", "亞洲旅遊", "人间卫视", "人間衛視",
        "八大娱乐台", "八大娱乐", "八大娱乐 *c", "八大戏剧HD", "八大戏剧", "八大戲劇", "八大戏剧 *c", "八大综合", "八大綜合", "八大综合 *c", "八大第一 *c",
        "公视HD", "公视台语台", "公视2 *c", "公視", "公视 *c", "公视", "台视HD[geo-blocked]", "台视HD", "台视新闻FHD", "台视新闻台", "台视新闻", "台视新闻 *c", "台视综合", "台视综合 *c", "台视 *c", "台视",
        "唯心电视", "壹新聞", "一新闻[geo-blocked]", "大爱", "大爱二台", "大愛二", "大爱电视台", "大爱电视台[geo-blocked]", "大愛電視", "大愛電視", "大爱1 *c", "大爱2 *c",
        "好莱坞电影", "好萊塢電影", "好讯息[geo-blocked]", "好讯息", "好讯息 2[geo-blocked]", "好讯息 2", "好消息", "好消息2", "好消息 2", "好消息 2 *c",
        "寰宇新闻", "寰宇新闻[geo-blocked]", "寰宇新闻FHD", "寰宇新闻 *c", "寰宇财经", "寰宇财经 *c",
        "年代新闻HD", "年代新闻HD[geo-blocked]", "年代新聞", "年代新闻 *c",
        "东森幼幼", "东森幼幼[geo-blocked]", "東森幼幼", "东森幼幼yoyo *c", "东森幼幼台",
        "东森戏剧", "东森戏剧[geo-blocked]", "東森戲劇", "东森戏剧 *c",
        "东森新闻HD", "东森新闻台", "东森新闻", "東森新聞", "东森新闻 *c",
        "东森洋片", "东森洋片 *c", "东森综合", "东森综合[geo-blocked]", "東森綜合", "东森综合 *c",
        "东森美洲", "东森美洲2", "东森美洲新闻台", "东森卫视",
        "东森财经[geo-blocked]", "东森财经", "东森财经新闻", "东森财经新闻 *c", "東森財經",
        "东森超视", "东森超视[geo-blocked]", "东森超视34.5", "东森电影", "东森电影 *c",
        "民视", "民視", "民视HD[geo-blocked]", "民视HD", "民视新闻 HD", "民视新闻 HD[geo-blocked]", "民视新闻HD", "民视新闻", "民视新闻 *c", "民视台湾台", "民视台湾", "民视台湾 *c",
        "纬来戏剧", "纬来戏剧[geo-blocked]", "緯來戲劇", "纬来日本", "纬来日本[geo-blocked]", "緯來日本", "纬来精彩", "纬来精彩[geo-blocked]", "纬来综合", "纬来综合[geo-blocked]", "緯來綜合", "纬来育乐", "纬来育乐[geo-blocked]", "緯來育樂", "纬来电影", "纬来电影[geo-blocked]", "緯來電影", "纬来体育", "纬来体育[geo-blocked]", "緯來體育", "纬来体育",
        "美亚电影台[TW]", "美亚电影2", "美亚电影 *c", "美亚电影",
        "华视", "华视HD[geo-blocked]", "华视HD", "華視", "華視 *c", "华视 *c",
        "靖天卡通", "靖天卡通 *c", "靖天国际 *c",
        "非凡商业[geo-blocked]", "非凡商业", "非凡商業", "非凡新闻HD", "非凡新闻", "非凡新闻 *c",
        "龙华偶像[geo-blocked]", "龙华偶像", "龍華偶像劇", "龙华偶像 *c", "龙华卡通[geo-blocked]", "龍華卡通", "龙华戏剧", "龙华戏剧[geo-blocked]", "龙华戏剧 *c", "龍華戲劇", "龙华日韩[geo-blocked]", "龙华日韩", "龍華日韓劇", "龙华经典[geo-blocked]", "龙华经典", "龙华经典 *c", "龙华电影", "龙华电影[geo-blocked]", "龍華電影", "龙华洋片 *c"
    ],
    "北京/南京频道,#genre#": [
        "[BD]北京卫视", "[HD]北京卫视", "[VGA]北京卫视", "[BD]北京卫视 8m1080", "[HD]南京少儿", "[BD]南京新闻综合",
        "北京青年", "北京卡酷少儿", "北京影视", "北京财经", "北京生活", "北京新闻", "北京文艺"
    ],
    "重庆频道,#genre#": [
        "重庆卫视", "重庆卫视[geo-blocked]", "重庆科教", "重庆科教[geo-blocked]", "BD 重庆科教高清", "BD 江津新闻综合"
    ],
    "内蒙古频道,#genre#": [
        "内蒙古文体娱乐", "内蒙古经济生活", "内蒙古蒙语", "内蒙古蒙语文化", "内蒙古卫视", "内蒙古农牧",
        "BD 内蒙古文体娱乐", "BD 内蒙古经济生活", "BD 内蒙古蒙语文化", "BD 内蒙古农牧"
    ],
    "上海频道,#genre#": [
        "上海新闻综合[geo-blocked]", "上海卫视", "上海都市[geo-blocked]", "BD 上海新闻综合", "BD 上海都市", "BD 上海第一财经"
    ],
    "浙江频道,#genre#": [
        "浙江卫视", "浙江卫视[geo-blocked]", "BD 浙江衛視", "浙江国际", "浙江国际[geo-blocked]", "BD 浙江国际",
        "浙江少儿", "浙江少儿频道", "BD 浙江少儿", "VGA 浙江少儿", "浙江教育科技", "BD 浙江教育", "BD 浙江教科", "HD 浙江教育", "VGA 浙江教育",
        "浙江新闻", "浙江新闻[geo-blocked]", "BD 浙江新闻", "VGA 浙江新闻", "浙江民生休閒", "浙江民生休閒[geo-blocked]", "BD 浙江民生", "VGA 浙江民生", "VGA 浙江民生休闲",
        "浙江经济生活", "浙江经济生活[geo-blocked]", "BD 浙江经济生活", "HD 浙江经济生活", "VGA 浙江经济生活", "BD 浙江经济", "HD 浙江经济",
        "BD 浙江公共新闻", "BD 浙江钱江", "VGA 浙江钱江都市", "BD 上虞新闻综合", "BD 浙江｜上虞新闻综合",
        "HD 萧山新闻综合", "BD 象山新闻综合", "BD 新昌新聞綜合", "BD 台州新闻综合",
        "BD 绍兴文化影视", "HD 绍兴文化影视", "HD 绍兴文化", "HD 绍兴文化影院", "HD 绍兴公共频道", "HD 绍兴公共", "SD 绍兴公共",
        "HD 绍兴新闻综合", "SD 绍兴新闻综合", "SD 绍兴新闻"
    ],
    "云南频道,#genre#": [
        "云南娱乐", "云南娱乐[geo-blocked]", "HD 云南娱乐", "云南影视", "云南影视[geo-blocked]", "HD 云南影视",
        "云南卫视", "云南卫视[geo-blocked]", "HD 云南卫视", "云南都市", "云南都市[geo-blocked]", "HD 云南都市",
        "HD 丽江新闻综合", "BD 大理新闻综合", "BD 文山新闻综合"
    ],
    "福建频道,#genre#": [
        "福建综合", "福建新闻", "福建公共", "福建旅游", "福建体育", "福建少儿", "BD 厦门卫视", "BD 廈門衛視"
    ],
    "江苏频道,#genre#": [
        "江苏城市", "江苏城市[geo-blocked]", "BD 江苏城市", "BD 江苏影视", "BD 江苏体育", "HD 江苏卫视", "BD 江苏卫视", "BD 江苏卫视[geo-blocked]", "BD 江苏卫视(B)",
        "BD 江苏体育休閒[geo-blocked]", "BD 南京新闻综合", "HD 宜兴新闻", "HD 无锡宜兴新闻", "HD 南京少儿",
        "BD 南通新闻综合", "BD 苏州新闻综合", "HD 苏州文化生活", "HD 苏州生活资讯", "BD 苏州社会经济", "HD 苏州电影娱乐信息"
    ],
    "四川频道,#genre#": [
        "四川卫视", "HD 四川卫视", "SD 四川卫视", "四川妇女儿童", "BD 四川妇女", "四川经济", "BD 四川经济",
        "四川科教", "BD 四川科教", "四川影视文艺", "BD 四川影视", "四川新闻资讯", "BD 四川新闻",
        "四川文化旅游", "BD 四川文化", "BD 成都公共", "BD 成都影视", "BD 成都新闻",
        "HD 成都简阳新闻综合", "HD 简阳新闻综合", "HD 南充科教生活", "HD 南充综合", "BD 南充综合",
        "BD 绵阳新闻", "BD 绵阳科技", "BD 眉山综合", "HD 眉山丹棱综合", "BD 川影视"
    ],
    "河南频道,#genre#": [
        "河南新闻", "河南民生", "河南民生[geo-blocked]", "BD 河南民生", "河南卫视", "河南卫视[geo-blocked]", "BD 河南都市", "河南都市", "河南都市[geo-blocked]",
        "BD 平舆新闻综合频道", "BD 沁阳新闻综合频道", "BD 泌阳新闻综合频道", "BD 新野新闻综合频道", "BD 新县新闻综合",
        "BD 新乡综合", "BD 新乡县新闻综合频道", "BD 郸城新闻综合", "BD 泌阳新闻综合", "BD 登封新闻综合频道",
        "BD 封丘新闻综合", "BD 晋城新闻", "BD 晋城公共", "BD 巩义新闻综合", "BD 义马新闻综合", "BD 获嘉新闻综合频道"
    ],
    "湖南频道,#genre#": [
        "湖南娱乐", "湖南娱乐", "HD 湖南娱乐", "VGA 湖南娱乐", "BD 湖南娱乐", "湖南电影", "HD 湖南电影",
        "湖南电视剧", "HD 湖南电视剧", "BD 湖南电视剧", "湖南都市", "HD 湖南都市", "BD 湖南都市", "湖南都市[geo-blocked]",
        "湖南经视", "HD 湖南经视", "BD 湖南经视", "VGA 湖南经视", "湖南教育", "HD 湖南教育", "湖南公共", "HD 湖南公共",
        "湖南国际", "VGA 湖南国际", "BD 湖南衛視", "HD 湖南卫视", "湖南卫视[geo-blocked]"
    ],
    "湖北频道,#genre#": [
        "十堰新闻", "HD 十堰经济旅游", "十堰经济旅游", "湖北影视", "湖北新闻综合", "湖北生活", "湖北卫视", "湖北卫视[geo-blocked]"
    ],
    "黑龙江频道,#genre#": [
        "黑龙江少儿", "黑龙江影视", "SD 黑龙江影视", "黑龙江文体", "黑龙江新闻法治", "SD 黑龙江新闻法治", "黑龙江都市",
        "哈尔滨新闻综合", "VGA 哈尔滨娱乐", "VGA 哈尔滨影视", "VGA 哈尔滨新闻综合", "VGA 哈尔滨新闻", "VGA 哈尔滨生活",
        "VGA 黑龙江哈尔滨都市资讯", "VGA 哈尔滨资讯", "BD 黑龙江卫视", "黑龙江卫视", "黑龙江卫视[geo-blocked]",
        "BD 黑龙江卫视 8m1080", "BD 黑龙江卫视 4m1080", "BD 嘉佳卡通", "SD 嘉佳卡通"
    ]
}

# GitHub仓库操作函数
def get_github_repo():
    g = Github(GITHUB_TOKEN)
    return g.get_repo(f"{REPO_OWNER}/{REPO_NAME}")

def read_github_file(repo, file_path):
    try:
        file_content = repo.get_contents(file_path)
        return base64.b64decode(file_content.content).decode("utf-8")
    except Exception as e:
        print(f"警告：未找到文件 {file_path} → {str(e)}")
        return ""

def write_github_file(repo, file_path, content, commit_msg):
    try:
        existing_file = repo.get_contents(file_path)
        repo.update_file(existing_file.path, commit_msg, content, existing_file.sha)
    except:
        repo.create_file(file_path, commit_msg, content)
    print(f"✅ 已更新：{file_path}")

# 工具函数
def download_channel_source():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://freetv.fun/",
        "Connection": "keep-alive"
    }
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    
    try:
        response = session.get("https://freetv.fun/test_channels_original_new.txt?key=1831", 
                              headers=headers, timeout=30, verify=False)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"⚠️  远程更新失败 → {str(e)}")
        return None

def get_core_channel_name(name: str) -> str:
    core_name = re.sub(r'^(?:\[(?:BD|HD|VGA|SD)\]\s*|(?:BD|HD|VGA|SD)\s+|-\s*)', '', name, flags=re.IGNORECASE)
    core_name = re.sub(r'\s*-gq$|\s*\d+m\d+$|\s*\*c$|\s*\*sm$|\s*\(备\)$|\s*\(粤\)$|\s*\(粵\)$', '', core_name, flags=re.IGNORECASE)
    core_name = re.sub(r'\[geo-blocked\]', '', core_name)
    core_name = re.sub(r'cctv0*(\d+)', r'CCTV\1', core_name, flags=re.IGNORECASE)
    core_name = re.sub(r'cctv(\d+)', r'CCTV\1', core_name, flags=re.IGNORECASE)
    core_name = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]+', '', core_name).strip()
    return core_name

def load_exclude_sources(repo):
    exclude_cores = set()
    exclude_urls = set()
    exclude_content = read_github_file(repo, EXCLUDE_FILE)
    
    for line in exclude_content.splitlines():
        line = line.strip()
        if not line or "," not in line:
            continue
        name, url = line.split(",", 1)
        exclude_cores.add(get_core_channel_name(name))
        exclude_urls.add(url.strip())
    
    return exclude_cores, exclude_urls

def load_sources(repo, exclude_cores, exclude_urls):
    sources = {}
    all_exclude_urls = exclude_urls.union(set(URL_BLACKLIST))
    
    source_content = read_github_file(repo, SOURCE_FILE)
    for line in source_content.splitlines():
        line = line.strip()
        if not line or "," not in line:
            continue
        name, url = line.split(",", 1)
        core_name = get_core_channel_name(name)
        url = url.strip()
        if core_name not in exclude_cores and url not in all_exclude_urls:
            if core_name not in sources:
                sources[core_name] = []
            if url not in sources[core_name]:
                sources[core_name].append(url)
    
    reserve_content = read_github_file(repo, RESERVE_FILE)
    for line in reserve_content.splitlines():
        line = line.strip()
        if not line or "," not in line:
            continue
        name, url = line.split(",", 1)
        core_name = get_core_channel_name(name)
        url = url.strip()
        if core_name not in exclude_cores and url not in all_exclude_urls:
            if core_name not in sources:
                sources[core_name] = []
            if url not in sources[core_name]:
                sources[core_name].append(url)
    
    return sources

def find_best_match_group(channel_name):
    core_name = get_core_channel_name(channel_name).lower()
    category_keywords = {
        "cctv": "央视频道,#genre#", "cetv": "央视频道,#genre#", "cgnt": "央视频道,#genre#",
        "汕头": "汕头频道,#genre#", "广东": "广东频道,#genre#", "广州": "广东频道,#genre#", "东莞": "广东频道,#genre#", "佛山": "广东频道,#genre#", "广西": "广东频道,#genre#",
        "翡翠": "港澳频道,#genre#", "tvb": "港澳频道,#genre#", "凤凰": "港澳频道,#genre#", "澳视": "港澳频道,#genre#", "澳门": "港澳频道,#genre#",
        "三立": "台湾频道,#genre#", "中天": "台湾频道,#genre#", "东森": "台湾频道,#genre#", "民视": "台湾频道,#genre#", "台视": "台湾频道,#genre#",
        "北京": "北京/南京频道,#genre#", "南京": "北京/南京频道,#genre#", "重庆": "重庆频道,#genre#", "内蒙古": "内蒙古频道,#genre#",
        "上海": "上海频道,#genre#", "浙江": "浙江频道,#genre#", "云南": "云南频道,#genre#", "福建": "福建频道,#genre#", "江苏": "江苏频道,#genre#",
        "四川": "四川频道,#genre#", "河南": "河南频道,#genre#", "湖南": "湖南频道,#genre#", "湖北": "湖北频道,#genre#", "黑龙江": "黑龙江频道,#genre#",
        "卫视": "卫视频道,#genre#", "电影": "数字频道,#genre#", "卡通": "数字频道,#genre#", "少儿": "数字频道,#genre#"
    }
    for keyword, group in category_keywords.items():
        if keyword in core_name:
            return group
    return "卫视频道,#genre#"

# 主函数
def main():
    repo = get_github_repo()
    log_lines = []
    
    # 更新主节目源
    new_source = download_channel_source()
    if new_source:
        write_github_file(repo, SOURCE_FILE, new_source, "Update jiemuyuan.txt from remote")
        log_lines.append("📥 已从远程更新主节目源")
    
    # 加载排除列表
    exclude_cores, exclude_urls = load_exclude_sources(repo)
    all_exclude_urls = exclude_urls.union(set(URL_BLACKLIST))
    log_lines.append(f"🚫 排除统计：{len(exclude_cores)}个节目名，{len(all_exclude_urls)}个URL")
    log_lines.append(f"黑名单URL：{URL_BLACKLIST}")
    
    # 加载节目源
    all_sources = load_sources(repo, exclude_cores, exclude_urls)
    log_lines.append(f"📺 加载节目源：{len(all_sources)}个核心节目")
    
    # 生成输出内容
    txt_out = []
    m3u_out = ["#EXTM3U"]
    processed = set()
    
    # 处理分类节目
    for group_title, channel_list in CHANNEL_GROUPS.items():
        txt_out.append(group_title)
        log_lines.append(f"\n📋 分类：{group_title}")
        channel_core_map = {}
        
        for ch in channel_list:
            core_name = get_core_channel_name(ch)
            if core_name not in exclude_cores and core_name in all_sources:
                if core_name not in channel_core_map:
                    channel_core_map[core_name] = []
                channel_core_map[core_name].append(ch)
        
        for core_name, original_names in channel_core_map.items():
            if core_name in processed:
                continue
            urls = all_sources[core_name]
            for url in urls:
                txt_out.append(f"{core_name},{url}")
                m3u_out.append(f'#EXTINF:-1 tvg-name="{core_name}",{core_name}')
                m3u_out.append(url)
            log_lines.append(f"  ✅ {original_names} → {core_name}（{len(urls)}条源）")
            processed.add(core_name)
        txt_out.append("")
    
    # 处理未分类节目
    unprocessed = set(all_sources.keys()) - processed
    if unprocessed:
        log_lines.append(f"\n🔍 发现未分类节目：{unprocessed}")
        for core_name in unprocessed:
            group = find_best_match_group(core_name)
            urls = all_sources[core_name]
            if group in txt_out:
                idx = txt_out.index(group) + 1
                while idx < len(txt_out) and txt_out[idx].strip() != "":
                    idx += 1
            else:
                txt_out.append(group)
                idx = len(txt_out)
            for url in urls:
                txt_out.insert(idx, f"{core_name},{url}")
                m3u_out.append(f'#EXTINF:-1 tvg-name="{core_name}",{core_name}')
                m3u_out.append(url)
                idx += 1
            log_lines.append(f"  🆕 自动分类：{core_name} → {group}（{len(urls)}条源）")
    
    # 写入结果到仓库根目录
    write_github_file(repo, OUTPUT_TXT, "\n".join(txt_out), "Update iptv4.txt")
    write_github_file(repo, OUTPUT_M3U, "\n".join(m3u_out), "Update iptv4.m3u")
    write_github_file(repo, LOG_FILE, "\n".join(log_lines), "Update iptv4.log")
    
    log_lines.append(f"\n✅ 处理完成！输出到仓库根目录：{OUTPUT_TXT}、{OUTPUT_M3U}")
    print("\n".join(log_lines))

if __name__ == "__main__":
    main()
