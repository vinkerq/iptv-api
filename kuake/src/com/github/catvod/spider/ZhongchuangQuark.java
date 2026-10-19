package com.github.catvod.spider;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import com.github.catvod.crawler.Spider;
import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.FilterInputStream;
import java.net.HttpURLConnection;
import java.net.InetAddress;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TimeZone;
import java.util.UUID;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 无第三方服务器的 TVBox/CatVod 夸克盘搜爬虫「源工程实验版」。
 *
 * 安全边界：登录 Cookie 只保存在当前设备的应用私有 SharedPreferences；
 * 只能清理此爬虫明确建立并记账的临时文件夹；不会把 Cookie 写到 JSON/日志。
 *
 * 注意：只有 CatVod Java Spider 实现兼容此 ABI、支持本地 proxy()，才能使用播放代理。
 * 普通 Spider 接口不提供播放器退出事件；此类通过 proxy 活动时间和重启兜底清理。
 */
public final class ZhongchuangQuark extends Spider {
    static final String SITE = "https://www.zhongchuangwl.com";
    static final String SESS_PREF = "zhongchuang_quark_private_v1";
    private static final Pattern SEARCH_NODE = Pattern.compile("(?is)<div\\s+class=[\"']pss[\"'][^>]*>\\s*<h2>\\s*<a\\s+([^>]*)>(.*?)</a>");
    private static final Pattern ATTR_TITLE = Pattern.compile("(?is)\\btitle=[\"']([^\"']*)[\"']");
    private static final Pattern ATTR_HREF = Pattern.compile("(?is)\\bhref=[\"']([^\"']*)[\"']");
    private static final Pattern PANLINK = Pattern.compile("https?://(?:www\\.)?zhongchuangwl\\.com/go/\\?gourl=[^\"'\\s<>]+|https://pan\\.quark\\.cn/s/[A-Za-z0-9_-]+", Pattern.CASE_INSENSITIVE);
    private static final Pattern SEARCH_ID = Pattern.compile("^https://www\\.zhongchuangwl\\.com/n/([A-Za-z0-9]+)\\.html$");
    private static final Pattern SHARE_ID = Pattern.compile("^https://pan\\.quark\\.cn/s/([A-Za-z0-9_-]{5,80})/?(?:\\?.*)?$");
    private static final Pattern GATE = Pattern.compile("(?:const|let|var)\\s+hash\\s*=\\s*['\"]([a-fA-F0-9]{32})['\"]");
    private static final Pattern VIDEO_EXT = Pattern.compile("(?i)\\.(mp4|mkv|mov|m4v|avi|webm|ts|m2ts|flv|wmv|mpeg|mpg)$");
    private static final long STALE_MS = 12L * 3600_000; // 任务内存保留上限
    private static final long STREAM_IDLE_MS = 30L * 60_000; // 无流量 30 分钟后清理
    private static final long CLOSE_GRACE_MS = 3L * 60_000; // 明确退出后 3 分钟
    private static final long ORPHAN_GRACE_MS = 60L * 60_000; // 崩溃重启的孤儿目录 1 小时

    private Context app;
    private Context uiContext;
    private SharedPreferences prefs;
    private final ScheduledExecutorService workers = Executors.newSingleThreadScheduledExecutor(r -> {
        Thread t = new Thread(r, "quark-local-cleanup");
        t.setDaemon(true);
        return t;
    });
    private boolean cleaningScheduled;
    private final Map<String, Play> playing = new LinkedHashMap<>();
    private String base = SITE;
    private volatile boolean loginShowing;

    private static final class Video {
        String share, fid, token, stoken, parent, path, name;
        Video(String share, String fid, String token, String stoken, String parent, String path, String name) {
            this.share = share; this.fid = fid; this.token = token;
            this.stoken = stoken; this.parent = parent; this.path = path; this.name = name;
        }
        JSONObject json() throws Exception {
            return new JSONObject().put("s", share).put("f", fid).put("t", token).put("p", parent)
                    .put("d", path).put("n", name);
        }
    }
    private static final class Play {
        Video video;
        long last = System.currentTimeMillis();
        String url, tmpFolder;
        boolean closed;
        int activeStreams;
        Play(Video video) { this.video = video; }
    }

    @Override public void init(Context context, String extend) {
        this.uiContext = context;
        this.app = context.getApplicationContext();
        this.prefs = app.getSharedPreferences(SESS_PREF, Context.MODE_PRIVATE);
        try {
            if (extend != null && extend.startsWith("https://www.zhongchuangwl.com")) base = SITE;
        } catch (Exception ignored) { }
        // 此操作不阻塞 UI；重启后只处理之前明确记账的临时目录。
        workers.execute(this::cleanupSafely);
        synchronized (this) {
            if (!cleaningScheduled) {
                cleaningScheduled = true;
                workers.scheduleWithFixedDelay(this::cleanupSafely, 90, 90, TimeUnit.SECONDS);
            }
        }
    }

    @Override public String homeContent(boolean filter) throws Exception {
        JSONArray categories = new JSONArray().put(new JSONObject().put("type_id", "quark")
                .put("type_name", "夸克盘搜"));
        return new JSONObject().put("class", categories).toString();
    }

    @Override public String categoryContent(String tid, String pg, boolean filter, HashMap<String, String> extend) throws Exception {
        return new JSONObject().put("list", new JSONArray()).put("page", 1).put("pagecount", 1).toString();
    }

    @Override public String searchContent(String key, boolean quick) throws Exception {
        return searchContent(key, quick, "1");
    }

    @Override public String searchContent(String key, boolean quick, String pg) throws Exception {
        int page;
        try { page = Math.min(20, Math.max(1, Integer.parseInt(pg))); } catch (Exception e) { page = 1; }
        String url = base + "/s/" + encPath(key) + "/" + (page == 1 ? "" : "pn" + page + ".html");
        String html = siteGet(url);
        JSONArray list = new JSONArray();
        Matcher m = SEARCH_NODE.matcher(html);
        Set<String> seen = new HashSet<>();
        while (m.find() && list.length() < 100) {
            String href = attr(ATTR_HREF, m.group(1));
            String title = attr(ATTR_TITLE, m.group(1));
            if (href.startsWith("/")) href = base + href;
            Matcher path = SEARCH_ID.matcher(href);
            if (!path.matches() || !seen.add(path.group(1))) continue;
            if (title.isEmpty()) title = plain(m.group(2));
            if (title.isEmpty()) continue;
            list.put(new JSONObject().put("vod_id", path.group(1)).put("vod_name", title)
                    .put("vod_pic", "").put("vod_remarks", "夸克网盘"));
        }
        return new JSONObject().put("list", list).put("page", page)
                .put("pagecount", list.length() == 0 ? page : page + 1).toString();
    }

    @Override public String detailContent(List<String> ids) throws Exception {
        if (ids == null || ids.isEmpty() || !ids.get(0).matches("[A-Za-z0-9]{1,35}")) return message("无效的资源ID");
        String id = ids.get(0);
        String html = siteGet(base + "/n/" + id + ".html");
        String title = match(html, "(?is)<h1[^>]*>(.*?)</h1>");
        title = plain(title); if (title.isEmpty()) title = "夸克盘搜";
        JSONObject vod = new JSONObject().put("vod_id", id).put("vod_name", title).put("vod_pic", "");
        List<String> shareIds = new ArrayList<>();
        Matcher links = PANLINK.matcher(unescape(html));
        while (links.find()) {
            String link = links.group();
            String actual = link.contains("/go/") ? decodeGo(link) : link;
            Matcher sm = SHARE_ID.matcher(actual);
            if (sm.matches() && !shareIds.contains(sm.group(1))) shareIds.add(sm.group(1));
        }
        if (shareIds.isEmpty()) {
            vod.put("vod_content", "未在详情页识别到夸克分享地址");
            return new JSONObject().put("list", new JSONArray().put(vod)).toString();
        }
        LinkedHashMap<String, List<String>> groups = new LinkedHashMap<>();
        List<String> errors = new ArrayList<>();
        int no = 0;
        for (String share : shareIds) {
            ++no;
            try {
                for (Video v : listVideos(share)) {
                    String group = shareIds.size() > 1 ? "分享" + no + " · " + v.path : v.path;
                    if (group.isEmpty()) group = "根目录";
                    if (!groups.containsKey(group)) groups.put(group, new ArrayList<>());
                    String data = android.util.Base64.encodeToString(v.json().toString().getBytes(StandardCharsets.UTF_8),
                            android.util.Base64.URL_SAFE | android.util.Base64.NO_WRAP);
                    groups.get(group).add(escapeTitle(v.name) + "$quark://" + data);
                }
            } catch (Exception e) {
                errors.add("分享" + no + "：" + publicMessage(e));
            }
        }
        if (groups.isEmpty()) {
            vod.put("vod_play_from", "夸克分享")
                    .put("vod_play_url", "扫码后重试$" + "https://pan.quark.cn/s/" + shareIds.get(0))
                    .put("vod_content", "尚未列出视频：" + String.join("；", errors));
        } else {
            List<String> names = new ArrayList<>(), urls = new ArrayList<>();
            int n = 0;
            for (Map.Entry<String, List<String>> entry : groups.entrySet()) {
                names.add(escapeTitle(entry.getKey()));
                Collections.sort(entry.getValue(), ZhongchuangQuark::naturalCompare);
                urls.add(String.join("#", entry.getValue())); n += entry.getValue().size();
            }
            vod.put("vod_play_from", String.join("$$$", names));
            vod.put("vod_play_url", String.join("$$$", urls));
            vod.put("vod_remarks", n + " 个视频 · " + groups.size() + " 个文件夹");
            vod.put("vod_content", "真实文件名选集，按网盘文件夹分组。" + String.join("；", errors));
            if (n == 1) vod.put("vod_name", groups.values().iterator().next().get(0).split("\\$", 2)[0]);
        }
        return new JSONObject().put("list", new JSONArray().put(vod)).toString();
    }

    @Override public String playerContent(String flag, String id, List<String> vipFlags) throws Exception {
        if (id == null || !id.startsWith("quark://")) return message("不是本源的视频文件");
        Video v;
        try {
            JSONObject j = new JSONObject(new String(android.util.Base64.decode(id.substring(8), android.util.Base64.URL_SAFE),
                    StandardCharsets.UTF_8));
            v = new Video(j.getString("s"), j.getString("f"), j.optString("t"), "",
                    j.optString("p", "0"), j.optString("d"), j.optString("n"));
        } catch (Exception e) { return message("播放文件信息已失效，请重新打开详情页"); }
        if (!loggedIn()) {
            showLoginDialog();
            return message("请完成本机夸克扫码登录，成功后重新点击本集");
        }
        Play play = new Play(v);
        String key = UUID.randomUUID().toString().replace("-", "");
        synchronized (playing) { playing.put(key, play); }
        try {
            // 经本地 CatVod proxy 代理流媒体，以便支持 Range/判断活跃与自动清理。
            Map<String, String> params = new HashMap<>();
            params.put("quark_play", key);
            String local = getProxyUrl(params);
            if (local == null || !local.startsWith("http://127.0.0.1:")) {
                synchronized (playing) { playing.remove(key); }
                return message("本版本播放器没有提供安全的本地播放代理，不能保证临时文件安全清理");
            }
            return new JSONObject().put("parse", 0).put("url", local).put("jx", 0).toString();
        } catch (Throwable e) {
            synchronized (playing) { playing.remove(key); }
            return message("本播放器不支持当前插件的本地代理功能");
        }
    }

    @Override public Object[] proxy(Map<String, String> params) throws Exception {
        String id = params.get("quark_play");
        if (id == null || !id.matches("[a-f0-9]{32}")) return proxyMessage(404, "无效播放任务");
        Play p;
        synchronized (playing) { p = playing.get(id); }
        if (p == null || p.closed) return proxyMessage(410, "播放任务已结束");
        try {
            String url;
            synchronized (p) {
                p.last = System.currentTimeMillis();
                if (p.url == null) p.url = resolvePlay(p);
                url = p.url;
            }
            // 通过同一设备直接连接夸克 CDN，Cookie 永不返还到播放器 JSON。
            String range = params.get("range");
            Map<String, String> headers = new HashMap<>();
            if (range != null && range.matches("bytes=[0-9]*-[0-9]*")) headers.put("Range", range);
            HttpURLConnection c = open(url, "GET", null, headers, false);
            int status = c.getResponseCode();
            if (status != 200 && status != 206) { c.disconnect(); return proxyMessage(502, "网盘链接已过期，请重新打开选集"); }
            Map<String, String> out = new HashMap<>();
            copyHeader(c, out, "Content-Length"); copyHeader(c, out, "Content-Range");
            copyHeader(c, out, "Accept-Ranges");
            out.put("Cache-Control", "private, no-store");
            p.last = System.currentTimeMillis();
            InputStream stream = c.getInputStream();
            synchronized (playing) { p.activeStreams++; }
            return new Object[]{status, c.getContentType() == null ? "application/octet-stream" : c.getContentType(),
                    trackedStream(p, c, stream), out};
        } catch (Exception e) { return proxyMessage(502, "视频流暂不可用，请返回重试"); }
    }

    /** Android 播放器可能支持 action，但普通退出播放器不一定会调用本方法。 */
    @Override public String action(String value) throws Exception {
        if ("quark_login".equals(value)) { showLoginDialog(); return message("请扫描弹出的二维码"); }
        if ("quark_logout".equals(value)) { prefs.edit().remove("cookie").apply(); return message("本设备已退出夸克"); }
        if (value != null && value.startsWith("quark_close:")) {
            String id = value.substring("quark_close:".length());
            synchronized (playing) { if (playing.containsKey(id)) { playing.get(id).closed = true; playing.get(id).last = System.currentTimeMillis(); } }
            workers.execute(this::cleanupSafely);
            return message("已收到本次播放的结束指令");
        }
        return "{}";
    }

    // ===== 网页搜索和安全检查 =====
    private String siteGet(String url) throws Exception {
        if (!url.startsWith(SITE + "/")) throw new IOException("非法网站请求");
        String page = text(open(url, "GET", null, Collections.emptyMap(), false), 2_000_000);
        if (!page.contains("cckey") || !page.contains("generateCCKey")) return page;
        Matcher gate = GATE.matcher(page);
        if (!gate.find()) throw new IOException("网站安全检查规则有变化");
        String hash = gate.group(1);
        int chinaDay = dayInChina();
        int n = Math.min(20, Math.max(10, chinaDay));
        Map<String, String> headers = new HashMap<>();
        headers.put("Cookie", "cckey=" + hash.substring(0, n));
        String retry = text(open(url, "GET", null, headers, false), 2_000_000);
        if (retry.contains("generateCCKey")) throw new IOException("该设备未通过网站验证，请检查系统时间或网络");
        return retry;
    }

    private static int dayInChina() {
        SimpleDateFormat day = new SimpleDateFormat("d", Locale.US);
        day.setTimeZone(TimeZone.getTimeZone("Asia/Shanghai"));
        return Integer.parseInt(day.format(new Date()));
    }

    private static String decodeGo(String raw) {
        try {
            String token = raw.replace("&amp;", "&");
            int start = token.indexOf("gourl="); if (start < 0) return "";
            token = token.substring(start + 6).split("[&@]", 2)[0].replace("_", "").replace("=", "");
            String b64 = "aHR0cH" + token;
            while (b64.length() % 4 != 0) b64 += "=";
            String share = new String(android.util.Base64.decode(b64, android.util.Base64.DEFAULT), StandardCharsets.UTF_8);
            return SHARE_ID.matcher(share).matches() ? share : "";
        } catch (Exception e) { return ""; }
    }

    private static String encPath(String val) throws Exception {
        return URLEncoder.encode(val == null ? "" : val, "UTF-8").replace("+", "%20");
    }
    private static String attr(Pattern p, String s) { Matcher m = p.matcher(s); return m.find() ? unescape(m.group(1)) : ""; }
    private static String match(String html, String regex) { Matcher m = Pattern.compile(regex).matcher(html); return m.find() ? m.group(1) : ""; }
    private static String unescape(String s) { return s.replace("&amp;", "&").replace("&quot;", "\"").replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">"); }
    private static String plain(String s) { return unescape(s.replaceAll("(?is)<[^>]*>", "")).replaceAll("\\s+", " ").trim(); }
    private static String escapeTitle(String s) { return s.replace("$$$", " ").replace("#", "＃").replace("$", "＄").replace("\n", " ").replace("\r", " "); }
    private static int naturalCompare(String a, String b) {
        String[] l = a.split("\\$", 2), r = b.split("\\$", 2);
        Matcher x = Pattern.compile("\\d+|\\D+").matcher(l[0].toLowerCase(Locale.ROOT));
        Matcher y = Pattern.compile("\\d+|\\D+").matcher(r[0].toLowerCase(Locale.ROOT));
        while (x.find() && y.find()) {
            String xa = x.group(), ya = y.group();
            if (xa.matches("\\d+") && ya.matches("\\d+")) {
                try { int c = Long.compare(Long.parseLong(xa), Long.parseLong(ya)); if (c != 0) return c; }
                catch (NumberFormatException ignored) { }
            } else { int c = xa.compareTo(ya); if (c != 0) return c; }
        }
        return l[0].compareToIgnoreCase(r[0]);
    }

    // ===== 夸克 API、文件树、播放 =====
    private static String apiQuery(String path, Map<String, String> args) throws Exception {
        Map<String, String> q = new LinkedHashMap<>();
        q.put("pr", "ucpro"); q.put("fr", "pc"); q.put("uc_param_str", "");
        q.put("__dt", "1000"); q.put("__t", String.valueOf(System.currentTimeMillis()));
        if (args != null) q.putAll(args);
        StringBuilder url = new StringBuilder(path).append('?');
        for (Map.Entry<String, String> e : q.entrySet())
            url.append(encPath(e.getKey())).append('=').append(encPath(e.getValue())).append('&');
        return url.toString();
    }

    private JSONObject quark(String method, String path, boolean share, Map<String, String> params, JSONObject payload) throws Exception {
        if (!path.startsWith("/1/clouddrive/")) throw new IOException("无效的夸克 API 路径");
        String host = share ? "https://drive.quark.cn" : "https://drive-pc.quark.cn";
        Map<String, String> headers = new HashMap<>();
        headers.put("Origin", "https://pan.quark.cn"); headers.put("Referer", "https://pan.quark.cn/");
        headers.put("Cookie", prefs.getString("cookie", ""));
        String json = text(open(apiQuery(host + path, params), method, payload == null ? null : payload.toString(), headers, false), 1_500_000);
        JSONObject parsed = new JSONObject(json);
        int code = parsed.optInt("code", 0);
        if (code != 0 && parsed.optInt("status", 0) != 2000000) throw new IOException("夸克 API 拒绝请求(" + code + ")");
        return parsed.optJSONObject("data") == null ? new JSONObject() : parsed.getJSONObject("data");
    }

    private String shareToken(String share) throws Exception {
        JSONObject result = quark("POST", "/1/clouddrive/share/sharepage/token", false, null,
                new JSONObject().put("pwd_id", share).put("passcode", ""));
        String token = result.optString("stoken");
        if (token.isEmpty()) throw new IOException("分享不可访问或需要提取码");
        return token;
    }

    private List<Video> listVideos(String share) throws Exception {
        String stoken = shareToken(share);
        ArrayDeque<String[]> queue = new ArrayDeque<>();
        queue.add(new String[]{"0", "根目录", "0"});
        Set<String> seen = new HashSet<>();
        List<Video> videos = new ArrayList<>();
        while (!queue.isEmpty() && seen.size() < 250 && videos.size() < 500) {
            String[] dir = queue.poll();
            if (!seen.add(dir[0])) continue;
            int depth = Integer.parseInt(dir[2]);
            for (int page = 1; page <= 30; ++page) {
                Map<String, String> p = new HashMap<>();
                p.put("pwd_id", share); p.put("stoken", stoken); p.put("pdir_fid", dir[0]);
                p.put("force", "0"); p.put("_page", String.valueOf(page)); p.put("_size", "100");
                p.put("_fetch_total", "1"); p.put("ver", "2");
                JSONObject data = quark("GET", "/1/clouddrive/share/sharepage/detail", true, p, null);
                JSONArray rows = data.optJSONArray("list");
                if (rows == null) break;
                for (int i = 0; i < rows.length() && videos.size() < 500; ++i) {
                    JSONObject item = rows.optJSONObject(i); if (item == null) continue;
                    String fid = item.optString("fid"), name = item.optString("file_name");
                    if (fid.isEmpty() || name.isEmpty()) continue;
                    boolean folder = item.optBoolean("dir", false) || item.optBoolean("is_dir", false)
                            || item.optInt("file_type", -1) == 0;
                    if (folder && depth < 8) queue.add(new String[]{fid, dir[1].equals("根目录") ? name : dir[1] + "/" + name, String.valueOf(depth + 1)});
                    else if (!folder && VIDEO_EXT.matcher(name).find()) videos.add(new Video(share, fid,
                            item.optString("share_fid_token"), stoken, item.optString("pdir_fid", dir[0]), dir[1], name));
                }
                if (rows.length() < 100) break;
            }
        }
        return videos;
    }

    private String resolvePlay(Play p) throws Exception {
        Video v = p.video;
        v.stoken = shareToken(v.share);
        JSONObject args = new JSONObject().put("pwd_id", v.share).put("stoken", v.stoken)
                .put("fid_list", new JSONArray().put(v.fid))
                .put("fid_token_list", new JSONArray().put(v.token)).put("pdir_fid", v.parent);
        try {
            JSONObject direct = quark("POST", "/1/clouddrive/share/sharepage/download", true, null, args);
            String link = videoLink(direct);
            if (validCdn(link)) return link;
        } catch (Exception ignored) { }
        // 直链不可用：只在本机登录的夸克账号内创建专用、可追踪的临时目录。
        String root = prefs.getString("owned_root", "");
        if (root.isEmpty()) {
            root = newFolder("0", "大龟影视临时播放-" + UUID.randomUUID().toString().substring(0, 8));
            prefs.edit().putString("owned_root", root).commit();
        }
        String folder = newFolder(root, "播放-" + UUID.randomUUID().toString().substring(0, 8));
        p.tmpFolder = folder;
        persistOwned(folder, System.currentTimeMillis()); // 必须先登记，才允许触发转存
        JSONObject saved = quark("POST", "/1/clouddrive/share/sharepage/save", true, null,
                args.put("to_pdir_fid", folder).put("pdir_save_all", false).put("scene", "link"));
        String task = saved.optString("task_id");
        if (task.isEmpty()) throw new IOException("云端临时转存未提交成功");
        String fid = "";
        for (int i = 0; i < 12 && fid.isEmpty(); ++i) {
            Thread.sleep(1000 + Math.min(i * 250, 1000));
            Map<String, String> query = new HashMap<>(); query.put("task_id", task); query.put("retry_index", String.valueOf(i));
            JSONObject job = quark("GET", "/1/clouddrive/task", false, query, null);
            JSONObject saveAs = job.optJSONObject("save_as");
            if (saveAs != null) {
                JSONArray result = saveAs.optJSONArray("save_as_top_fids");
                if (result == null) result = saveAs.optJSONArray("save_as_select_top_fids");
                if (result != null && result.length() > 0) fid = result.getString(0);
            }
        }
        if (fid.isEmpty()) throw new IOException("云端转存任务超时，请稍后再试");
        JSONObject download = quark("POST", "/1/clouddrive/file/download", false, null,
                new JSONObject().put("fids", new JSONArray().put(fid)));
        String link = videoLink(download);
        if (!validCdn(link)) throw new IOException("网盘未返回允许访问的下载地址");
        return link;
    }

    private String newFolder(String parent, String name) throws Exception {
        JSONObject data = quark("POST", "/1/clouddrive/file", false, null,
                new JSONObject().put("pdir_fid", parent).put("file_name", name)
                        .put("dir_path", "").put("dir_init_lock", false));
        String id = data.optString("fid"); if (id.isEmpty()) throw new IOException("创建播放临时文件夹失败");
        return id;
    }

    private static String videoLink(JSONObject data) {
        JSONObject entry = data;
        JSONArray list = data.optJSONArray("list");
        if (list != null && list.length() > 0) entry = list.optJSONObject(0);
        if (entry == null) return "";
        String url = entry.optString("download_url"); if (url.isEmpty()) url = entry.optString("url");
        if (url.isEmpty()) url = entry.optString("play_url");
        return url;
    }

    private boolean loggedIn() { return prefs != null && !prefs.getString("cookie", "").isEmpty(); }

    private void persistOwned(String folder, long created) {
        synchronized (playing) {
            // JSON 中仅记录本程序创建的文件夹 ID / 时间，绝不猜测用户目录 ID。
            try {
                JSONObject j = new JSONObject(prefs.getString("owned_temp", "{}"));
                j.put(folder, created);
                prefs.edit().putString("owned_temp", j.toString()).commit();
            } catch (Exception ignored) { }
        }
    }
    /** 代理流每次读取都刷新最后活动时间，阻止删除正在传输的数据。 */
    private InputStream trackedStream(Play p, HttpURLConnection connection, InputStream source) {
        return new FilterInputStream(source) {
            private boolean finished;
            private void touch() { synchronized (playing) { p.last = System.currentTimeMillis(); } }
            private void finish() {
                if (finished) return;
                finished = true;
                synchronized (playing) { if (p.activeStreams > 0) p.activeStreams--; p.last = System.currentTimeMillis(); }
                connection.disconnect();
            }
            @Override public int read() throws IOException {
                try { int value = super.read(); if (value >= 0) touch(); else finish(); return value; }
                catch (IOException e) { finish(); throw e; }
            }
            @Override public int read(byte[] b, int off, int len) throws IOException {
                try { int value = in.read(b, off, len); if (value > 0) touch(); else if (value < 0) finish(); return value; }
                catch (IOException e) { finish(); throw e; }
            }
            @Override public void close() throws IOException {
                try { super.close(); } finally { finish(); }
            }
        };
    }

    /** 只允许删除本插件独立创建并记录过的 folderId；绝不搜索用户网盘其他目录。 */
    private void cleanupSafely() {
        if (prefs == null) return;
        try {
            long now = System.currentTimeMillis();
            JSONObject owned = new JSONObject(prefs.getString("owned_temp", "{}"));
            for (String folder : new ArrayList<>(jsonKeys(owned))) {
                // 目录 ID 必须是合法的云端 fid，不能混入路径/特殊字符。
                if (!folder.matches("[A-Za-z0-9_-]{5,128}")) continue;
                boolean found = false, shouldWait = false;
                synchronized (playing) {
                    for (Play play : playing.values()) {
                        if (!folder.equals(play.tmpFolder)) continue;
                        found = true;
                        long inactive = now - play.last;
                        if (play.activeStreams > 0 && inactive < STREAM_IDLE_MS) shouldWait = true;
                        else if (play.closed && inactive < CLOSE_GRACE_MS) shouldWait = true;
                        else if (!play.closed && inactive < STREAM_IDLE_MS) shouldWait = true;
                    }
                }
                long created = owned.optLong(folder, now);
                if (shouldWait || (!found && now - created < ORPHAN_GRACE_MS)) continue;
                try {
                    quark("POST", "/1/clouddrive/file/delete", false, null,
                            new JSONObject().put("action_type", 2).put("filelist", new JSONArray().put(folder))
                                    .put("exclude_fids", new JSONArray()));
                    owned.remove(folder);
                    prefs.edit().putString("owned_temp", owned.toString()).commit();
                } catch (Exception ignored) { /* 无法删除时保留登记，下次继续重试 */ }
            }
            synchronized (playing) {
                for (String key : new ArrayList<>(playing.keySet())) {
                    Play play = playing.get(key);
                    if (play == null || play.activeStreams > 0) continue;
                    if ((play.closed && now - play.last >= CLOSE_GRACE_MS)
                            || now - play.last > STALE_MS) playing.remove(key);
                }
            }
        } catch (Exception ignored) { }
    }
    private static List<String> jsonKeys(JSONObject j) {
        List<String> keys = new ArrayList<>();
        java.util.Iterator<String> it = j.keys(); while (it.hasNext()) keys.add(it.next()); return keys;
    }

    // ===== 本机扫码：应用内 Dialog + WebView 离线 QR 绘制 =====
    private void showLoginDialog() {
        if (loginShowing || !(uiContext instanceof Activity)) return;
        loginShowing = true;
        Activity activity = (Activity) uiContext;
        activity.runOnUiThread(() -> {
            try {
                final WebView web = new WebView(activity);
                web.getSettings().setJavaScriptEnabled(true);
                web.getSettings().setAllowFileAccess(false);
                web.getSettings().setAllowContentAccess(false);
                web.setWebViewClient(new WebViewClient());
                final AlertDialog dialog = new AlertDialog.Builder(activity).setTitle("夸克网盘 · 本机扫码")
                        .setView(web).setNegativeButton("关闭", (d, which) -> loginShowing = false).create();
                dialog.setOnDismissListener(d -> { loginShowing = false; web.destroy(); });
                dialog.show();
                workers.execute(() -> {
                    try {
                        // 此处用同一 Java 网络栈请求上游二维码，不依赖公共二维码生成网站。
                        JSONObject data = new JSONObject(text(open("https://uop.quark.cn/cas/ajax/getTokenForQrcodeLogin?client_id=532&v=1.2&request_id="
                                + UUID.randomUUID(), "GET", null, Collections.emptyMap(), true), 160000));
                        String token = data.getJSONObject("data").getJSONObject("members").getString("token");
                        String qrUrl = "https://su.quark.cn/4_eMHBJ?token=" + encPath(token)
                                + "&client_id=532&ssb=weblogin&uc_param_str=&uc_biz_str=S%3Acustom%7COPT%3ASAREA%400%7COPT%3AIMMERSIVE%401%7COPT%3ABACK_BTN_STYLE%400";
                        String html = "<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'></head>"
                                + "<body style='text-align:center;font-family:sans-serif'><h3>用手机夸克 App 扫码确认</h3><canvas id='qr'></canvas>"
                                + "<p id='state'>二维码约 5 分钟后过期</p><script>" + QrScript.CODE +
                                "\nvar qr=new QRCode(-1,1);qr.addData(" + JSONObject.quote(qrUrl) + ");qr.make();"
                                + "var s=qr.getModuleCount(),cv=document.getElementById('qr'),c=cv.getContext('2d');cv.width=cv.height=300;"
                                + "c.fillStyle='#fff';c.fillRect(0,0,300,300);c.fillStyle='#000';"
                                + "for(var i=0;i<s;i++)for(var j=0;j<s;j++)if(qr.isDark(i,j))c.fillRect(Math.floor((i+2)*300/(s+4)),Math.floor((j+2)*300/(s+4)),Math.ceil(300/(s+4)),Math.ceil(300/(s+4)));"
                                + "</script></body></html>";
                        activity.runOnUiThread(() -> { if (dialog.isShowing()) web.loadDataWithBaseURL("https://pan.quark.cn/", html, "text/html", "utf-8", null); });
                        for (int i = 0; i < 140 && dialog.isShowing(); ++i) {
                            Thread.sleep(2000);
                            JSONObject result = new JSONObject(text(open("https://uop.quark.cn/cas/ajax/getServiceTicketByQrcodeToken?client_id=532&v=1.2&token="
                                    + encPath(token) + "&request_id=" + UUID.randomUUID(), "GET", null, Collections.emptyMap(), true), 160000));
                            int code = result.optInt("status", 0);
                            if (code == 2000000) {
                                JSONObject mem = result.optJSONObject("data") == null ? null : result.getJSONObject("data").optJSONObject("members");
                                String ticket = mem == null ? "" : mem.optString("service_ticket");
                                if (!ticket.isEmpty()) {
                                    // 读取 Set-Cookie，只在本机保存；扫码 token / 票据均不写日志。
                                    HttpURLConnection c = open("https://pan.quark.cn/account/info?st=" + encPath(ticket) + "&lw=scan",
                                            "GET", null, Collections.emptyMap(), true);
                                    String cookie = cookieFromResponse(c);
                                    c.disconnect();
                                    if (!cookie.contains("__pus=") && !cookie.contains("__kps="))
                                        throw new IOException("二维码确认后未取得登录 Cookie");
                                    prefs.edit().putString("cookie", cookie).commit();
                                    activity.runOnUiThread(() -> {
                                        if (dialog.isShowing()) {
                                            web.loadDataWithBaseURL("https://pan.quark.cn/", "<html><body style='text-align:center;padding:30px'><h2>夸克登录成功</h2><p>Cookie 已保存在本机，稍后自动关闭</p></body></html>", "text/html", "utf-8", null);
                                            web.postDelayed(dialog::dismiss, 1500);
                                        }
                                    });
                                    return;
                                }
                            }
                            if (code == 50004002 || code == 50004003 || code == 50004004) break;
                        }
                        activity.runOnUiThread(() -> { if (dialog.isShowing()) web.loadDataWithBaseURL(null,
                                "<html><body><h3>二维码已过期或已取消，请重新点击播放</h3></body></html>", "text/html", "utf-8", null); });
                    } catch (Exception e) {
                        activity.runOnUiThread(() -> { if (dialog.isShowing()) web.loadDataWithBaseURL(null,
                                "<html><body><h3>扫码请求失败</h3><p>请检查设备网络，关闭后重试</p></body></html>", "text/html", "utf-8", null); });
                    }
                });
            } catch (Exception e) { loginShowing = false; }
        });
    }

    private static String cookieFromResponse(HttpURLConnection connection) {
        Map<String, String> cookies = new LinkedHashMap<>();
        for (Map.Entry<String, List<String>> entry : connection.getHeaderFields().entrySet()) {
            if (entry.getKey() == null || !entry.getKey().equalsIgnoreCase("Set-Cookie")) continue;
            for (String line : entry.getValue()) {
                String first = line.split(";", 2)[0];
                int eq = first.indexOf('=');
                if (eq > 0 && first.length() < 10000) cookies.put(first.substring(0, eq), first.substring(eq + 1));
            }
        }
        List<String> pairs = new ArrayList<>();
        for (Map.Entry<String, String> entry : cookies.entrySet()) pairs.add(entry.getKey() + "=" + entry.getValue());
        return String.join("; ", pairs);
    }

    private static boolean validCdn(String link) {
        try {
            URL uri = new URL(link);
            if (!uri.getProtocol().equals("https") || uri.getUserInfo() != null || uri.getPort() != -1) return false;
            String host = uri.getHost().toLowerCase(Locale.ROOT);
            boolean valid = false;
            for (String suffix : Arrays.asList("quark.cn", "quarkcdn.com", "myquark.cn", "uc.cn", "aliyuncs.com", "alicdn.com"))
                if (host.equals(suffix) || host.endsWith("." + suffix)) valid = true;
            if (!valid) return false;
            for (InetAddress addr : InetAddress.getAllByName(host))
                if (addr.isAnyLocalAddress() || addr.isLoopbackAddress() || addr.isLinkLocalAddress() || addr.isSiteLocalAddress()) return false;
            return true;
        } catch (Exception e) { return false; }
    }

    private static HttpURLConnection open(String url, String method, String payload, Map<String, String> headers, boolean qrHost) throws Exception {
        URL uri = new URL(url);
        if (!uri.getProtocol().equals("https")) throw new IOException("拒绝非 HTTPS 请求");
        String host = uri.getHost().toLowerCase(Locale.ROOT);
        boolean isSite = host.equals("www.zhongchuangwl.com");
        boolean isQuark = host.equals("uop.quark.cn") || host.equals("pan.quark.cn")
                || host.equals("drive-pc.quark.cn") || host.equals("drive.quark.cn") || host.equals("su.quark.cn");
        if (!isSite && !isQuark && !validCdn(url)) throw new IOException("不允许的联网目标");
        HttpURLConnection c = (HttpURLConnection) uri.openConnection();
        c.setConnectTimeout(8000); c.setReadTimeout(23000); c.setInstanceFollowRedirects(false);
        c.setRequestMethod(method);
        c.setRequestProperty("User-Agent", "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36");
        c.setRequestProperty("Accept", "application/json,text/html,*/*");
        c.setRequestProperty("Accept-Language", "zh-CN,zh;q=0.9");
        for (Map.Entry<String, String> e : headers.entrySet()) c.setRequestProperty(e.getKey(), e.getValue());
        if (payload != null) {
            c.setDoOutput(true); c.setRequestProperty("Content-Type", "application/json;charset=UTF-8");
            byte[] bytes = payload.getBytes(StandardCharsets.UTF_8);
            c.setFixedLengthStreamingMode(bytes.length);
            try (java.io.OutputStream out = c.getOutputStream()) { out.write(bytes); }
        }
        return c;
    }
    private static String text(HttpURLConnection c, int limit) throws Exception {
        try {
            int status = c.getResponseCode();
            if (status < 200 || status >= 300) throw new IOException("上游 HTTP " + status);
            try (InputStream input = c.getInputStream(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
                byte[] b = new byte[8192]; int n;
                while ((n = input.read(b)) != -1) {
                    if (out.size() + n > limit) throw new IOException("上游响应超过限制");
                    out.write(b, 0, n);
                }
                return new String(out.toByteArray(), StandardCharsets.UTF_8);
            }
        } finally { c.disconnect(); }
    }
    private static void copyHeader(HttpURLConnection c, Map<String, String> out, String key) {
        String val = c.getHeaderField(key); if (val != null) out.put(key, val);
    }
    private static Object[] proxyMessage(int status, String text) {
        return new Object[]{status, "text/plain; charset=utf-8",
                new ByteArrayInputStream(text.getBytes(StandardCharsets.UTF_8)), Collections.emptyMap()};
    }
    private static String publicMessage(Exception e) { return e instanceof IOException ? e.getMessage() : "请检查网络和网盘权限"; }
    private static String message(String text) throws Exception {
        return new JSONObject().put("parse", 0).put("msg", text).put("url", "").toString();
    }
}
