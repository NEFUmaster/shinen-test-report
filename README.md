# 象恩检测报告静态网页

这是一个纯静态 PDF 检测报告展示网页，适合部署到 Cloudflare Pages、GitHub Pages 等免费静态托管平台。

## 访问路径

部署后：

- 根路径会自动跳转到 `./shinen/`
- 前台展示页：`/shinen/`
- PDF 文件：`/shinen/uploads/`
- 报告数据：`/shinen/data/reports.json`

## 本地预览

```powershell
cd "D:\codex file\pdf-report-site\docs"
python -m http.server 8000
```

打开：

```text
http://127.0.0.1:8000/shinen/
```

## Cloudflare Pages 部署

1. 打开 Cloudflare Pages。
2. 连接 GitHub 仓库：`NEFUmaster/shinen-report-site`。
3. Framework preset 选择 `None`。
4. Build command 留空。
5. Build output directory 填写：

```text
docs
```

部署完成后，Cloudflare 会给出一个公网地址，例如：

```text
https://你的项目名.pages.dev/shinen/
```

## GitHub Pages 部署

1. 打开 GitHub 仓库设置。
2. 进入 Pages。
3. Source 选择 `Deploy from a branch`。
4. Branch 选择 `main`。
5. Folder 选择 `/docs`。
6. 保存。

部署完成后，地址通常是：

```text
https://nefUmaster.github.io/shinen-report-site/shinen/
```

## 如何更新报告

纯静态版本没有后台上传功能。后续新增或修改报告时，需要更新仓库文件：

- 把 PDF 放到 `docs/shinen/uploads/`
- 修改 `docs/shinen/data/reports.json`
- 提交并推送到 GitHub

推送后，Cloudflare Pages 或 GitHub Pages 会自动重新部署。

## 当前功能

- 前台按分类展示 PDF 检测报告
- 支持搜索报告标题、分类、说明
- 支持 PDF 预览和下载
- 没有后台入口
- 没有服务器费用
