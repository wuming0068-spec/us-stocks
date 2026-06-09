# 美股自选股监控系统

个人美股自选股每日监控，基于 akshare 数据 + GitHub Actions 定时更新 + GitHub Pages 展示 + pushplus 微信推送。

## 功能

- 📊 自选股数据展示：开盘/收盘/昨收、涨跌幅、成交量、成交均价、MA5/MA20、KDJ
- 🏭 按行业分组，市值排序
- 🎯 买卖信号识别（基于 KDJ + MA）
- 🔄 每日早晨 8:00（北京时间）自动更新数据
- 📱 移动端适配
- 📲 pushplus 微信晨报推送

## 本地预览

```bash
cd docs
python -m http.server 8080
# 打开浏览器访问 http://localhost:8080
```

## 使用方式

### 自选股管理
- 点击「+ 添加」输入美股代码
- 点击 ⚙ 进入管理面板，支持批量添加和删除
- 自选股列表保存在浏览器 localStorage

### 手动刷新
点击「🔄 刷新」按钮（每日限 10 次强制更新）

## 部署到 GitHub Pages

1. 创建 GitHub 仓库，推送代码
2. Settings → Pages → Source: `Deploy from a branch` → Branch: `master` / Folder: `/docs`
3. Settings → Secrets and variables → Actions → 添加 `PUSHPLUS_TOKEN`
4. GitHub Actions 会在每个交易日 UTC 00:00 自动运行

## 自定义自选股

在浏览器中添加/删除即可，自动保存到 localStorage。

如需修改默认自选股列表，编辑 `docs/js/app.js` 中 `loadWatchlist()` 的种子数据。

## 技术栈

- 前端：HTML + CSS + Vanilla JS
- 数据：akshare (Python)
- 定时：GitHub Actions
- 推送：pushplus
