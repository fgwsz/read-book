# read-book – 命令行阅读器

[![Python Version](https://img.shields.io/badge/python-3.6%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**read-book** 是一个纯文本、键盘驱动的命令行阅读器，专为阅读大型文本文件（电子书、日志、报告等）设计。它支持书签（带标签）、笔记（完整 CRUD）、自动进度记录，并提供彩色终端界面增强阅读体验。

## 特性

- **高效阅读**：按非空行分段，支持 `↑/↓` 滚动、`g` 跳转至任意段落。
- **书签管理**：添加带标签的书签（`m`），浏览列表（`b`），编辑标签（`e`）或删除（`d`），退出时自动记录当前位置。
- **笔记系统**：为任意段落添加笔记（`n`），在笔记管理界面（`l`）进行编辑/删除，阅读时可随时切换笔记显示（`N`）。
- **进度恢复**：每次退出自动保存最后阅读段落，再次打开书籍时自动跳转。
- **元数据独立**：每本书的元数据（书签、笔记、进度）保存在书籍目录下的 `.meta.json` 文件中，使用相对路径，支持整体目录迁移。
- **终端美化**：正文加粗、笔记高亮、按钮彩色提示，兼容所有支持 ANSI 的终端（Windows Terminal、iTerm2、GNOME Terminal 等）。
- **零依赖**：仅使用 Python 标准库，无需额外安装。

## 安装

```bash
# 克隆仓库
git clone https://github.com/fgwsz/read-book.git
cd read-book

# （可选）安装到系统路径
chmod +x read-book.py
sudo cp read-book.py /usr/local/bin/read-book
```

## 使用方法

```bash
python read-book.py <文本文件>
```

例如：
```bash
python read-book.py ~/books/novel.txt
```

## 快捷键

| 按键 | 功能 |
|------|------|
| `↑` / `↓` | 上一段 / 下一段 |
| `g` | 跳转到指定段落（输入数字） |
| `m` | 为当前段落添加书签（可输入标签） |
| `b` | 打开书签列表（上下选择，Enter 跳转，e 编辑，d 删除） |
| `n` | 为当前段落添加笔记 |
| `l` | 管理当前段落的笔记（编辑、删除） |
| `N` | 切换阅读界面笔记显示/隐藏 |
| `i` | 查看当前段落的详情（书签标签+笔记） |
| `q` / `ESC` | 退出（自动保存进度并添加书签） |

## 数据存储

- 元数据文件：与书籍文件同目录下的 `.meta.json`
- 格式示例：
```json
{
  "relative/path/to/book.txt": {
    "bookmarks": [
      {"idx": 10, "timestamp": "2026-07-21T10:30:00", "label": "精彩开头"}
    ],
    "notes": {
      "5": [{"timestamp": "2026-07-21T10:35:00", "content": "注意这个伏笔"}]
    },
    "last_position": 10
  }
}
```
- 完全基于相对路径，整个目录可随意移动。

## 自定义配置

暂无外部配置文件，所有设置（颜色、快捷键）可在代码中修改（参见 `TerminalStyler` 和 `KeyBinding` 类）。

## 贡献

欢迎提交 Issue 和 Pull Request。请确保代码符合 PEP8，并附带测试（目前无自动化测试，手动验证即可）。

## 许可证

MIT License – 详见 [LICENSE](LICENSE) 文件。

---

# read-book 开发者文档

本文档面向想要了解内部架构、扩展功能或修改行为的开发者。

## 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                     MainController                      │
│  - 主循环：渲染 → 获取按键 → 分发命令                   │
│  - 管理显示状态（show_notes）                           │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                   命令层 (Handlers)                     │
│  每个命令实现 ICommandHandler，执行业务逻辑             │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                    服务层 (Services)                    │
│  ReadingService, BookmarkService, NoteService           │
│  封装业务逻辑，调用存储层                               │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│                   存储层 (Repository)                   │
│  IMetadataRepository 接口 + JsonMetadataRepository      │
│  负责持久化书签、笔记、进度                             │
└─────────────────────────────────────────────────────────┘
```

## 核心模块说明

### 领域模型 (`Bookmark`, `Note`)

纯数据类，提供 `to_dict()` / `from_dict()` 用于 JSON 序列化。

```python
class Bookmark:
    idx: int          # 段落索引（0-based）
    timestamp: str    # ISO 格式
    label: str        # 用户标签
```

### 存储接口 `IMetadataRepository`

所有持久化操作均通过此接口，便于替换存储后端（如 SQLite、远程 API）。

- `get_bookmarks(file_path) -> List[Bookmark]`
- `add_bookmark(file_path, bookmark)`
- `delete_bookmark(file_path, bookmark)`
- `update_bookmark(file_path, old, new_label)`
- `get_notes(file_path, idx) -> List[Note]`
- `add_note(file_path, idx, note)`
- `delete_note(file_path, idx, note)`
- `update_note(file_path, idx, old, new_content)`
- `get_last_position(file_path) -> Optional[int]`
- `set_last_position(file_path, position)`

### 实现 `JsonMetadataRepository`

- 元数据文件：书籍所在目录下的 `.meta.json`
- 内部以**相对路径**（相对于该目录）为键存储各书籍数据。
- 当书籍文件移动时，相对路径不变（只要目录结构不变），元数据依然有效。

### 服务层

- `ReadingService`：管理当前阅读位置，提供 `go_to()`, `next()`, `prev()`。
- `BookmarkService`：封装书签操作，并添加当前时间戳。
- `NoteService`：封装笔记操作。

### 命令层

每个命令继承 `ICommandHandler` 并实现 `execute()`。控制器通过命令枚举 `Command` 查找处理器。

添加新命令步骤：
1. 在 `Command` 枚举中添加新值。
2. 在 `KeyBinding` 中绑定按键。
3. 创建新的 Handler 类实现 `execute()`。
4. 在 `MainController.__init__` 中注册到 `self.handlers` 字典。

### 视图层

- `BookmarkListView`：渲染书签列表，处理交互（上下选择、编辑、删除）。
- `NoteManagementView`：类似，用于笔记管理。
- `DetailView`：静态显示详情，仅用于查看。

### 工具类

- `TerminalStyler`：ANSI 样式工具，可自定义颜色。
- `KeyBinding`：按键→命令映射，可重写以支持自定义快捷键。
- `Platform`：抽象平台键盘输入（Windows / Unix），便于测试。
- `ConsoleHelper`：清屏、终端宽度、文本截断等。

## 数据格式（.meta.json）

顶层为对象，键为相对路径（使用 `/` 分隔），值为：

```json
{
  "bookmarks": [
    {"idx": 0, "timestamp": "ISO", "label": "string"}
  ],
  "notes": {
    "1": [{"timestamp": "ISO", "content": "string"}]
  },
  "last_position": 0
}
```

- `idx` 为段落索引（0-based）
- 笔记使用字符串形式的数字键，便于 JSON 解析

## 扩展建议

### 添加新命令（示例：搜索）

1. 添加 `Command.SEARCH`
2. 在 `KeyBinding` 中绑定 `Ctrl+F` 或 `/`
3. 创建 `SearchHandler`，调用 `FileReader` 的搜索方法（需先实现）
4. 注册到 `self.handlers`

### 更换存储后端

实现新的 `IMetadataRepository` 子类，如 `SqliteRepository`，并在 `main()` 中替换 `JsonMetadataRepository`。

### 自定义样式

修改 `TerminalStyler` 类中的颜色常量，或增加新的样式方法。

## 测试

目前无自动化测试。推荐使用 `unittest` 或 `pytest` 对以下关键模块编写测试：
- `JsonMetadataRepository`（文件读写）
- `ReadingService`（位置管理）
- `Command` 处理（可模拟平台输入）

## 依赖

- Python 3.6+
- 标准库：`os`, `sys`, `json`, `datetime`, `textwrap`, `platform`, `array`, `abc`, `typing`, `enum`

无第三方依赖，但可选用 `chardet` 增强编码检测。

---

*本文档随项目更新，如有疑问请提交 Issue。*
