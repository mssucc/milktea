# AI Chatbox 桌面应用配置

本项目已配置为使用 **Tauri** 构建为桌面应用程序。

## 功能特性

- 独立桌面窗口（非浏览器网页）
- 固定窗口大小: 1200x800
- 最小窗口限制: 900x600
- 可调整大小，但保持合理比例
- 窗口居中显示

## 快速开始

### 1. 安装依赖

```bash
cd ai-chatbox-vue
npm install
```

### 2. 运行桌面应用（开发模式）

```bash
npm run tauri:dev
```

这将启动 Rust 后端并打开一个独立的桌面窗口。

### 3. 构建桌面应用（生产版本）

```bash
npm run tauri:build
```

构建完成后，安装包位于:
- Windows: `src-tauri/target/release/bundle/`
  - `.msi` - Windows 安装程序
  - `.exe` - 便携版可执行文件

## 自定义配置

### 修改窗口大小

编辑 `src-tauri/tauri.conf.json`:

```json
"windows": [{
  "title": "AI Chatbox",
  "width": 1200,      // 修改宽度
  "height": 800,      // 修改高度
  "minWidth": 900,    // 最小宽度
  "minHeight": 600,   // 最小高度
  "resizable": true,  // 是否允许调整大小
  "decorations": true // 是否显示窗口边框和标题栏
}]
```

### 无边框窗口模式

如果想创建类似聊天小部件的无边框窗口:

```json
"windows": [{
  "decorations": false,  // 无边框
  "transparent": true,   // 透明背景
  "alwaysOnTop": true    // 始终置顶
}]
```

### 固定大小窗口

防止用户调整窗口大小:

```json
"windows": [{
  "resizable": false,
  "maxWidth": 1200,
  "maxHeight": 800,
  "minWidth": 1200,
  "minHeight": 800
}]
```

## 窗口控制 API

可以在 Vue 组件中使用 Tauri API 控制窗口:

```typescript
import { getCurrentWindow } from '@tauri-apps/api/window';

const appWindow = getCurrentWindow();

// 最小化
appWindow.minimize();

// 最大化/恢复
appWindow.toggleMaximize();

// 关闭
appWindow.close();

// 设置窗口大小
appWindow.setSize({ width: 1000, height: 700 });

// 设置窗口位置
appWindow.setPosition({ x: 100, y: 100 });
```

## 系统要求

- Windows 10/11
- 需要安装 WebView2（Windows 10/11 通常已预装）

## 故障排除

### 构建失败

1. 确保已安装 Rust:
   ```bash
   rustc --version
   cargo --version
   ```

2. 如果没有安装，从 https://rustup.rs/ 安装

### 窗口不显示

检查 `vite.config.ts` 中的端口配置是否与 `tauri.conf.json` 中的 `devUrl` 一致。

### 图标生成

要添加自定义图标:

1. 准备一个 1024x1024 的 PNG 图标文件
2. 放在项目根目录，命名为 `app-icon.png`
3. 运行:
   ```bash
   npm run tauri icon app-icon.png
   ```

这会自动生成所有需要的图标尺寸。

## 参考资料

- [Tauri 文档](https://tauri.app/)
- [Tauri API 参考](https://tauri.app/v1/api/js/)
