# 体能训练管理平台 V1

这是一个以 `iPad / 平板横屏` 为主要使用场景的体能训练管理平台，面向团队训练管理、训练执行和训练数据追踪。

当前版本已经打通以下主流程：

- 动作库管理
- 训练模板管理
- 计划分配与分配总览
- 训练模式执行
- 自动调重建议
- 测试数据记录
- 训练数据查看
- Windows 一键初始化与一键启动
- iPad / PWA 基础支持
- 单入口启动 + 右上角模式切换

## 当前使用方式

系统目前采用 **免登录模式**：

- 打开系统后默认进入 **训练模式**
- 右上角可切换到 **管理模式**
- 系统会记住上次使用的模式
- 不需要输入账号密码

## 环境要求

请先安装以下软件：

- Python `3.12.x`
- Node.js `18+`
- Git

建议安装时都勾选加入 PATH。

## 本地启动

### 最简单方式

平时只需要双击：

- `scripts/start_system.bat`

这个脚本会自动判断是否缺少环境或依赖：

- 如果是第一次运行，会自动执行初始化
- 初始化完成后会继续启动前后端
- 然后自动打开浏览器

### 初始化脚本

如果你需要手动重装环境，可以单独双击：

- `scripts/init_system.bat`

它会自动完成：

- 检查 Python / Node.js / npm
- 创建后端虚拟环境
- 安装后端依赖
- 初始化数据库
- 导入示例数据
- 安装前端依赖

## iPad 访问方式

请确认：

- iPad 和电脑连接在同一个 Wi-Fi
- 电脑已经运行 `scripts/start_system.bat`

然后在 iPad Safari 中打开：

```text
http://你的电脑IPv4地址:5173
```

例如：

```text
http://192.168.1.25:5173
```

## 添加到 iPad 主屏幕

1. 用 Safari 打开系统首页
2. 点击“分享”
3. 选择“添加到主屏幕”
4. 回到主屏幕后点击图标即可像 App 一样打开

## 目录结构

```text
backend/    后端服务、数据库、业务逻辑、初始化脚本
frontend/   前端页面、组件、状态管理、PWA 资源
scripts/    Windows 一键初始化与启动脚本
```

## GitHub 上传流程

### 第一步：安装 Git

安装完成后，在终端执行：

```powershell
git --version
```

如果能看到版本号，就说明 Git 可用。

### 第二步：在 GitHub 新建私有仓库

建议：

- 新建 **私有仓库**
- 创建时不要勾选自动生成 README

### 第三步：本地上传

在项目根目录执行：

```powershell
git init
git add .
git commit -m "初始化体能训练管理平台 V1"
git branch -M main
git remote add origin 你的仓库地址
git push -u origin main
```

## 跨电脑继续开发

在新电脑上：

1. 安装 Python 3.12、Node.js、Git
2. 克隆仓库
3. 进入项目目录
4. 双击 `scripts/start_system.bat`

如果新电脑还没有依赖环境，脚本会自动初始化。

## 协作文档

为了让其他开发者或其他 AI / vibe coding 工具快速接手，这个仓库应同时维护：

- `PROJECT_CONTEXT.md`
- `DEVELOPMENT_GUIDE.md`

它们分别负责：

- 项目背景、功能边界、当前架构、业务规则
- 编码规范、改动原则、模块分层、验证要求

## 上传前检查

上传到 GitHub 前，建议至少确认：

```powershell
cd frontend
npm run build
```

```powershell
cd ..
python -m compileall backend\app
```

并确认：

- `README.md` 不乱码
- 示例数据可正常初始化
- `scripts/start_system.bat` 可以直接启动

## 常见问题

### 1. 找不到 Python

请安装 Python `3.12.x`，并确认：

```powershell
python --version
```

输出应为：

```text
Python 3.12.x
```

### 2. 找不到 Node.js 或 npm

请安装 Node.js `18+`，然后重新打开终端，再执行：

```powershell
node -v
npm -v
```

### 3. 找不到 Git

请安装 Git，并确认：

```powershell
git --version
```

### 4. 浏览器打不开页面

请检查：

- 前端是否运行在 `5173`
- 后端是否运行在 `8000`
- 是否有其他程序占用了端口

### 5. iPad 打得开页面但没有数据

常见原因：

- 后端没有成功启动
- 电脑防火墙拦截了 `8000`
- iPad 和电脑不在同一个 Wi-Fi
