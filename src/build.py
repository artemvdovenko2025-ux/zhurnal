# -*- coding: utf-8 -*-
"""Сборка трёх версий «Журнала учителя» из одного исходника.

  artifact  — ссылка на claude.ai: без списков учеников
  private   — личный офлайн-файл учителя: со списками
  site      — сайт для GitHub Pages (ставится на ПК и телефон): без списков,
              без имени учителя, с синхронизацией через Яндекс.Диск
"""
import io, re, os, json, sys, shutil

SRC = io.open("app.src.html", encoding="utf-8").read()
ROSTERS_OBJ = "{}"
if os.path.exists("rosters.private.js"):
    m = re.search(r"var ROSTERS = (\{.*\});", io.open("rosters.private.js", encoding="utf-8").read(), re.S)
    ROSTERS_OBJ = m.group(1)

CLIENT_ID = os.environ.get("YANDEX_CLIENT_ID", "")      # впишется после регистрации в Яндексе
CACHE_VER = os.environ.get("CACHE_VER", "1")

STANDALONE_HEAD = (
    '<!doctype html>\n<html lang="ru">\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<meta name="theme-color" content="#2f7d6b">\n'
    '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}</style>\n'
)
SITE_HEAD = (
    '<link rel="manifest" href="manifest.webmanifest">\n'
    '<link rel="icon" href="icon-192.png" type="image/png">\n'
    '<link rel="apple-touch-icon" href="apple-touch-icon.png">\n'
    '<meta name="apple-mobile-web-app-capable" content="yes">\n'
    '<meta name="mobile-web-app-capable" content="yes">\n'
    '<meta name="apple-mobile-web-app-title" content="Журнал">\n'
    '<meta name="description" content="Расписание пар, план недели, классы, дела и копилка приёмов.">\n'
)

# Личное (имя учителя, обращение) лежит в private.json рядом со сборщиком
# и в репозиторий не попадает. Без него личные версии соберутся с пустым именем.
PRIV = {"name": "", "nick": "", "title": "Журнал учителя"}
if os.path.exists("private.json"):
    PRIV.update(json.load(io.open("private.json", encoding="utf-8")))

VARIANTS = {
    "artifact": dict(rosters=False, site=False, name=PRIV["name"], nick=PRIV["nick"],
                     title=PRIV["title"], head="", client=""),
    "private":  dict(rosters=True,  site=False, name=PRIV["name"], nick=PRIV["nick"],
                     title=PRIV["title"], head=STANDALONE_HEAD, client=""),
    "site":     dict(rosters=False, site=True,  name="", nick="",
                     title="Журнал учителя", head=STANDALONE_HEAD + SITE_HEAD, client=CLIENT_ID),
}

def conditionals(s, flags):
    pat = re.compile(r"<!--@IF:(\w+)-->(.*?)(?:<!--@ELSE-->(.*?))?<!--@END-->", re.S)
    def sub(mm):
        return mm.group(2) if flags.get(mm.group(1)) else (mm.group(3) or "")
    return pat.sub(sub, s)

def build(kind, client_override=None):
    v = VARIANTS[kind]
    s = SRC
    s = s.replace("<!--@HEAD@-->", v["head"])
    s = s.replace("@@TITLE@@", v["title"])
    s = s.replace("/*@ROSTERS@*/", ROSTERS_OBJ if v["rosters"] else "{}")
    s = s.replace("/*@PROFILE@*/", json.dumps({"name": v["name"], "nick": v["nick"]}, ensure_ascii=False))
    s = s.replace("/*@BUILD@*/", "pwa" if v["site"] else kind)
    s = s.replace("/*@CLIENT_ID@*/", client_override if client_override is not None else v["client"])
    s = conditionals(s, {"rosters": v["rosters"], "pwa": v["site"]})
    left = re.findall(r"/\*@\w+@\*/|@@\w+@@|<!--@\w+", s)
    assert not left, (kind, left)
    return s

MANIFEST = {
    "name": "Журнал учителя", "short_name": "Журнал", "lang": "ru",
    "description": "Расписание пар, план недели, классы, дела и копилка приёмов.",
    "start_url": "./", "scope": "./", "display": "standalone",
    "background_color": "#eef1ef", "theme_color": "#2f7d6b",
    "icons": [
        {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ],
}

SW = r"""// Офлайн-кэш «Журнала учителя». При каждом выпуске меняется номер версии.
const CACHE = "zhurnal-v@VER@";
const FONTS = "zhurnal-fonts";
const SHELL = ["./", "./index.html", "./manifest.webmanifest",
  "./icon-192.png", "./icon-512.png", "./icon-maskable-512.png", "./apple-touch-icon.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys
        .filter((k) => k.startsWith("zhurnal-v") && k !== CACHE)
        .map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  // Яндекс (вход и Диск) — только напрямую, никогда из кэша.
  if (/(^|\.)yandex\.(ru|net)$/.test(url.hostname)) return;

  // Сама страница: при наличии сети — свежая версия, без сети — из кэша.
  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req)
        .then((r) => {
          const copy = r.clone();
          caches.open(CACHE).then((c) => c.put("./index.html", copy));
          return r;
        })
        .catch(() => caches.match("./index.html"))
    );
    return;
  }

  // Шрифты: отдаём из кэша сразу, в фоне обновляем.
  if (url.hostname === "fonts.googleapis.com" || url.hostname === "fonts.gstatic.com") {
    e.respondWith(caches.open(FONTS).then((c) => c.match(req).then((hit) => {
      const net = fetch(req).then((r) => {
        if (r.ok || r.type === "opaque") c.put(req, r.clone());
        return r;
      }).catch(() => hit);
      return hit || net;
    })));
    return;
  }

  if (url.origin === self.location.origin) {
    e.respondWith(caches.match(req).then((hit) => hit || fetch(req)));
  }
});
"""

if __name__ == "__main__":
    out = "out"
    if os.path.isdir(out): shutil.rmtree(out)
    os.makedirs(out + "/site")
    io.open(out + "/artifact.html", "w", encoding="utf-8").write(build("artifact"))
    io.open(out + "/private.html", "w", encoding="utf-8").write(build("private"))
    io.open(out + "/site/index.html", "w", encoding="utf-8").write(build("site"))
    io.open(out + "/site/manifest.webmanifest", "w", encoding="utf-8").write(json.dumps(MANIFEST, ensure_ascii=False, indent=2))
    io.open(out + "/site/sw.js", "w", encoding="utf-8").write(SW.replace("@VER@", CACHE_VER))
    # отдельная тестовая сборка сайта с выдуманным ClientID — только для проверки синхронизации
    io.open(out + "/site-test.html", "w", encoding="utf-8").write(build("site", client_override="TEST-CLIENT"))
    print("собрано:", sorted(os.listdir(out)), sorted(os.listdir(out + "/site")))
