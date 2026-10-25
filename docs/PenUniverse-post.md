# 全网首发 | 有道词典笔视频播放器小程序：Doge视频

> 设备：有道词典笔 YDPX8-1（X8），OTA 4.61.0，Linux armv7l，936×280  
> 项目：**Doge视频**（本地视频启动器）  
> 开源：https://github.com/yangsongh/doge-video  
> 下载：https://github.com/yangsongh/doge-video/releases/latest

---

## 先说结论

有道词典笔没有公开的 `video` 组件，也不能像 Android 一样随便装播放器。但这个设备里其实藏着一个**系统视频播放器 App**（appid `8001661999525016`），数学课本、视频精讲等官方功能都在用它。

Doge视频做的事情很简单：

1. 扫描 `/userdisk/Favorite/Video` 下的 MP4；
2. 把 `file://` 路径交给系统播放器；
3. 用 `$falcon.navTo('falcon://8001661999525016/index', ...)` 调起播放；
4. 附带文件浏览器、自定义播放器 AppID、数字键盘和 PC 转码工具。

它不自己解码视频，所以不需要硬解、不需要移植 ffmpeg，也不需要 root 改系统。

![Doge视频列表](https://raw.githubusercontent.com/yangsongh/doge-video/main/docs/screenshot.png)

---

## 为什么值得写一篇

社区里之前更多是词典笔的词典、笔记、ADB、装第三方 App 的玩法，**视频播放**一直比较边缘：

- 设备是 Linux + framebuffer，不是 Android；
- 没有公开的 video 组件；
- 系统播放器是私有页面，参数和视频规格都要靠试；
- 装进去的小程序，重启后还可能被系统桌面清掉。

这次把整条链路跑通了：**本地视频列表 → 系统播放器 → 离线播放 → PC 转码 → 一键推送**。至少是我在社区里第一次见到完整可用的方案，所以标题用了“全网首发”；如果有更早的方案，欢迎在评论区补充。

---

## 核心原理

### 1. 系统播放器不是公开 API

从系统日志和 `pms` 注册信息里可以找到：

```text
appid: 8001661999525016
name : 视频播放器
page : pages/index/index
```

调起参数：

```js
$falcon.navTo('falcon://8001661999525016/index', {
  url: 'file:///userdisk/Favorite/Video/001_video.mp4',
  castUrl: 'file:///userdisk/Favorite/Video/001_video.mp4',
  title: '001_video.mp4',
  from: 'math-book'
});
```

`from: 'math-book'` 很关键。它不是随便写的来源标记，而是让播放器按“课本视频”的上下文初始化；去掉或改错，页面可能不认这个本地文件。

### 2. 视频规格是最大的坑

不是所有 MP4 都能播。实测：

| 规格 | 结果 |
| --- | --- |
| H.264 High，960×540，15fps，AAC | ✅ 正常 |
| H.264 Baseline，480×270，30fps，AAC | ❌ 黑屏，有声音/进度 |
| H.264 High，960×720，30fps，AAC | ❌ 播放器崩溃，小程序 abort，设备重启 |

最终稳定参数：

```text
H.264 High
960×540
15 fps
yuv420p
AAC-LC 44.1kHz stereo，约 96k
faststart
视频约 600k，音频约 96k
```

所以项目里带了一个 Windows 图形转码工具，内置 ffmpeg，不需要用户装 Python，也不需要懂命令行：

![转码工具](https://raw.githubusercontent.com/yangsongh/doge-video/main/docs/gui.png)

转码工具支持**硬件加速**：自动检测 Intel QSV / NVIDIA NVENC / AMD AMF，实际试开编码器；不可用时自动回退 `libx264`，单个文件硬件编码失败也会用软件重试。默认勾选，输出规格仍是 H.264 High / 960×540 / 15fps，不改变兼容性。

---

## 踩坑合集（温馨提示）

### 坑 1：重启后小程序从桌面消失

这是最容易被当成“包坏了”的问题。

系统桌面 App（appid `8080222437664451`）在启动/刷新时会执行 `cleanUnofficialApps`：

1. 从 Overmind 拉取 `appWhitelist`；
2. 白名单启用且非空时，对比本机已安装 appid；
3. 不在白名单里的应用调用 `removePackage`，原因记为 `remove_unofficial`。

日志里可以直接看到：

```text
start cleanUnofficialApps
installed: 8001145141919810,8001145141919811,8001145141919812
done, removed: ...
```

官方系统包的 `flag` 是 `3`，而 `miniapp_cli install` 安装的 sideload 包是 `flag: 16384`；被清掉的就是这些 `16384` 的包。清理只在白名单成功拉取且非空时执行，所以断网、配置拉取失败时会跳过，看起来就像“随机消失”。

桌面 App 的 JS 里留了一个测试开关：

```text
/userdata/.disable_app_whitelist_clean
```

文件存在时日志会打印：

```text
disabled by test flag, skip cleanUnofficialApps
```

并跳过清理。项目里带了补丁脚本：

```bash
# 开启：重启后不再自动清理 sideload 小程序
bash tools/fix_app_whitelist_clean.sh

# 恢复系统默认清理策略
bash tools/fix_app_whitelist_clean.sh --restore
```

或者手动：

```bash
adb shell touch /userdata/.disable_app_whitelist_clean
```

**温馨提示：**

- 这是绕过系统策略的测试开关，只建议在自己的设备上使用；
- OTA、恢复出厂或清理 `/userdata` 后可能丢失，重新执行即可；
- 真正长期合规的方式是让 appid 进入官方 `appWhitelist`，或者正式上架；
- 单纯把 appid 数字改成别的，不会自动进白名单。

### 坑 2：系统没有输入法

设置页原本用 `<input>` 输入播放器 AppID，但词典笔系统没有自带输入法，点上去无法输入。

最终改成**自绘数字键盘**：0–9、清空、退格、保存、默认。完全不用系统 IME，也不依赖键盘弹窗。

![AppID 数字键盘](https://raw.githubusercontent.com/yangsongh/doge-video/main/docs/settings.png)

### 坑 3：`adb push` 把后缀弄丢

早期推送用的是“目录 + 斜杠”：

```bash
adb push local.mp4 /userdisk/Favorite/Video/
```

在某些 adb 版本/环境下，目标解析不稳定。现在改成显式目标文件名，并强制补 `.mp4`：

```bash
adb push local /userdisk/Favorite/Video/001_video.mp4
```

如果看到系统播放器标题显示 `001_video.`，通常是播放器标题栏对长文件名的**显示截断**；文件本身仍是 `001_video.mp4`，用 `adb shell ls -l /userdisk/Favorite/Video` 可以确认。

### 坑 4：设备不是 Android

不要用 `adb install` 装 APK。词典笔跑的是 Falcon 小程序运行时，包是 `.amr`，安装命令是：

```bash
adb push 8001145141919820.1_0_0.amr /userdisk/Favorite/
adb shell "miniapp_cli install /userdisk/Favorite/8001145141919820.1_0_0.amr"
```

---

## 成本：分析 + 开发约 7 元

这个项目最想说明的一点是：

> **大部分分析、代码、调试和打包工作，是 DeepSeek Harness 完成的。**

从最初的“这个设备能不能播视频”，到找系统播放器 appid、试视频规格、写 Vue 页面、做数字键盘、修重启清理、写 ffmpeg 转码 GUI，再到最后的文档和发布，基本都是在 DeepSeek Harness 里一步步跑出来的。我主要负责提需求、在设备上点按钮、看日志和验收。

整个分析 + 开发过程的 API 调用成本大约 **7 元人民币**（不含设备和电费）。这不是广告，只是记录一个普通用户 + AI 编程工具，在冷门嵌入式设备上把一个想法跑通的真实成本。

---

## 功能清单

- 默认目录：`/userdisk/Favorite/Video`
- 自动扫描两级子目录，最多 200 个 MP4
- 手动文件浏览器：从 `/userdisk` 进入任意目录选 MP4
- 系统播放器 appid 可改，设置保存在 `settings.json`
- 自绘数字键盘，无输入法也能改 AppID
- Windows 图形转码工具：H.264 High / 960×540 / 15fps / AAC，内置 ffmpeg
- 一键 adb 推送，自动创建清理开关
- 重启后保留（在清理开关生效的前提下）

---

## 安装

1. 从 Releases 下载：
   - `8001145141919820.1_0_0.amr`
   - `DogeVideoConverter.exe`
2. 连接词典笔，确认 `adb devices` 能看到设备；
3. 安装：

```bash
adb push 8001145141919820.1_0_0.amr /userdisk/Favorite/
adb shell "miniapp_cli install /userdisk/Favorite/8001145141919820.1_0_0.amr"
adb shell touch /userdata/.disable_app_whitelist_clean
```

也可以直接用仓库脚本：

```bash
bash tools/install_to_device.sh ./8001145141919820.1_0_0.amr
```

4. 把 MP4 转码后放到 `/userdisk/Favorite/Video`；
5. 打开桌面「Doge视频」，点视频播放。

---

## 已知限制

- 只在 YDPX8-1（X8）/ 4.61.0 上验证；别的机型可能没有这个播放器 appid，或页面参数不同；
- 系统播放器是私有 App，系统 OTA 后页面/参数可能变化；
- 这是 sideload 小程序，不是官方上架应用；
- 清理开关是测试开关，不是官方长期方案；
- 不提供/不鼓励下载受版权保护的视频，工具只做本地转码和播放。

---

## 致谢

- DeepSeek Harness：大部分分析、编码、调试和文档
- Doge 漫画作者：BasePage / 小程序工程结构参考
- PenUniverse / PenMods 社区：设备资料和讨论
- 有道词典笔系统里的视频播放器：真正干活的是它

项目以 AGPLv3 开源，欢迎提 Issue / PR，也欢迎在评论区补充更多机型的测试结果。

---

**仓库：** https://github.com/yangsongh/doge-video  
**Releases：** https://github.com/yangsongh/doge-video/releases/latest  
**补丁脚本：** https://github.com/yangsongh/doge-video/blob/main/tools/fix_app_whitelist_clean.sh
