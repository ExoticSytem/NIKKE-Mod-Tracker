package com.exoticsystem.nikkemodtracker;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Comparator;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final String CATALOG_URL = "https://raw.githubusercontent.com/ExoticSytem/NIKKE-Mod-Tracker/main/catalog/admin/characters.json";
    private static final String IMAGE_PREFIX = "https://raw.githubusercontent.com/ExoticSytem/NIKKE-Mod-Tracker/main/catalog/admin/images/";
    private static final long CARD_CACHE_LIMIT = 80L * 1024L * 1024L;

    private WebView webView;
    private final ExecutorService io = Executors.newFixedThreadPool(3);
    private String pendingPairUri = null;
    private boolean pageReady = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.rgb(10, 13, 18));
        getWindow().setNavigationBarColor(Color.rgb(10, 13, 18));

        webView = new WebView(this);
        setContentView(webView);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setUserAgentString(settings.getUserAgentString() + " NIKKE-Mod-Tracker/0.3.0");
        webView.setBackgroundColor(Color.rgb(10, 13, 18));
        webView.setWebChromeClient(new WebChromeClient());
        webView.addJavascriptInterface(new NativeBridge(), "Native");
        webView.setWebViewClient(new AppWebViewClient());

        Intent intent = getIntent();
        if (intent != null && intent.getData() != null) {
            pendingPairUri = intent.getData().toString();
        }
        webView.loadUrl("file:///android_asset/index.html");
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        Uri data = intent != null ? intent.getData() : null;
        if (data != null) {
            pendingPairUri = data.toString();
            dispatchPendingPair();
        }
    }

    @Override
    public void onBackPressed() {
        if (webView != null) {
            webView.evaluateJavascript("window.androidBack && window.androidBack()", result -> {
                if ("false".equals(result)) {
                    MainActivity.super.onBackPressed();
                }
            });
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        io.shutdownNow();
        if (webView != null) webView.destroy();
        super.onDestroy();
    }

    private void dispatchPendingPair() {
        if (!pageReady || pendingPairUri == null || pendingPairUri.isEmpty()) return;
        String js = "window.receivePairUri(" + JSONObject.quote(pendingPairUri) + ")";
        webView.evaluateJavascript(js, null);
        pendingPairUri = null;
    }

    private void deliver(String fn, String json) {
        runOnUiThread(() -> webView.evaluateJavascript("window." + fn + "(" + JSONObject.quote(json) + ")", null));
    }

    private static String readAll(InputStream in) throws Exception {
        if (in == null) return "";
        byte[] buf = new byte[32 * 1024];
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
        int n;
        while ((n = in.read(buf)) >= 0) out.write(buf, 0, n);
        return out.toString("UTF-8");
    }

    private static String sha1(String text) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-1");
            byte[] dig = md.digest(text.getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            for (byte b : dig) sb.append(String.format(Locale.US, "%02x", b));
            return sb.toString();
        } catch (Exception e) {
            return Integer.toHexString(text.hashCode());
        }
    }

    private File cardCacheDir() {
        File f = new File(getCacheDir(), "card_images");
        if (!f.exists()) f.mkdirs();
        return f;
    }

    private void trimCardCache() {
        File[] files = cardCacheDir().listFiles();
        if (files == null) return;
        Arrays.sort(files, Comparator.comparingLong(File::lastModified));
        long total = 0;
        for (File f : files) total += f.length();
        for (File f : files) {
            if (total <= CARD_CACHE_LIMIT) break;
            long len = f.length();
            if (f.delete()) total -= len;
        }
    }

    private class AppWebViewClient extends WebViewClient {
        @Override
        public void onPageFinished(WebView view, String url) {
            pageReady = true;
            dispatchPendingPair();
        }

        @Override
        public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
            String url = request.getUrl().toString();
            if (!url.startsWith(IMAGE_PREFIX) || !url.contains("__card.")) return null;
            try {
                String ext = url.toLowerCase(Locale.US).contains(".webp") ? ".webp" : url.toLowerCase(Locale.US).contains(".jpg") || url.toLowerCase(Locale.US).contains(".jpeg") ? ".jpg" : ".png";
                File dest = new File(cardCacheDir(), sha1(url) + ext);
                if (!dest.exists() || dest.length() == 0) {
                    HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
                    c.setConnectTimeout(7000);
                    c.setReadTimeout(12000);
                    c.setRequestProperty("User-Agent", "NIKKE-Mod-Tracker/0.3.0");
                    c.connect();
                    if (c.getResponseCode() != 200) {
                        c.disconnect();
                        return null;
                    }
                    File tmp = new File(dest.getAbsolutePath() + ".tmp");
                    try (InputStream in = c.getInputStream(); FileOutputStream out = new FileOutputStream(tmp)) {
                        byte[] buf = new byte[32 * 1024];
                        int n;
                        while ((n = in.read(buf)) >= 0) out.write(buf, 0, n);
                    }
                    c.disconnect();
                    if (!tmp.renameTo(dest)) {
                        try (InputStream in = new FileInputStream(tmp); FileOutputStream out = new FileOutputStream(dest)) {
                            byte[] buf = new byte[32 * 1024]; int n; while ((n = in.read(buf)) >= 0) out.write(buf, 0, n);
                        }
                        tmp.delete();
                    }
                    trimCardCache();
                }
                dest.setLastModified(System.currentTimeMillis());
                String mime = ext.equals(".webp") ? "image/webp" : ext.equals(".jpg") ? "image/jpeg" : "image/png";
                return new WebResourceResponse(mime, null, new FileInputStream(dest));
            } catch (Exception ignored) {
                return null;
            }
        }
    }

    public class NativeBridge {
        @JavascriptInterface
        public void ready() {
            pageReady = true;
            dispatchPendingPair();
        }

        @JavascriptInterface
        public void loadCatalog() {
            io.execute(() -> {
                try {
                    HttpURLConnection c = (HttpURLConnection) new URL(CATALOG_URL + "?v=" + System.currentTimeMillis()).openConnection();
                    c.setConnectTimeout(7000);
                    c.setReadTimeout(15000);
                    c.setUseCaches(false);
                    c.setRequestProperty("Cache-Control", "no-cache");
                    c.setRequestProperty("User-Agent", "NIKKE-Mod-Tracker/0.3.0");
                    int code = c.getResponseCode();
                    if (code != 200) throw new RuntimeException("HTTP " + code);
                    String body = readAll(c.getInputStream());
                    c.disconnect();
                    deliver("onNativeCatalog", body);
                } catch (Exception e) {
                    deliver("onNativeCatalogError", e.getClass().getSimpleName() + ": " + e.getMessage());
                }
            });
        }

        @JavascriptInterface
        public void sync(String host, String token, String tagsJson) {
            io.execute(() -> {
                try {
                    String cleanHost = host == null ? "" : host.trim();
                    if (!(cleanHost.startsWith("http://") || cleanHost.startsWith("https://"))) throw new RuntimeException("Host inválido");
                    URL url = new URL(cleanHost.replaceAll("/$", "") + "/v1/sync?token=" + Uri.encode(token == null ? "" : token));
                    HttpURLConnection c = (HttpURLConnection) url.openConnection();
                    c.setRequestMethod("POST");
                    c.setConnectTimeout(5000);
                    c.setReadTimeout(12000);
                    c.setDoOutput(true);
                    c.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                    c.setRequestProperty("X-NIKKE-Token", token == null ? "" : token);
                    JSONObject root = new JSONObject();
                    JSONObject tags = new JSONObject(tagsJson == null || tagsJson.isEmpty() ? "{}" : tagsJson);
                    root.put("tags", tags);
                    byte[] body = root.toString().getBytes(StandardCharsets.UTF_8);
                    c.setFixedLengthStreamingMode(body.length);
                    try (java.io.OutputStream out = c.getOutputStream()) { out.write(body); }
                    int code = c.getResponseCode();
                    String response = readAll(code >= 200 && code < 400 ? c.getInputStream() : c.getErrorStream());
                    c.disconnect();
                    if (code != 200) throw new RuntimeException("HTTP " + code + (response.isEmpty() ? "" : ": " + response));
                    deliver("onNativeSync", response);
                } catch (Exception e) {
                    deliver("onNativeSyncError", e.getClass().getSimpleName() + ": " + e.getMessage());
                }
            });
        }

        @JavascriptInterface
        public void copyText(String text) {
            runOnUiThread(() -> {
                ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
                if (cm != null) cm.setPrimaryClip(ClipData.newPlainText("NIKKE", text == null ? "" : text));
            });
        }

        @JavascriptInterface
        public void clearImageCache() {
            io.execute(() -> {
                File[] files = cardCacheDir().listFiles();
                if (files != null) for (File f : files) f.delete();
                runOnUiThread(() -> Toast.makeText(MainActivity.this, "Caché de miniaturas limpiada", Toast.LENGTH_SHORT).show());
            });
        }
    }
}
