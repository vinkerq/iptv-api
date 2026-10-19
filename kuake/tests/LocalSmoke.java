import com.github.catvod.spider.ZhongchuangQuark;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.lang.reflect.*;
import java.util.regex.*;
import java.util.*;

public class LocalSmoke {
    static String text(String path) throws Exception { return new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8); }
    static void chk(boolean yes, String desc) { if (!yes) throw new AssertionError(desc); System.out.println("PASS " + desc); }
    public static void main(String[] args) throws Exception {
        Class<?> cls = ZhongchuangQuark.class;
        Field searchField = cls.getDeclaredField("SEARCH_NODE"); searchField.setAccessible(true);
        Pattern search = (Pattern)searchField.get(null);
        Matcher matcher = search.matcher(text("tests/fixtures/search_wudu.html"));
        int n = 0; while(matcher.find()) n++;
        chk(n==10,"saved web search sample yields 10 entries (regex only)");
        Field gateField = cls.getDeclaredField("GATE"); gateField.setAccessible(true);
        Matcher challenge=((Pattern)gateField.get(null)).matcher(text("tests/fixtures/cckey_challenge.html"));
        chk(challenge.find() && challenge.group(1).length()==32,"saved cckey challenge hash recognized");
        Method decode = cls.getDeclaredMethod("decodeGo", String.class);decode.setAccessible(true);
        Matcher go=Pattern.compile("gourl=[^\\\"\\s<>]+",Pattern.CASE_INSENSITIVE).matcher(text("tests/fixtures/detail_wudu.html"));
        chk(go.find(),"saved detail contains gourl parameter");
        String link=(String)decode.invoke(null,"https://www.zhongchuangwl.com/go/?"+go.group());
        chk("https://pan.quark.cn/s/86e3f13e8a79".equals(link),"gourl decodes into expected Quark share");
        Method natural=cls.getDeclaredMethod("naturalCompare",String.class,String.class);natural.setAccessible(true);
        int cmp=(Integer)natural.invoke(null,"第2集.mp4$quark://a","第10集.mp4$quark://b");
        chk(cmp<0,"episode file names naturally sort 2 before 10");
        chk(!text("src/com/github/catvod/spider/ZhongchuangQuark.java").contains("103.236.77.86"),"no rental server dependency");
        System.out.println("Local JVM smoke tests passed (does not prove Android or live Quark API compatibility)");
    }
}
