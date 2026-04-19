# 前端说明

前端技术栈：

- Vue 3
- Vue Router
- Pinia
- ECharts
- Vite

## 推荐启动方式

优先使用项目根目录脚本：

- `scripts/start_system.bat`

这个脚本会自动：

- 检查依赖
- 启动前端
- 启动后端
- 打开浏览器

## 手动启动方式

```powershell
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## 构建检查

```powershell
cd frontend
npm run build
```

## iPad 访问

前端开发服务器支持局域网访问，iPad 可以通过：

```text
http://你的电脑IPv4地址:5173
```

访问系统。

## PWA 说明

当前前端已具备基础 PWA 支持：

- `public/manifest.webmanifest`
- `index.html` 中的移动端与主屏幕 meta 配置
- `public/icons/` 中的图标资源

当前能力包括：

- 添加到主屏幕
- 更接近 App 的独立打开方式

当前不包括：

- Service Worker
- 离线缓存

## 页面模式

前端当前包含两种使用模式：

- 训练模式
- 管理模式

默认进入训练模式，右上角按钮可切换。
