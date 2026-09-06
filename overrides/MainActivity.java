package com.maxi.nikkemodtracker;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.MimeTypeMap;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.json.JSONArray;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

public class MainActivity extends Activity {
    private WebView webView;

    public class AndroidBridge {
        @JavascriptInterface
        public String getCachedImage(String key) {
            File dir = new File(getCacheDir(), "nikke_images");
            if (!dir.exists()) return "";
            File[] files = dir.listFiles();
            if (files == null) return "";
            String prefix = safeKey(key) + ".";
            for (File f : files) {
                if (f.getName().startsWith(prefix) && f.length() > 0) {
                    return Uri.fromFile(f).toString();
                }
            }
            return "";
        }

        @JavascriptInterface
        public void clearImageCache() {
            File dir = new File(getCacheDir(), "nikke_images");
            if (!dir.exists()) return;
            File[] files = dir.listFiles();
            if (files == null) return;
            for (File f : files) {
                try { f.delete(); } catch (Exception ignored) {}
            }
        }

        @JavascriptInterface
        public String cacheImage(String key, String urlsJson) {
            try {
                String cached = getCachedImage(key);
                if (!cached.isEmpty()) return cached;
                JSONArray urls = new JSONArray(urlsJson == null ? "[]" : urlsJson);
                File dir = new File(getCacheDir(), "nikke_images");
                if (!dir.exists()) dir.mkdirs();
                for (int i = 0; i < urls.length(); i++) {
                    String value = urls.optString(i, "");
                    if (value.isEmpty() || !(value.startsWith("https://") || value.startsWith("http://"))) continue;
                    HttpURLConnection conn = null;
                    try {
                        URL url = new URL(value);
                        conn = (HttpURLConnection) url.openConnection();
                        conn.setConnectTimeout(7000);
                        conn.setReadTimeout(10000);
                        conn.setInstanceFollowRedirects(true);
                        conn.setRequestProperty("User-Agent", "Mozilla/5.0 (Android) NIKKE-Mod-Tracker/0.2.5");
                        conn.setRequestProperty("Accept", "image/avif,image/webp,image/apng,image/*,*/*;q=0.8");
                        int status = conn.getResponseCode();
                        if (status < 200 || status >= 300) continue;
                        String type = conn.getContentType();
                        String ext = MimeTypeMap.getSingleton().getExtensionFromMimeType(type == null ? "" : type.split(";")[0]);
                        if (ext == null || ext.isEmpty()) {
                            String path = url.getPath().toLowerCase();
                            if (path.endsWith(".webp")) ext = "webp";
                            else if (path.endsWith(".jpg") || path.endsWith(".jpeg")) ext = "jpg";
                            else ext = "png";
                        }
                        File out = new File(dir, safeKey(key) + "." + ext);
                        try (InputStream in = conn.getInputStream(); FileOutputStream fos = new FileOutputStream(out)) {
                            byte[] buf = new byte[16384];
                            int n;
                            long total = 0;
                            while ((n = in.read(buf)) > 0) {
                                fos.write(buf, 0, n);
                                total += n;
                                if (total > 12_000_000) throw new Exception("image too large");
                            }
                        }
                        if (out.length() > 100) return Uri.fromFile(out).toString();
                        out.delete();
                    } catch (Exception ignored) {
                    } finally {
                        if (conn != null) conn.disconnect();
                    }
                }
            } catch (Exception ignored) {
            }
            return "";
        }

        @JavascriptInterface
        public String getCatalogJson() {
            try (InputStream in = getAssets().open("catalog.json")) {
                byte[] buf = new byte[16384];
                java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
                int n;
                while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
                return out.toString(StandardCharsets.UTF_8.name());
            } catch (Exception ignored) {
                return "";
            }
        }

        @JavascriptInterface
        public String appVersion() {
            return "0.2.5";
        }
    }

    private static String safeKey(String key) {
        return (key == null ? "unknown" : key).replaceAll("[^A-Za-z0-9_-]", "_");
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        webView = new WebView(this);
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setAllowFileAccessFromFileURLs(true);
        s.setAllowUniversalAccessFromFileURLs(true);
        s.setLoadsImagesAutomatically(true);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        webView.addJavascriptInterface(new AndroidBridge(), "AndroidBridge");
        webView.setWebViewClient(new WebViewClient());
        webView.setWebChromeClient(new WebChromeClient());
        setContentView(webView);
        loadAppFromIntent(getIntent());
    }

    private void loadAppFromIntent(Intent intent) {
        String base = "file:///android_asset/index.html";
        Uri data = intent == null ? null : intent.getData();
        if (data != null && "nikkemodtracker".equalsIgnoreCase(data.getScheme()) && "pair".equalsIgnoreCase(data.getHost())) {
            try {
                String host = data.getQueryParameter("host");
                String token = data.getQueryParameter("token");
                String name = data.getQueryParameter("name");
                String q = "?pairHost=" + enc(host) + "&pairToken=" + enc(token) + "&pairName=" + enc(name);
                webView.loadUrl(base + q);
                return;
            } catch (Exception ignored) {
            }
        }
        webView.loadUrl(base);
    }

    private static String enc(String value) throws Exception {
        return URLEncoder.encode(value == null ? "" : value, StandardCharsets.UTF_8.name());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        loadAppFromIntent(intent);
    }

    @Override
    public void onBackPressed() {
        if (webView != null) {
            webView.evaluateJavascript("window.androidBack && window.androidBack()", null);
        } else {
            super.onBackPressed();
        }
    }
}
