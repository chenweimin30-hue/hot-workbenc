#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自媒体热点工作台 - 热点抓取 + 自动分类（v3）
改用在 GitHub Actions（海外）可访问的免费接口。
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote

TOP_N = 15
TIMEOUT = 15
BEIJING = timezone(timedelta(hours=8))

# 每个平台可尝试多条链路（按优先级）
# parser: 用于解析不同返回格式
PROVIDERS = {
    "weibo": {
        "name": "微博",
        "endpoints": [
            ("https://v2.xxapi.cn/api/weibohot", "xxapi"),
            ("https://uapis.cn/api/v1/misc/hotboard?type=weibo", "vvhan"),
            ("https://api.vvhan.com/api/hotlist?type=weiboHot", "vvhan"),
        ],
    },
    "douyin": {
        "name": "抖音",
        "endpoints": [
            ("https://v2.xxapi.cn/api/douyinhot", "xxapi_douyin"),
            ("https://uapis.cn/api/v1/misc/hotboard?type=douyin", "vvhan"),
        ],
    },
    "baidu": {
        "name": "百度",
        "endpoints": [
            ("https://v2.xxapi.cn/api/baiduhot", "xxapi"),
            ("https://uapis.cn/api/v1/misc/hotboard?type=baidu", "vvhan"),
        ],
    },
    "toutiao": {
        "name": "今日头条",
        "endpoints": [
            ("https://uapis.cn/api/v1/misc/hotboard?type=toutiao", "vvhan"),
            ("https://v2.xxapi.cn/api/toutiaohot", "xxapi"),
        ],
    },
    "zhihu": {
        "name": "知乎",
        "endpoints": [
            ("https://uapis.cn/api/v1/misc/hotboard?type=zhihu", "vvhan"),
            ("https://api.vvhan.com/api/hotlist?type=zhihuHot", "vvhan"),
        ],
    },
}

CATEGORY_RULES = [
    # 优先级：AI > 科技 > 民生 > 社会（先匹配先生效）
    ("AI", [
        "AI", "人工智能", "ChatGPT", "GPT", "大模型", "AIGC", "深度学习", "机器学习",
        "OpenAI", "Claude", "Gemini", "文心一言", "通义千问", "智谱", "Kimi", "豆包",
        "智能体", "Agent", "算力", "英伟达", "NVIDIA", "Sora", "Midjourney",
        "Stable Diffusion", "多模态", "大语言模型", "LLM", "生成式", "智能问答",
    ]),
    ("科技", [
        "芯片", "华为", "苹果", "特斯拉", "太空", "火箭", "5G", "6G", "手机", "电脑",
        "机器人", "自动驾驶", "元宇宙", "半导体", "量子", "折叠屏", "智能穿戴",
        "新能源车", "航天", "卫星", "操作系统", "鸿蒙", "安卓", "iOS", "数码",
        "互联网", "软件", "黑科技", "科技", "电池", "登月", "算法", "iPhone",
        "小米", "OPPO", "vivo", "荣耀", "人形机器人", "天工",
    ]),
    ("民生", [
        "教育", "医疗", "养老", "社保", "就业", "高考", "中考", "菜价", "地铁", "公交",
        "停电", "停水", "疫情", "疫苗", "医院", "学校", "幼儿园", "养老金", "医保",
        "房租", "外卖", "快递", "通勤", "供暖", "限电", "物价", "工资", "假期",
        "放假", "加班", "住房", "租房", "买房", "交通", "报到", "入学", "新生",
        "家长", "大学", "北大", "校园", "开学", "学费", "看病", "挂号", "药品",
        "处暑", "出伏", "高温", "暴雨", "天气",
    ]),
    ("社会", [
        "车祸", "火灾", "地震", "救人", "警察", "法院", "判决", "犯罪", "盗窃", "诈骗",
        "失踪", "遇害", "坠亡", "纠纷", "维权", "事故", "爆料", "溺水", "打架",
        "通缉", "离世", "病逝", "去世", "身亡", "遇难", "伤亡", "肇事", "摄像头",
        "派出所", "刑拘", "逮捕", "获刑", "醉驾", "酒驾", "碰撞", "爆炸", "坍塌",
        "记者", "战地", "通报", "警方", "案件", "嫌疑人", "官方通报",
    ]),
]

DEFAULT_CATEGORY = "其他"


def http_get_json(url: str):
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
            },
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
            return json.loads(raw)
    except Exception as e:
        print("    请求失败 %s: %s" % (url[:60], e))
        return None


def clean_title(title: str) -> str:
    if not title:
        return ""
    t = str(title).strip()
    t = re.sub(r"^#+\s*", "", t)
    t = re.sub(r"\s*#+$", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def parse_xxapi(data, source_key: str) -> list:
    """v2.xxapi.cn 通用格式: {code:200, data:[{title,hot,url,index},...]}"""
    if not data or data.get("code") != 200:
        return []
    items = []
    for idx, row in enumerate(data.get("data") or [], 1):
        if idx > TOP_N:
            break
        title = clean_title(row.get("title") or row.get("name") or "")
        if not title:
            continue
        url = row.get("url") or row.get("link") or ""
        hot = row.get("hot") or row.get("hot_value") or row.get("hotValue") or ""
        items.append({
            "rank": row.get("index") or idx,
            "title": title,
            "desc": (row.get("desc") or "").strip(),
            "url": url,
            "hot": str(hot) if hot else "",
            "pic": "",
            "source": source_key,
            "source_name": PROVIDERS[source_key]["name"],
        })
    return items


def parse_xxapi_douyin(data, source_key: str) -> list:
    """抖音返回字段略有不同"""
    if not data or data.get("code") != 200:
        return []
    items = []
    for idx, row in enumerate(data.get("data") or [], 1):
        if idx > TOP_N:
            break
        title = clean_title(
            row.get("title")
            or row.get("word")
            or row.get("sentence")
            or row.get("name")
            or ""
        )
        if not title:
            continue
        hot = row.get("hot_value") or row.get("hot") or row.get("hotValue") or ""
        url = row.get("url") or ("https://www.douyin.com/search/" + quote(title))
        items.append({
            "rank": idx,
            "title": title,
            "desc": "",
            "url": url,
            "hot": str(hot) if hot else "",
            "pic": "",
            "source": source_key,
            "source_name": PROVIDERS[source_key]["name"],
        })
    return items


def parse_vvhan(data, source_key: str) -> list:
    """vvhan: {type, list:[{index,title,url,hot_value},...]} 或 data 字段"""
    if not data:
        return []
    rows = data.get("list") or data.get("data") or []
    if not isinstance(rows, list):
        return []
    items = []
    for idx, row in enumerate(rows, 1):
        if idx > TOP_N:
            break
        title = clean_title(row.get("title") or row.get("name") or "")
        if not title:
            continue
        url = row.get("url") or row.get("mobilUrl") or row.get("link") or ""
        hot = row.get("hot_value") or row.get("hot") or row.get("hotValue") or ""
        items.append({
            "rank": row.get("index") or idx,
            "title": title,
            "desc": (row.get("desc") or "").strip(),
            "url": url,
            "hot": str(hot) if hot else "",
            "pic": "",
            "source": source_key,
            "source_name": PROVIDERS[source_key]["name"],
        })
    return items


PARSERS = {
    "xxapi": parse_xxapi,
    "xxapi_douyin": parse_xxapi_douyin,
    "vvhan": parse_vvhan,
}


def ensure_url(item: dict) -> dict:
    if item.get("url"):
        return item
    title = item["title"]
    sk = item["source"]
    if sk == "weibo":
        item["url"] = "https://s.weibo.com/weibo?q=" + quote(title)
    elif sk == "douyin":
        item["url"] = "https://www.douyin.com/search/" + quote(title)
    elif sk == "baidu":
        item["url"] = "https://www.baidu.com/s?wd=" + quote(title)
    elif sk == "zhihu":
        item["url"] = "https://www.zhihu.com/search?q=" + quote(title)
    elif sk == "toutiao":
        item["url"] = "https://so.toutiao.com/search?keyword=" + quote(title)
    return item


def fetch_source(source_key: str) -> tuple:
    cfg = PROVIDERS[source_key]
    for url, parser_name in cfg["endpoints"]:
        print("  → %s 尝试 %s ..." % (cfg["name"], url[:50]))
        data = http_get_json(url)
        parser = PARSERS.get(parser_name)
        if not parser:
            continue
        items = parser(data, source_key)
        if items:
            items = [ensure_url(it) for it in items]
            print("    成功 %d 条" % len(items))
            return source_key, items
        time.sleep(0.5)
    print("  [WARN] %s 全部失败" % cfg["name"])
    return source_key, []


def classify(title: str, desc: str = "") -> str:
    text = (title + " " + desc).lower()
    for cat, kws in CATEGORY_RULES:
        for kw in kws:
            if kw.lower() in text:
                return cat
    return DEFAULT_CATEGORY


def deduplicate(items: list) -> list:
    seen = set()
    out = []
    for it in items:
        key = re.sub(r"[^\w\u4e00-\u9fff]", "", it["title"]).lower()
        if len(key) < 4:
            out.append(it)
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def load_previous(path: Path):
    try:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("total", 0) > 0 and data.get("items"):
                return data
    except Exception:
        pass
    return None


def main():
    now = datetime.now(BEIJING)
    print("[%s] 开始抓取（v3 多源）..." % now.strftime("%Y-%m-%d %H:%M:%S"))

    out_path = Path(__file__).parent / "docs" / "data.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    by_source = {}
    all_items = []
    health = {"sources_ok": [], "sources_fail": []}

    with ThreadPoolExecutor(max_workers=5) as pool:
        futs = {pool.submit(fetch_source, k): k for k in PROVIDERS}
        for fut in as_completed(futs):
            key, items = fut.result()
            for it in items:
                it["category"] = classify(it["title"], it.get("desc", ""))
            by_source[key] = items
            all_items.extend(items)
            name = PROVIDERS[key]["name"]
            if items:
                health["sources_ok"].append(name)
            else:
                health["sources_fail"].append(name)

    before = len(all_items)
    all_items = deduplicate(all_items)
    if before != len(all_items):
        print("去重: %d → %d" % (before, len(all_items)))

    if len(all_items) < 3:
        prev = load_previous(out_path)
        if prev and prev.get("total", 0) >= 3:
            print("[FALLBACK] 使用上次成功数据")
            prev["fallback"] = True
            prev["health"] = health
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(prev, f, ensure_ascii=False, indent=2)
            return

    cat_count = {}
    for it in all_items:
        cat_count[it["category"]] = cat_count.get(it["category"], 0) + 1

    result = {
        "update_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "update_timestamp": int(now.timestamp()),
        "total": len(all_items),
        "category_stats": cat_count,
        "sources": by_source,
        "items": all_items,
        "fallback": False,
        "health": health,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("[OK] 共 %d 条" % result["total"])
    print("     成功: %s" % health["sources_ok"])
    if health["sources_fail"]:
        print("     失败: %s" % health["sources_fail"])
    print("     分类: %s" % cat_count)


if __name__ == "__main__":
    main()
