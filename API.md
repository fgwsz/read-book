# read-book API 参考文档（详细版）

本文档为 `read-book` 命令行阅读器的完整 API 参考，涵盖所有公开类、方法、属性和函数。适合开发者进行二次开发、扩展或集成。

---

## 目录
1. [领域模型](#领域模型)  
   - `Bookmark`
   - `Note`
2. [存储层](#存储层)  
   - `IMetadataRepository` (接口)
   - `JsonMetadataRepository` (实现)
3. [文件读取](#文件读取)  
   - `FileReader`
4. [服务层](#服务层)  
   - `ReadingService`
   - `BookmarkService`
   - `NoteService`
5. [命令处理器](#命令处理器)  
   - `ICommandHandler` (接口)
   - 各个处理器实现类
6. [视图层](#视图层)  
   - `BookmarkListView`
   - `NoteManagementView`
   - `DetailView`
7. [控制器](#控制器)  
   - `MainController`
8. [工具类](#工具类)  
   - `TerminalStyler`
   - `KeyBinding`
   - `ConsoleHelper`
   - `Platform` 及其子类 `WindowsPlatform` / `UnixPlatform`
   - `PlatformFactory`
9. [枚举](#枚举)  
   - `Command`
10. [全局函数](#全局函数)  
    - `main()`

---

## 领域模型

### `class Bookmark`
表示一个书签。

**属性**：
| 名称 | 类型 | 描述 |
|------|------|------|
| `idx` | `int` | 段落索引（0-based） |
| `timestamp` | `str` | ISO 8601 格式时间戳（例如 `"2026-07-21T10:30:45.123456"`） |
| `label` | `str` | 用户自定义标签，可为空字符串 |

**方法**：

#### `to_dict() -> Dict[str, Any]`
将对象转换为可 JSON 序列化的字典。

- **返回值**：`{'idx': int, 'timestamp': str, 'label': str}`
- **示例**：
  ```python
  bm = Bookmark(3, "2026-01-01T12:00:00", "精彩")
  bm.to_dict()  # {'idx': 3, 'timestamp': '2026-01-01T12:00:00', 'label': '精彩'}
  ```

#### `from_dict(data: Dict[str, Any]) -> Bookmark`
类方法，从字典构造 `Bookmark` 实例。

- **参数**：`data` – 必须包含 `idx`, `timestamp` 键，`label` 可选。
- **返回值**：`Bookmark` 实例
- **示例**：
  ```python
  Bookmark.from_dict({'idx': 0, 'timestamp': '...', 'label': 'start'})
  ```
- **注意**：若 `label` 缺失，默认空字符串。

---

### `class Note`
表示一条笔记。

**属性**：
| 名称 | 类型 | 描述 |
|------|------|------|
| `timestamp` | `str` | ISO 8601 格式时间戳 |
| `content` | `str` | 笔记内容（纯文本） |

**方法**：

#### `to_dict() -> Dict[str, Any]`
返回 `{'timestamp': str, 'content': str}`。

#### `from_dict(data: Dict[str, Any]) -> Note`
类方法构造，要求 `timestamp` 和 `content` 都存在。

---

## 存储层

### `class IMetadataRepository` (抽象基类)
定义元数据存储的统一接口。所有存储实现必须继承此类并实现以下方法。

#### `get_bookmarks(file_path: str) -> List[Bookmark]`
- **描述**：返回指定书籍的所有书签。
- **参数**：`file_path` – 书籍文件的绝对路径（存储实现可使用或忽略）。
- **返回值**：书签列表，若无则返回空列表。

#### `add_bookmark(file_path: str, bookmark: Bookmark) -> None`
- **描述**：添加一个新书签。
- **参数**：
  - `file_path` – 书籍路径
  - `bookmark` – 要添加的 `Bookmark` 对象

#### `delete_bookmark(file_path: str, bookmark: Bookmark) -> None`
- **描述**：删除一个书签。通常根据 `idx` 和 `timestamp` 唯一确定。
- **参数**：同添加。

#### `update_bookmark(file_path: str, old: Bookmark, new_label: str) -> None`
- **描述**：更新指定书签的标签，并自动更新 `timestamp` 为当前时间。
- **参数**：
  - `old` – 已有的书签对象（用于定位）
  - `new_label` – 新标签字符串

#### `get_notes(file_path: str, idx: int) -> List[Note]`
- **描述**：返回指定段落的所有笔记。
- **参数**：`idx` – 段落索引（0-based）
- **返回值**：笔记列表，可能为空。

#### `add_note(file_path: str, idx: int, note: Note) -> None`
为指定段落添加一条笔记。

#### `delete_note(file_path: str, idx: int, note: Note) -> None`
删除指定笔记（匹配 `timestamp` 和 `content`）。

#### `update_note(file_path: str, idx: int, old: Note, new_content: str) -> None`
更新笔记内容，同时更新 `timestamp`。

#### `get_last_position(file_path: str) -> Optional[int]`
- **描述**：获取上次退出时记录的段落索引。
- **返回值**：若从未记录则返回 `0`（实际可能是 `None`，但此接口返回 `Optional[int]`，实现通常返回 `0` 或存储值）。

#### `set_last_position(file_path: str, position: int) -> None`
更新最后阅读位置。

---

### `class JsonMetadataRepository(IMetadataRepository)`
基于 JSON 文件的存储实现。

**构造函数**：
```python
JsonMetadataRepository(book_file_path: str)
```
- **参数**：`book_file_path` – 书籍文件的绝对路径。
- **行为**：
  1. 计算所在目录，并在此目录下查找/创建 `.meta.json` 文件。
  2. 计算书籍相对于该目录的相对路径（使用 POSIX 风格 `/` 分隔）。
  3. 如果该相对路径在 JSON 中不存在，则创建默认条目 `{"bookmarks": [], "notes": {}, "last_position": 0}`。

**内部属性**（仅供内部使用）：
- `_data` – 加载的整个 JSON 对象（字典）
- `meta_file` – 元数据文件完整路径
- `rel_path` – 当前书籍的相对路径（用作键）

**实现的所有接口方法**与接口定义完全一致，不再重复。但需要注意：
- 所有方法内部均使用 `_get_entry()` 获取当前书籍的数据字典。
- 每次修改后调用 `_save()` 立即写入磁盘。

**额外说明**：
- 该实现保证原子性（写入前先完整构造字典）。
- 相对路径确保当整个书籍目录被移动时，元数据仍能正确关联（只要目录结构不变）。

---

## 文件读取

### `class FileReader`
负责读取文本文件，为每个非空行建立字节偏移索引，支持快速随机访问。

**构造函数**：
```python
FileReader(file_path: str)
```
- **参数**：`file_path` – 文件的绝对或相对路径。
- **内部行为**：
  1. 打开文件，检测 UTF-8 BOM（`\xef\xbb\xbf`），若存在则使用 `utf-8-sig` 编码，否则用 `utf-8`。
  2. 逐行读取，跳过空行（`strip()` 为空的行），记录每行的起始字节偏移量到 `array('Q')` 中。
- **可能抛出**：`FileNotFoundError`, `OSError` 等。

**属性**：
- `total` (`int`) – 非空行总数（段落数）。只读。

**方法**：

#### `get_paragraph(idx: int) -> str`
- **描述**：返回指定索引段落的文本内容。
- **参数**：`idx` – 0-based 段落索引，必须在 `[0, total-1]` 范围内。
- **返回值**：去除行尾换行符（`\n` 或 `\r\n`）的字符串。
- **可能抛出**：`IndexError` 若索引越界。
- **性能**：O(1) 磁盘随机读取，适合大文件。

#### `_build_index() -> Tuple[array, str]`
内部方法（私有），不推荐外部调用。

---

## 服务层

### `class ReadingService`
管理当前阅读位置。

**构造函数**：
```python
ReadingService(reader: FileReader)
```
- **参数**：`reader` – 已初始化的 `FileReader` 实例。
- **初始状态**：`current_idx = 0`。

**属性**：
- `current` (`int`) – 当前段落索引（只读）。
- `total_paragraphs` (`int`) – 总段落数（只读）。

**方法**：

#### `go_to(idx: int) -> None`
- **描述**：跳转到指定段落，若 `idx` 在有效范围内则更新 `current_idx`，否则忽略。

#### `next() -> None`
- 如果 `current_idx < total - 1`，则 `current_idx += 1`。

#### `prev() -> None`
- 如果 `current_idx > 0`，则 `current_idx -= 1`。

#### `get_current_paragraph() -> str`
- **描述**：返回当前段落的文本。
- **等价于**：`self.reader.get_paragraph(self.current_idx)`。

---

### `class BookmarkService`
书签业务逻辑封装。

**构造函数**：
```python
BookmarkService(repo: IMetadataRepository, file_path: str)
```
- `repo` – 存储实现
- `file_path` – 当前书籍路径（用于所有仓库调用）

**方法**：

#### `get_all() -> List[Bookmark]`
返回该书籍的所有书签（直接委托仓库）。

#### `add(idx: int, label: str = "") -> Bookmark`
- **描述**：创建一个新书签（自动生成当前时间戳），存储并返回。
- **返回值**：新创建的 `Bookmark` 实例。

#### `delete(bookmark: Bookmark) -> None`
删除指定的书签对象。

#### `update_label(bookmark: Bookmark, new_label: str) -> None`
更新标签，仓库会自动更新时间戳。

#### `has_at(idx: int) -> bool`
- **描述**：检查指定段落是否至少有一个书签。
- **实现**：`any(b.idx == idx for b in self.get_all())`。

---

### `class NoteService`
笔记业务逻辑封装，API 类似 `BookmarkService`。

**构造函数**：
```python
NoteService(repo: IMetadataRepository, file_path: str)
```

**方法**：

#### `get_all(idx: int) -> List[Note]`
返回指定段落的所有笔记。

#### `add(idx: int, content: str) -> Note`
创建并存储笔记，返回新建的 `Note`。

#### `delete(idx: int, note: Note) -> None`
删除指定笔记（需要匹配完整内容及时间戳）。

#### `update(idx: int, old: Note, new_content: str) -> None`
更新笔记内容，自动更新时间戳。

#### `has_at(idx: int) -> bool`
检查指定段落是否有笔记（`len(self.get_all(idx)) > 0`）。

---

## 命令处理器

所有命令处理器都实现抽象基类 `ICommandHandler`。

### `class ICommandHandler` (抽象)
```python
class ICommandHandler(ABC):
    @abstractmethod
    def execute(self) -> None:
        pass
```
执行具体的业务逻辑，通常无返回值，副作用包括修改服务状态或更新视图。

### 具体处理器（列表）

| 类名 | 依赖 | 行为 |
|------|------|------|
| `UpHandler` | `ReadingService` | 调用 `reading.prev()` |
| `DownHandler` | `ReadingService` | 调用 `reading.next()` |
| `JumpHandler` | `ReadingService, Platform` | 清屏，提示用户输入段落号，调用 `go_to()` |
| `ShowBookmarkListHandler` | `BookmarkService, ReadingService, KeyBinding, Platform` | 进入书签列表交互循环，允许跳转、编辑、删除 |
| `AddBookmarkHandler` | `BookmarkService, ReadingService, Platform` | 提示输入标签，调用 `add()` |
| `AddNoteHandler` | `NoteService, ReadingService, Platform` | 提示输入内容，调用 `add()` |
| `ToggleNotesHandler` | `MainController` | 切换 `controller.show_notes` 布尔值 |
| `ManageNotesHandler` | `NoteService, ReadingService, KeyBinding, Platform` | 进入笔记管理交互循环，允许编辑、删除 |
| `ShowDetailsHandler` | `BookmarkService, NoteService, ReadingService, width` | 显示当前段落的详情（书签标签和笔记） |

每个处理器均将 `execute()` 作为入口，未提供其他公开方法。

---

## 视图层

### `class BookmarkListView`
负责渲染书签列表界面，处理用户交互。

**构造函数**：
```python
BookmarkListView(key_binding: KeyBinding, platform: Platform)
```

**方法**：

#### `render(bookmarks: List[Bookmark], selected: int) -> None`
- **描述**：清屏，绘制列表。高亮当前选中的条目。
- **参数**：
  - `bookmarks` – 书签列表（已排序）
  - `selected` – 当前选中索引（0-based）
- **副作用**：打印内容到 stdout。

#### `get_key() -> Optional[str]`
- **描述**：委托平台获取按键。
- **返回值**：按键字符串（如 `'UP'`, `'ENTER'`），若超时或无效可返回 `None`（当前实现会阻塞等待）。

#### `_title() -> str`
私有方法，生成标题栏文本（带颜色）。

---

### `class NoteManagementView`
类似 `BookmarkListView`，但针对笔记管理。

**构造函数**：
```python
NoteManagementView(key_binding: KeyBinding, platform: Platform)
```

**方法**：

#### `render(notes: List[Note], idx: int, selected: int) -> None`
- `idx` – 当前段落索引（仅用于标题显示）
- `selected` – 当前选中笔记索引

#### `get_key() -> Optional[str]`
同 `BookmarkListView`。

---

### `class DetailView`
静态视图，只显示信息。

**静态方法**：

#### `render(bookmark_svc: BookmarkService, note_svc: NoteService, idx: int, width: int) -> None`
- **描述**：清屏，打印当前段落的所有书签标签和笔记内容，然后等待用户按任意键返回（`platform.get_key()` 在内部调用）。
- **参数**：`idx` – 要显示的段落索引，`width` – 终端宽度（用于分隔线）。

---

## 控制器

### `class MainController`
主循环控制器，负责渲染阅读界面、处理按键分发、状态管理。

**构造函数**：
```python
MainController(reading_svc: ReadingService,
               bookmark_svc: BookmarkService,
               note_svc: NoteService,
               repo: IMetadataRepository,
               file_path: str,
               key_binding: KeyBinding,
               platform: Platform,
               width: int)
```
- 所有服务、仓库、路径、绑定、平台和终端宽度均通过构造函数注入。

**属性**：
- `show_notes` (`bool`) – 控制是否在阅读界面显示笔记。默认 `True`。

**方法**：

#### `run() -> None`
- **描述**：主循环，持续执行直到用户退出（`q` 或 `ESC`）。
- **行为**：
  1. 清屏
  2. 获取当前段落，加粗并自动换行输出
  3. 若 `show_notes` 为 `True`，获取当前段落的笔记并显示
  4. 打印状态栏（书签/笔记标记、进度、按键提示）
  5. 获取按键，解析为命令
  6. 若命令为 `QUIT` 或 `CANCEL`，自动添加当前段落为书签，保存最后位置，跳出循环
  7. 否则查找命令处理器并调用 `execute()`

#### `_build_hint() -> str`
- **描述**：构建底部提示栏的彩色字符串。
- **返回值**：包含所有顶级命令及其描述的文本（以空格分隔）。

---

## 工具类

### `class TerminalStyler`
纯静态类，提供 ANSI 转义序列样式。

**常量**（字符串）：
- `RESET = '\033[0m'`
- `BOLD = '\033[1m'`
- `YELLOW = '\033[33m'`
- `BLUE = '\033[34m'`
- `CYAN = '\033[36m'`
- `GREEN = '\033[32m'`
- `BG_YELLOW = '\033[43m'`

**静态方法**：
每个方法接收一个字符串并返回包裹了样式转义码的新字符串，样式结束后自动重置。

- `bold(text: str) -> str`
- `highlight(text: str) -> str` – 加粗 + 黄色
- `button(text: str) -> str` – 加粗 + 青色
- `selected(text: str) -> str` – 加粗 + 黄色背景
- `info(text: str) -> str` – 加粗 + 蓝色
- `note(text: str) -> str` – 加粗 + 绿色

---

### `class KeyBinding`
管理按键到命令的映射。

**构造函数**：
```python
KeyBinding()
```
初始化内部映射表。

**方法**：

#### `get_command(key: str) -> Optional[Command]`
- **参数**：`key` – 平台返回的按键字符串（如 `'UP'`, `'g'`, `'ESC'`）
- **返回值**：对应的 `Command` 枚举值，若无映射则返回 `None`

#### `get_display_key(cmd: Command) -> str`
- **描述**：返回适合显示给用户的按键符号（如 `'↑'`, `'g'`）。

#### `get_description(cmd: Command) -> str`
- **描述**：返回中文功能描述（如 `'上一段'`）。

#### `top_level_commands() -> List[Command]`
- **描述**：返回应在主界面底部提示栏显示的命令列表（不包括 `SELECT`, `DELETE`, `EDIT`, `CANCEL`）。

---

### `class ConsoleHelper`
静态辅助工具。

#### `clear() -> None`
跨平台清屏（`cls` / `clear`）。

#### `get_terminal_width() -> int`
- **描述**：尝试获取终端列数，若失败则返回 80。

#### `truncate(text: str, max_len: int = 50) -> str`
- **描述**：若 `text` 长度超过 `max_len`，则截断并添加 `'...'`，否则原样返回。

#### `wait_for_any_key(platform: Platform) -> None`
- **描述**：调用 `platform.get_key()` 等待任意按键，用于暂停。

---

### `class Platform` (抽象基类)
抽象平台输入。

#### `get_key() -> Optional[str]`
- **描述**：阻塞等待一个按键事件，并返回标准化后的字符串。
- **返回字符串映射**：
  - 方向键：`'UP'`, `'DOWN'`, `'LEFT'`, `'RIGHT'`
  - 回车：`'ENTER'`
  - ESC：`'ESC'`
  - 普通字符：原样（如 `'g'`, `'q'`）
- **注意**：`LEFT` 和 `RIGHT` 目前未使用，但被实现支持。

#### `input_line(prompt: str = "") -> str`
- **描述**：显示提示并读取一行输入（带回显）。

---

### `class WindowsPlatform(Platform)` 和 `class UnixPlatform(Platform)`
分别实现 Windows 和 Unix 系统的键盘读取。

- **`WindowsPlatform`**：使用 `msvcrt.kbhit()` 和 `msvcrt.getch()`，处理扩展键（`\xe0` 前缀）。
- **`UnixPlatform`**：使用 `tty` 和 `termios` 设置原始模式，读取 `sys.stdin.read(1)`，处理 ANSI 转义序列（`\x1b[...`）。

两者均实现 `get_key()` 和 `input_line()`。

---

### `class PlatformFactory`
工厂类，用于创建平台适配实例。

#### `create() -> Platform`
- **描述**：根据 `platform.system()` 返回 `WindowsPlatform()` 或 `UnixPlatform()`。

---

## 枚举

### `class Command(Enum)`
命令枚举，各成员含义：
- `UP`, `DOWN` – 上下滚动
- `JUMP` – 跳转
- `BOOKMARK_LIST` – 显示书签列表
- `ADD_BOOKMARK` – 添加书签
- `ADD_NOTE` – 添加笔记
- `TOGGLE_NOTES` – 切换笔记显示
- `MANAGE_NOTES` – 笔记管理
- `DETAILS` – 详情
- `QUIT` – 退出
- `SELECT` – 选择/确认
- `DELETE` – 删除
- `EDIT` – 编辑
- `CANCEL` – 取消

---

## 全局函数

### `main() -> None`
程序入口点。

**行为**：
1. 检查 `sys.argv`，若参数不足则显示用法并退出。
2. 取 `sys.argv[1]` 为书籍路径，转为绝对路径。
3. 实例化 `FileReader`，若总段落数为 0 则提示并退出。
4. 实例化 `JsonMetadataRepository(book_file_path)`。
5. 实例化 `ReadingService`。
6. 尝试从仓库恢复 `last_position`，若有效则设置 `reading_svc.current_idx`。
7. 实例化 `BookmarkService` 和 `NoteService`。
8. 实例化 `KeyBinding`，`PlatformFactory.create()`，获取终端宽度。
9. 实例化 `MainController` 并调用 `run()`。
10. 程序正常退出。

---

## 异常与错误处理
- 文件操作可能抛出 `OSError`、`FileNotFoundError`，但当前版本未做捕获，将传递给调用者。
- 在 `JumpHandler` 中，用户输入非数字时捕获 `ValueError` 和 `EOFError` 并忽略。
- 所有存储操作在写入时可能因权限问题失败（未特殊处理）。

---

## 扩展注意事项
- 若替换 `Platform` 实现，需确保 `get_key()` 返回的字符串与 `KeyBinding` 中的映射一致。
- 新增命令时，务必在 `top_level_commands()` 中注册，以便显示在提示栏。
- 修改 `JsonMetadataRepository` 的数据结构时，需考虑向后兼容性（可增加版本字段）。

---

*本文档覆盖了当前代码库中所有公开 API。如有遗漏，请参考源代码注释。*
