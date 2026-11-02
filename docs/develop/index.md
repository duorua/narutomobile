# 快速上手

> [!NOTE]
> 在开始之前请先自行学习[MaaFramework的开发文档](https://github.com/MaaXYZ/MaaFramework/blob/main/docs/zh_cn/1.1-%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B.md)，了解基于 MaaFramework 进行开发所需的基础知识。在学习开发初期遇到的大部分问题你都可以在文档里找到答案

## 1. 开发环境配置

### 1.1 编辑器推荐

我们**强烈推荐**使用 [VSCode](https://code.visualstudio.com/Download) 进行开发，因为社区提供了优秀的 [Maa Pipeline Support](https://marketplace.visualstudio.com/items?itemName=nekosu.maa-support) VSCode 插件来进行调试。

### 1.2 必要软件安装

1. **安装 VSCode** - 代码编辑器
2. **安装 Git** - 版本控制工具
3. **安装 Python** - 开发语言（**≥3.13**，推荐使用 **Python 3.13.15** 版本）
4. **安装 node.js** - 辅助开发（**版本≥22**,相关见于下方10.开发辅助环境）

### 1.3 常用开发工具

| 工具 | 简介 |
| --- | --- |
| [Maa Pipeline Support](https://marketplace.visualstudio.com/items?itemName=nekosu.maa-support) | VSCode 插件，提供调试、截图、获取 ROI 、取色等功能（强烈推荐） |
| [MaaPipelineEditor](https://github.com/kqcoxn/MaaPipelineEditor) | 任务流程pipeline可视化工具（推荐） |
| [MaaLogAnalyzer](https://github.com/MaaXYZ/MaaLogAnalyzer) | 日志分析工具，用于分析任务流程的执行情况 |

---

## 2. Python 安装详情

### 2.1 下载 Python

访问华为云镜像站下载 Python：

> [!NOTE]
> **镜像地址：** [https://repo.huaweicloud.com/python/3.13.15/](https://repo.huaweicloud.com/python/3.13.15/)
> **推荐下载：** [https://repo.huaweicloud.com/python/3.13.15/python-3.13.15-amd64.exe](https://repo.huaweicloud.com/python/3.13.15/python-3.13.15-amd64.exe)

### 2.2 安装 Python

运行下载的 Python 安装程序，**强烈建议**勾选 "Add Python to PATH" 选项，然后按照默认设置完成安装。

---

## 3. 克隆项目代码

使用 Git 克隆项目代码到本地：

```bash title="克隆项目代码"
git clone https://github.com/duorua/narutomobile.git
cd narutomobile
```

> [!TIP]
> 确保您已经安装了 Git 工具，否则无法执行上述命令。

---

## 4. 下载 OCR（文字识别）资源文件 [ppocr_v6.zip](https://download.maafw.xyz/MaaCommonAssets/OCR/ppocr_v6/ppocr_v6-small.zip) 解压到 `assets/resource/base/model/ocr/` 目录下，确保路径如下

```bash
   assets/resource/base/model/ocr/
   ├── det.onnx
   ├── keys.txt
   └── rec.onnx
```

---

## 5. 安装 Python 依赖

使用 uv 安装项目所需的 Python 依赖：

```bash title="安装Python依赖"
# 安装uv
pip install uv
# 创建虚拟环境并安装依赖
uv sync
```

> [!WARNING]  
>
> 由于项目统一配置了 vscode 的`maa插件`调试功能，所以必须要创建虚拟环境。

---

## 6. 验证安装

安装完成后，可以运行项目来验证是否安装成功：

```bash title="验证安装"
python -m agent.main <identifier>#<identifier>替换为uuid如"3be2c931-9c0d-4d69-9ebd-eed2263e06fd"
```

`identifier`属性与值可以放在`assets/interface.json`里的"agent"属性中

**✓ 如果能够正常启动，说明开发环境已经搭建完成！**

---

## 7. 开始开发

### 7.1 入门指南

1. 阅读 [M9A 开发须知](https://1999.fan/zh_cn/develop/development.html)，了解如何在本地以开发模式运行本项目（本项目与M9A的项目结构类似，可以作为学习参考）。

2. 如果不会写代码，但对某些功能的实现有明确的思路：
   - 参考 [任务流水线（Pipeline）协议](https://github.com/MaaXYZ/MaaFramework/blob/main/docs/zh_cn/3.1-%E4%BB%BB%E5%8A%A1%E6%B5%81%E6%B0%B4%E7%BA%BF%E5%8D%8F%E8%AE%AE.md) 学习如何将思路转化为具体实现
   - 了解如何在 `assets\resource\base\pipeline` 中编写流水线文件
   - 学习 [Project Interface 协议](https://github.com/MaaXYZ/MaaFramework/blob/main/docs/zh_cn/3.2-ProjectInterface%E5%8D%8F%E8%AE%AE.md#project-interface-%E5%8D%8F%E8%AE%AE)，了解如何让软件能够调用你写的流水线文件

3. 如果你有一定的 Python 基础，想要尝试为项目编写代码：
   - 阅读 [MaaFramework 集成接口](https://github.com/MaaXYZ/MaaFramework/blob/main/docs/zh_cn/2.2-%E9%9B%86%E6%88%90%E6%8E%A5%E5%8F%A3%E4%B8%80%E8%A7%88.md) 并**结合本项目源码**以了解如何为项目开发高级功能
   - **重要提示**：纸上学来终觉浅，绝知此事要躬行。不结合代码实践读文档，等于白读。

4. 为项目贡献你所编写的内容，请参考 [牛牛也能看懂的 GitHub Pull Request 使用指南](https://maa.plus/docs/zh-cn/develop/pr-tutorial.html)

---

## 8. 进行调试

| 工具 | 简介 |
| --- | --- |
| [Maa Pipeline Support](https://docs.maa.plus/zh-cn/develop/vsc-ext-tutorial.html) | VSCode 插件，提供调试、截图、获取 ROI 、取色等功能（强烈推荐） |

---

## 9. 常见问题与解决方案

### 9.1 运行项目问题

1. **错误**：提示 "Failed to load det or rec", "ocrer is null"
   **解决方案**：确保 MaaFramework 依赖已正确安装，且 OCR 模型文件完整

2. **错误**：提示找不到模块
   **解决方案**：检查是否已正确激活虚拟环境（如果使用了虚拟环境），或重新安装依赖

### 9.2 开发相关问题

1. **问题**：我在这个仓库里提了 Issue 很久没人回复
   **解决方案**：本项目目前紧缺人手，你可以先阅读文档自行尝试寻找解决方案。欢迎提交 PR 贡献代码！

---

## 10.其他工具

- 参见[tools.md](./tools)

---

## 完成

您已经成功搭建了 Maa Auto Naruto 的开发环境！

如果您在使用过程中遇到其他问题，请参考：

- [MaaFramework 官方文档](https://maafw.xyz/)

祝您开发愉快！
