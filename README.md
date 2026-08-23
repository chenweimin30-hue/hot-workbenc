# 🔥 自媒体热点工作台

每天自动抓取微博 / 抖音 / 知乎 / 今日头条热搜 → 自动分类 → 手机上像 APP 一样生成三平台文案、收集素材。

完全免费，零服务器成本，基于 **GitHub Actions + GitHub Pages**。

---

## 功能一览

| 功能 | 说明 |
|------|------|
| 📡 雷达 | 自动抓取四大平台热搜，关键词规则自动分类（社会/娱乐/情感/科技/财经/时政/民生/搞笑/其他） |
| ✍️ 文案 | 填一次 DeepSeek API Key（只存你手机浏览器），一键生成头条 / 小红书 / 抖音三平台文案 |
| 🗂️ 素材 | 手动记录灵感、链接，数据存在本机 localStorage |

---

## 8 步快速部署（新手友好）

### 第 1 步：注册 / 登录 GitHub
打开 https://github.com 注册账号（已有就直接登录）。

### 第 2 步：新建仓库
1. 右上角 **+** → **New repository**
2. Repository name 填：`hot-workbench`（随便取，英文即可）
3. 选 **Public**
4. **不要**勾选 Add a README
5. 点 **Create repository**

### 第 3 步：上传代码
1. 下载本项目的 zip 包并解压
2. 在刚创建的仓库页面，点 **uploading an existing file**
3. 把解压后的所有文件（fetch_hot.py、requirements.txt、.github 文件夹、docs 文件夹、README.md）拖进去
4. 底部 Commit changes → 点绿色按钮

> 注意：要保持目录结构，`.github/workflows/daily.yml` 和 `docs/index.html` 必须在正确位置。

### 第 4 步：开启 GitHub Pages
1. 仓库页面 → **Settings** → 左侧 **Pages**
2. Source 选 **Deploy from a branch**
3. Branch 选 **main**，文件夹选 **/docs**
4. 点 **Save**
5. 等 1~2 分钟，页面会显示你的访问地址，类似：  
   `https://你的用户名.github.io/hot-workbench/`

### 第 5 步：开启 Actions 权限
1. 仓库 → **Settings** → 左侧 **Actions** → **General**
2. 找到 **Workflow permissions**
3. 选中 **Read and write permissions**
4. 勾选 **Allow GitHub Actions to create and approve pull requests**（可选）
5. 点 **Save**

### 第 6 步：手动跑一次 Actions（立即看到数据）
1. 仓库 → 顶部 **Actions** 标签
2. 左侧点 **Daily Hot Fetch**
3. 右侧 **Run workflow** → 绿色 **Run workflow**
4. 等 30 秒~1 分钟，状态变绿就成功了
5. 回到 Pages 地址刷新，就能看到热搜了

### 第 7 步：手机添加到主屏幕
1. 用手机 Chrome / Safari 打开你的 Pages 地址
2. Chrome：菜单 → **添加到主屏幕**
3. Safari：分享 → **添加到主屏幕**
4. 以后就像 APP 一样点图标打开

### 第 8 步：（可选）配置 DeepSeek 文案功能
1. 去 https://platform.deepseek.com 注册，拿到 API Key（新用户有免费额度）
2. 打开工作台 → **文案** 标签 → 粘贴 Key
3. Key 只存在你手机浏览器的 localStorage，不会上传到 GitHub

---

## 定时任务说明

GitHub Actions 会在每天 **北京时间 08:00 和 20:00** 自动运行抓取脚本并更新 `docs/data.json`。

也可以随时在 Actions 页面手动触发。

---

## 目录结构

```
hot-workbench/
├── fetch_hot.py              # 抓热点 + 分类（纯标准库）
├── requirements.txt          # 无第三方依赖
├── .github/workflows/daily.yml
├── docs/
│   ├── index.html            # 手机看板页面
│   └── data.json             # 每天自动更新的数据
└── README.md
```

---

## 常见问题

**Q：Actions 跑失败了？**  
A：检查 Settings → Actions → General 是否给了 write 权限。再看 Actions 日志里具体报错。

**Q：页面打开是空的 / 加载失败？**  
A：确认 Pages 的 Source 选的是 **main 分支 + /docs 文件夹**，并且已经手动跑通过一次 Actions。

**Q：热搜接口挂了怎么办？**  
A：数据源用的是公开免费接口 `api-hot.imsyy.top`。如果长期不可用，可以换成自己部署的 DailyHotApi，只需改 `fetch_hot.py` 里的 `API_BASE`。

**Q：想改分类关键词？**  
A：编辑 `fetch_hot.py` 里的 `CATEGORY_RULES` 即可，改完 push 后下次 Actions 生效。

---

## 后续可优化方向（部署成功后再考虑）

1. 每天自动预生成文案（需要把 DeepSeek Key 存成 GitHub Secret）
2. 做成真正的 PWA（桌面图标 + 启动画面 + 全屏）
3. 保存历史热点数据（现在每天覆盖）
4. 先稳定跑通现有版本

有问题直接在 Issues 提，或继续在对话里问我。
