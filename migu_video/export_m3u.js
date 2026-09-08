import fs from "node:fs";
import { channel } from "./utils/appUtils.js";

const baseDir = process.cwd();
const interfaceFile = `${baseDir}/interface.txt`;
const outputFile = `${baseDir}/migu.m3u`;
const txtFile = `${baseDir}/migu.txt`;

console.log("");
console.log("==============================================");
console.log("        咪咕真实播放地址 M3U 生成器");
console.log("==============================================");
console.log("");

if (!fs.existsSync(interfaceFile)) {
    console.log("错误：找不到 interface.txt");
    console.log(`文件：${interfaceFile}`);
    process.exit(1);
}

const content = fs.readFileSync(interfaceFile, "utf8");

/*
================================================
咪咕卫视频道,#genre#
================================================
*/
const satelliteChannels = new Set([
    "东方卫视",
    "江苏卫视",
    "广东卫视",
    "北京卫视",
    "辽宁卫视",
    "河北卫视",
    "江西卫视",
    "河南卫视",
    "陕西卫视",
    "大湾区卫视",
    "湖北卫视",
    "吉林卫视",
    "青海卫视",
    "东南卫视",
    "海南卫视",
    "海峡卫视",
    "中国农林卫视",
    "兵团卫视",
    "宁夏卫视",
    "重庆卫视",
    "三沙卫视",
    "黑龙江卫视"
]);

/*
================================================
咪咕央视频道,#genre#
================================================
*/
const cctvChannels = new Set([
    "CCTV1综合",
    "CCTV2财经",
    "CCTV3综艺",
    "CCTV4中文国际",
    "CCTV5体育",
    "CCTV5+体育赛事",
    "CCTV6电影",
    "CCTV7国防军事",
    "CCTV8电视剧",
    "CCTV9纪录",
    "CCTV10科教",
    "CCTV11戏曲",
    "CCTV12社会与法",
    "CCTV13新闻",
    "CCTV14少儿",
    "CCTV15音乐",
    "CCTV17农业农村",
    "CCTV4欧洲",
    "CCTV4美洲",
    "CGTN外语纪录",
    "CGTN阿拉伯语",
    "CGTN西班牙语",
    "CGTN法语",
    "CGTN俄语",
    "老故事",
    "发现之旅",
    "中学生",
    "CGTN"
]);

/*
================================================
根据频道名称自动判断分类
================================================
*/
function getGroup(name) {

    if (satelliteChannels.has(name)) {
        return "咪咕卫视频道,#genre#";
    }

    if (cctvChannels.has(name)) {
        return "咪咕央视频道,#genre#";
    }

    return "咪咕其他频道,#genre#";
}

/*
================================================
读取 interface.txt
================================================
*/

const regex = /EXTINF:([^\r\n]*)\r?\n\$\{replace\}\/(\d+)/g;

const channels = [];
let match;

while ((match = regex.exec(content)) !== null) {

    const info = match[1];
    const pid = match[2];

    let name = pid;

    const commaIndex = info.lastIndexOf(",");

    if (commaIndex !== -1) {
        name = info.substring(commaIndex + 1).trim();
    }

    const group = getGroup(name);

    channels.push({
        pid,
        info,
        name,
        group
    });
}

console.log(`发现频道：${channels.length} 个`);
console.log("");

if (channels.length === 0) {
    console.log("错误：interface.txt 中没有发现频道！");
    process.exit(1);
}

/*
================================================
统计分类
================================================
*/

let satelliteCount = 0;
let cctvCount = 0;
let otherCount = 0;

for (const item of channels) {

    if (item.group === "咪咕卫视频道,#genre#") {
        satelliteCount++;
    } else if (item.group === "咪咕央视频道,#genre#") {
        cctvCount++;
    } else {
        otherCount++;
    }
}

console.log("频道分类：");
console.log(`咪咕央视频道,#genre#：${cctvCount}`);
console.log(`咪咕卫视频道,#genre#：${satelliteCount}`);
console.log(`咪咕其他频道,#genre#：${otherCount}`);
console.log("");

/*
================================================
生成 M3U
================================================
*/

let m3u = "EXTM3U\r\n";
let txtGroups = {
    "咪咕央视频道,#genre#": [],
    "咪咕卫视频道,#genre#": [],
    "咪咕其他频道,#genre#": []
};

let success = 0;
let failed = 0;

for (let i = 0; i < channels.length; i++) {

    const item = channels[i];

    process.stdout.write(
        `[${i + 1}/${channels.length}] ${item.name} [${item.group}] ... `
    );

    try {

        const result = await channel(
            `/${item.pid}`,
            "",
            ""
        );

        if (
            result &&
            result.code === 302 &&
            result.playURL
        ) {

            /*
            修改 group-title
            但是保留：
            tvg-id
            tvg-name
            tvg-logo
            频道名称
            */

            let newInfo = item.info.replace(
                /group-title="[^"]*"/,
                `group-title="${item.group}"`
            );

            /*
            M3U
            */

            m3u += `#EXTINF:${newInfo}\r\n`;
            m3u += `${result.playURL}\r\n`;

            /*
            TXT
            */

            txtGroups[item.group].push(
    `${item.name},${result.playURL}`
);

            success++;

            console.log("成功");

        } else {

            failed++;

            console.log(
                `失败：${result?.desc || "没有播放地址"}`
            );
        }

    } catch (error) {

        failed++;

        console.log(
            `错误：${error.message || error}`
        );
    }
}

/*
================================================
写入文件
================================================
*/

fs.writeFileSync(outputFile, m3u, "utf8");
let txt = "";

for (const group of [
    "咪咕央视频道,#genre#",
    "咪咕卫视频道,#genre#",
    "咪咕其他频道,#genre#"
]) {

    txt += `#${group}\r\n`;

    for (const line of txtGroups[group]) {
        txt += `${line}\r\n`;
    }

    txt += "\r\n";
}

fs.writeFileSync(txtFile, txt, "utf8");

/*
================================================
完成
================================================
*/

console.log("");
console.log("==============================================");
console.log("                  完成");
console.log("==============================================");
console.log("");

console.log(`频道总数：${channels.length}`);
console.log(`获取成功：${success}`);
console.log(`获取失败：${failed}`);
console.log("");

console.log("分类统计：");
console.log(`咪咕央视频道,#genre#：${cctvCount}`);
console.log(`咪咕卫视频道,#genre#：${satelliteCount}`);
console.log(`咪咕其他频道,#genre#：${otherCount}`);
console.log("");

console.log(`M3U：${outputFile}`);
console.log(`TXT：${txtFile}`);
console.log("");

if (success > 0) {
    console.log("真实播放地址已经生成。");
} else {
    console.log("警告：没有获取到任何播放地址！");
}

console.log("");
console.log("5 秒后自动退出...");
console.log("");

setTimeout(() => {
    process.exit(0);
}, 5000);