#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自媒体热点工作台 - 热点抓取 + 自动分类脚本
使用 Python 标准库，无需额外依赖。
数据源：https://api-hot.imsyy.top （免费公开接口，无需 Key）
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ==================== 配置 ====================
API_BASE = "https://api-hot.imsyy.top"
SOURCES = {
    "weibo": "微博",
    "douyin": "抖音",
    "zhihu": "知乎",
    "toutiao": "今日头条",
}
# 每个平台取前 N 条
TOP_N = 15

# 分类关键词规则（优先级从高到低）
CATEGORY_RULES = [
    ("情感", ["分手", "复合", "恋爱", "结婚", "离婚", "出轨", "相亲", "单身", "情侣", "表白", "渣男", "渣女", "恋爱脑", "感情", "暧昧", "暗恋", "相亲角", "婚恋"]),
    ("娱乐", ["明星", "综艺", "电影", "电视剧", "演员", "歌手", "偶像", "粉丝", "演唱会", "流量", "顶流", "出道", "退圈", "塌房", "恋情", "绯闻", "官宣", "代言", "综艺节目", "选秀"]),
    ("科技", ["AI", "人工智能", "芯片", "华为", "苹果", "特斯拉", "太空", "火箭", "5G", "6G", "手机", "电脑", "机器人", "自动驾驶", "元宇宙", "ChatGPT", "大模型", "芯片制裁", "半导体", "量子"]),
    ("财经", ["股票", "基金", "房价", "楼市", "经济", "GDP", "通胀", "降息", "加息", "理财", "银行", "融资", "上市", "破产", "裁员", "薪资", "物价", "消费", "投资", "创业板", "A股"]),
    ("时政", ["政府", "政策", "两会", "外交", "军事", "国防", "主席", "总理", "人大", "政协", "制裁", "战争", "冲突", "国际", "联合国", "峰会", "法规", "立法"]),
    ("民生", ["教育", "医疗", "养老", "社保", "就业", "高考", "中考", "物价", "菜价", "地铁", "公交", "停电", "停水", "疫情", "疫苗", "医院", "学校", "幼儿园", "养老金", "医保"]),
    ("搞笑", ["沙雕", "整活", "笑死", "社死", "迷惑", "离谱", "神操作", "名场面", "鬼畜", "段子", "表情包", "整蛊", "翻车", "迷惑行为"]),
    ("社会", ["车祸", "火灾", "地震", "救人", "警察", "法院", "判决", "犯罪", "盗窃", "诈骗", "失踪", "遇害", "坠亡", "纠纷", "维权", "上热搜"]),
]

DEFAULT_CATEGORY = "其他"

# 北京时区
BEIJING = timezone(timedelta(hours=8))


def fetch_source(source_key: str) -> list:
    """抓取单个平台热榜，返回标准化列表"""
    url = f"{API_BASE}/{source_key}"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; HotWorkbench/1.0)",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[WARN] 抓取 {source_key} 失败: {e}")
        return []

    if data.get("code") != 200:
        print(f"[WARN] {source_key} 返回异常: {data.get('message')}")
        return []

    items = []
    for idx, item in enumerate(data.get("data", [])[:TOP_N], 1):
        title = item.get("title") or item.get("name") or ""
        if not title:
            continue
        items.append({
            "rank": idx,
            "title": title.strip(),
            "desc": (item.get("desc") or item.get("description") or "").strip(),
            "url": item.get("url") or item.get("mobileUrl") or item.get("link") or "",
            "hot": item.get("hot") or item.get("hotValue") or item.get("score") or "",
            "pic": item.get("pic") or item.get("cover") or "",
            "source": source_key,
            "source_name": SOURCES.get(source_key, source_key),
        })
    return items


def classify(title: str, desc: str = "") -> str:
    """根据关键词规则自动分类"""
    text = (title + " " + desc).lower()
    for cat, keywords in CATEGORY_RULES:
        for kw in keywords:
            if kw.lower() in text:
                return cat
    return DEFAULT_CATEGORY


def main():
    print(f"[{datetime.now(BEIJING).strftime('%Y-%m-%d %H:%M:%S')}] 开始抓取热点...")

    all_items = []
    for key in SOURCES:
        print(f"  → 正在抓取 {SOURCES[key]} ...")
        items = fetch_source(key)
        for it in items:
            it["category"] = classify(it["title"], it["desc"])
        all_items.extend(items)
        print(f"    得到 {len(items)} 条")

    # 按平台分组，方便前端展示
    by_source = {}
    for it in all_items:
        src = it["source"]
        if src not in by_source:
            by_source[src] = []
        by_source[src].append(it)

    # 统计分类
    cat_count = {}
    for it in all_items:
        cat_count[it["category"]] = cat_count.get(it["category"], 0) + 1

    result = {
        "update_time": datetime.now(BEIJING).strftime("%Y-%m-%d %H:%M:%S"),
        "update_timestamp": int(datetime.now(BEIJING).timestamp()),
        "total": len(all_items),
        "category_stats": cat_count,
        "sources": by_source,
        "items": all_items,  # 扁平列表，方便筛选
    }

    # 写入 docs/data.json
    out_path = Path(__file__).parent / "docs" / "data.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] 共抓取 {len(all_items)} 条热点，已写入 {out_path}")
    print(f"     分类统计: {cat_count}")


if __name__ == "__main__":
    main()
