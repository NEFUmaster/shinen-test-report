# 象恩检测报告网页

一个可本地运行、也可部署到公网的 PDF 检测报告展示网站。

## 本地启动

```powershell
cd "D:\codex file\pdf-report-site"
$env:ADMIN_USER="shinen"
$env:ADMIN_PASSWORD="请改成你自己的强密码"
python server.py
```

本地访问：

- 前台展示：http://127.0.0.1:8000/shinen/
- 后台管理：http://127.0.0.1:8000/shinen/shinenadmin

同一 Wi-Fi 下手机访问：

- 前台展示：http://192.168.3.17:8000/shinen/
- 后台管理：http://192.168.3.17:8000/shinen/shinenadmin

如果电脑的 Wi-Fi IP 变化，需要用新的 IPv4 地址替换 `192.168.3.17`。

## 公网部署

这个项目包含 `render.yaml`，可以部署到 Render 这类支持 Python Web Service 和持久磁盘的平台。

部署后访问地址通常类似：

- 前台展示：`https://你的服务名.onrender.com/shinen/`
- 后台管理：`https://你的服务名.onrender.com/shinen/shinenadmin`

公网部署前必须设置环境变量：

- `ADMIN_USER`：后台用户名，例如 `shinen`
- `ADMIN_PASSWORD`：后台密码，请使用强密码
- `APP_STORAGE_DIR`：持久化存储路径，Render 配置里默认为 `/var/data`
- `PYTHON_VERSION`：建议固定为 `3.11.9`

## 功能

- 前台按分类展示 PDF 检测报告
- 支持搜索报告标题、分类、说明
- 后台上传新的 PDF 报告
- 后台修改报告标题、分类、说明
- 后台删除报告
- 后台页面和写入接口需要账号密码

## 数据位置

本地默认：

- PDF 文件：`uploads/`
- 报告数据：`data/reports.json`

公网部署时：

- 数据会写入 `APP_STORAGE_DIR` 下的 `uploads/` 和 `data/reports.json`
- 首次启动会把项目内已有的 9 份 PDF 和报告数据复制到持久化目录
