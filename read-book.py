#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
read-book - 极简命令行阅读器
"""

import sys
import os
import textwrap
import platform
import json
import ctypes
from datetime import datetime
from array import array
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple, Callable
from enum import Enum, auto

# ============================================================================
# 常量配置
# ============================================================================

TEXT = {
    "word_bookmark": "书签",
    "word_note": "笔记",
    "word_paragraph": "段落",
    "word_label": "标签",
    "word_none": "无",
    "word_hide": "隐藏",
    "word_show": "显示",
    "bookmark_list_title": "=== 书签列表 ({actions}) ===",
    "bookmark_list_format": "{prefix}段落 {idx}  -  {ts}{tags}",
    "bookmark_list_empty": "没有书签记录。",
    "bookmark_list_cancel": "按 {key} 取消",
    "note_management_title": "=== 笔记管理 - 段落 {idx} ({actions}) ===",
    "note_management_format": "{prefix} {ts} {content}",
    "note_management_empty": "当前段落没有笔记。",
    "note_management_return": "按 {key} 返回",
    "detail_title": ">> 段落 {idx} 详情",
    "detail_bookmark_section": "[{word_bookmark}] {word_label}:",
    "detail_note_section": "[{word_note}]:",
    "detail_none": "[{word_bookmark}] {word_none}",
    "detail_note_none": "[{word_note}] {word_none}",
    "detail_return": "按 {key} 返回",
    "main_notes_header": "[{word_note}] (按 {key} {word_hide})：",
    "main_status": "{marks} 第 {cur} / {total} 段    {hint}",
    "main_toggle_desc": "切换笔记({status})",
    "prompt_jump": "跳转到段落 (1-{total}): ",
    "prompt_add_note": "为段落 {idx} 添加笔记 (空行取消): ",
    "prompt_add_bookmark": "为段落 {idx} 添加书签标签 (空行取消): ",
    "prompt_edit_label": "输入新标签（空字符串清除）: ",
    "prompt_edit_content": "输入新内容: ",
    "message_note_added": "笔记已添加。",
    "message_bookmark_added": "书签已添加。",
    "message_press_any": "按任意键继续...",
    "message_current_label": "当前标签: {label}",
    "message_current_content": "当前内容: {content}",
    "action_separator": "  ",
    "bookmark_tag_format": " [{label}]",
    "separator_line": "-",
    "separator_thick": "=",
}

LAYOUT = {"left_margin": 0, "top_margin": 0, "max_width": 0, "center": False}
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# ============================================================================
# 终端样式
# ============================================================================

class Style:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    ITALIC = '\033[3m'
    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = (
        '\033[30m', '\033[31m', '\033[32m', '\033[33m',
        '\033[34m', '\033[35m', '\033[36m', '\033[37m'
    )
    BRIGHT_BLACK, BRIGHT_RED, BRIGHT_GREEN, BRIGHT_YELLOW = (
        '\033[90m', '\033[91m', '\033[92m', '\033[93m'
    )
    BRIGHT_BLUE, BRIGHT_MAGENTA, BRIGHT_CYAN, BRIGHT_WHITE = (
        '\033[94m', '\033[95m', '\033[96m', '\033[97m'
    )
    BG_YELLOW, BG_MAGENTA, BG_BRIGHT_YELLOW = '\033[43m', '\033[45m', '\033[103m'

    @classmethod
    def body(cls, text: str) -> str:
        return f"{cls.BOLD}{cls.BRIGHT_WHITE}{text}{cls.RESET}"
    @classmethod
    def key(cls, text: str) -> str:
        return f"{cls.BOLD}{cls.BRIGHT_GREEN}{text}{cls.RESET}"
    @classmethod
    def selected(cls, text: str) -> str:
        return f"{cls.BG_BRIGHT_YELLOW}{cls.BLACK}{cls.BOLD}{text}{cls.RESET}"
    @classmethod
    def title(cls, text: str) -> str:
        return f"{cls.BOLD}{cls.BRIGHT_MAGENTA}{text}{cls.RESET}"
    @classmethod
    def subtitle(cls, text: str) -> str:
        return f"{cls.BOLD}{cls.BRIGHT_CYAN}{text}{cls.RESET}"
    @classmethod
    def note(cls, text: str) -> str:
        return f"{cls.BRIGHT_GREEN}{text}{cls.RESET}"
    @classmethod
    def bookmark_label(cls, text: str) -> str:
        return f"{cls.BRIGHT_YELLOW}{text}{cls.RESET}"
    @classmethod
    def timestamp(cls, text: str) -> str:
        return f"{cls.ITALIC}{cls.WHITE}{text}{cls.RESET}"
    @classmethod
    def separator(cls, text: str) -> str:
        return f"{cls.WHITE}{text}{cls.RESET}"
    @classmethod
    def badge_bookmark(cls, text: str) -> str:
        return f"{cls.BG_YELLOW}{cls.BLACK}{cls.BOLD}{text}{cls.RESET}"
    @classmethod
    def badge_note(cls, text: str) -> str:
        return f"{cls.BG_MAGENTA}{cls.BLACK}{cls.BOLD}{text}{cls.RESET}"
    @classmethod
    def progress(cls, text: str) -> str:
        return f"{cls.BRIGHT_CYAN}{text}{cls.RESET}"
    @classmethod
    def success(cls, text: str) -> str:
        return f"{cls.BOLD}{cls.BRIGHT_GREEN}{text}{cls.RESET}"


# ============================================================================
# 工具函数
# ============================================================================

def format_timestamp(dt: datetime) -> str:
    return dt.strftime(TIME_FORMAT)

def truncate_text(text: str, max_len: int = 50) -> str:
    return text if len(text) <= max_len else text[:max_len] + '...'

def enable_ansi():
    if os.name == 'nt':
        try:
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            mode.value |= 0x0004
            kernel32.SetConsoleMode(handle, mode)
        except Exception:
            pass

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


# ============================================================================
# 平台抽象
# ============================================================================

class Platform(ABC):
    @abstractmethod
    def get_key(self) -> Optional[str]: pass
    @abstractmethod
    def input_line(self, prompt: str = "") -> str: pass

class WindowsPlatform(Platform):
    def get_key(self) -> Optional[str]:
        import msvcrt
        while True:
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch == b'\xe0':
                    ch2 = msvcrt.getch()
                    if ch2 == b'H': return 'UP'
                    if ch2 == b'P': return 'DOWN'
                    if ch2 == b'M': return 'RIGHT'
                    if ch2 == b'K': return 'LEFT'
                    return None
                if ch == b'\x1b': return 'ESC'
                try:
                    key = ch.decode('ascii')
                    if key == '\r': return 'ENTER'
                    return key
                except UnicodeDecodeError:
                    return None
        return None
    def input_line(self, prompt: str = "") -> str:
        return input(prompt)

class UnixPlatform(Platform):
    def get_key(self) -> Optional[str]:
        import tty, termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                ch2 = sys.stdin.read(1)
                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    if ch3 == 'A': return 'UP'
                    if ch3 == 'B': return 'DOWN'
                    if ch3 == 'C': return 'RIGHT'
                    if ch3 == 'D': return 'LEFT'
                return 'ESC'
            if ch == '\r': return 'ENTER'
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    def input_line(self, prompt: str = "") -> str:
        import tty, termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
            return input(prompt)
        finally:
            pass

def create_platform() -> Platform:
    return WindowsPlatform() if platform.system() == 'Windows' else UnixPlatform()


# ============================================================================
# 按键绑定
# ============================================================================

class Command(Enum):
    UP, DOWN, JUMP, BOOKMARK_LIST, ADD_BOOKMARK, ADD_NOTE, TOGGLE_NOTES, \
    MANAGE_NOTES, DETAILS, QUIT, SELECT, DELETE, EDIT, CANCEL = auto(), auto(), auto(), auto(), auto(), auto(), auto(), auto(), auto(), auto(), auto(), auto(), auto(), auto()

class KeyBinding:
    def __init__(self):
        self._map = {
            'UP': Command.UP, 'DOWN': Command.DOWN,
            'G': Command.JUMP, 'g': Command.JUMP,
            'B': Command.BOOKMARK_LIST, 'b': Command.BOOKMARK_LIST,
            'n': Command.ADD_NOTE,
            'N': Command.TOGGLE_NOTES,
            'M': Command.ADD_BOOKMARK, 'm': Command.ADD_BOOKMARK,
            'L': Command.MANAGE_NOTES, 'l': Command.MANAGE_NOTES,
            'I': Command.DETAILS, 'i': Command.DETAILS,
            'Q': Command.QUIT, 'q': Command.QUIT,
            'ESC': Command.CANCEL,
            'ENTER': Command.SELECT,
            'D': Command.DELETE, 'd': Command.DELETE,
            'E': Command.EDIT, 'e': Command.EDIT,
        }
        self._display = {
            Command.UP: ('↑', '上一段'), Command.DOWN: ('↓', '下一段'),
            Command.JUMP: ('g', '跳转'), Command.BOOKMARK_LIST: ('b', '书签列表'),
            Command.ADD_BOOKMARK: ('m', '添加书签'), Command.ADD_NOTE: ('n', '添加笔记'),
            Command.TOGGLE_NOTES: ('N', '切换笔记'), Command.MANAGE_NOTES: ('l', '笔记管理'),
            Command.DETAILS: ('i', '详情'), Command.QUIT: ('q', '退出'),
            Command.SELECT: ('Enter', '选择'), Command.DELETE: ('d', '删除'),
            Command.EDIT: ('e', '编辑'), Command.CANCEL: ('ESC', '取消'),
        }

    def get_command(self, key: str) -> Optional[Command]:
        return self._map.get(key)

    def get_display(self, cmd: Command) -> Tuple[str, str]:
        return self._display.get(cmd, ('?', '?'))

    def top_level(self) -> List[Command]:
        return [Command.UP, Command.DOWN, Command.JUMP,
                Command.BOOKMARK_LIST, Command.ADD_BOOKMARK,
                Command.ADD_NOTE, Command.TOGGLE_NOTES,
                Command.MANAGE_NOTES, Command.DETAILS, Command.QUIT]


# ============================================================================
# 领域模型
# ============================================================================

class Bookmark:
    def __init__(self, idx: int, timestamp: str, label: str = ""):
        self.idx, self.timestamp, self.label = idx, timestamp, label
    def to_dict(self) -> Dict:
        return {'idx': self.idx, 'timestamp': self.timestamp, 'label': self.label}
    @classmethod
    def from_dict(cls, data: Dict) -> 'Bookmark':
        return cls(data['idx'], data['timestamp'], data.get('label', ''))

class Note:
    def __init__(self, timestamp: str, content: str):
        self.timestamp, self.content = timestamp, content
    def to_dict(self) -> Dict:
        return {'timestamp': self.timestamp, 'content': self.content}
    @classmethod
    def from_dict(cls, data: Dict) -> 'Note':
        return cls(data['timestamp'], data['content'])


# ============================================================================
# 存储层
# ============================================================================

class IMetadataRepository(ABC):
    @abstractmethod
    def get_bookmarks(self) -> List[Bookmark]: pass
    @abstractmethod
    def add_bookmark(self, bookmark: Bookmark): pass
    @abstractmethod
    def delete_bookmark(self, bookmark: Bookmark) -> bool: pass
    @abstractmethod
    def update_bookmark(self, old: Bookmark, new_label: str): pass
    @abstractmethod
    def get_notes(self, idx: int) -> List[Note]: pass
    @abstractmethod
    def add_note(self, idx: int, note: Note): pass
    @abstractmethod
    def delete_note(self, idx: int, note: Note) -> bool: pass
    @abstractmethod
    def update_note(self, idx: int, old: Note, new_content: str): pass
    @abstractmethod
    def get_last_position(self) -> Optional[int]: pass
    @abstractmethod
    def set_last_position(self, position: int): pass

class JsonMetadataRepository(IMetadataRepository):
    def __init__(self, book_file_path: str):
        self.book_file_path = os.path.abspath(book_file_path)
        self.base_dir = os.path.dirname(self.book_file_path)
        self.meta_file = os.path.join(self.base_dir, '.meta.json')
        self.rel_path = os.path.relpath(self.book_file_path, self.base_dir).replace('\\', '/')
        self._data = {}
        self._load()
        if self.rel_path not in self._data:
            self._data[self.rel_path] = {'bookmarks': [], 'notes': {}, 'last_position': 0}
            self._save()
    def _load(self):
        if os.path.exists(self.meta_file):
            with open(self.meta_file, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
    def _save(self):
        with open(self.meta_file, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
    def _entry(self) -> Dict:
        return self._data[self.rel_path]
    def get_bookmarks(self) -> List[Bookmark]:
        return [Bookmark.from_dict(b) for b in self._entry().get('bookmarks', [])]
    def add_bookmark(self, bookmark: Bookmark):
        self._entry()['bookmarks'].append(bookmark.to_dict())
        self._save()
    def delete_bookmark(self, bookmark: Bookmark) -> bool:
        entry = self._entry()
        original_len = len(entry['bookmarks'])
        entry['bookmarks'] = [b for b in entry['bookmarks']
                              if not (b['idx'] == bookmark.idx and b['timestamp'] == bookmark.timestamp)]
        if len(entry['bookmarks']) == original_len:
            return False
        self._save()
        return True
    def update_bookmark(self, old: Bookmark, new_label: str):
        for b in self._entry()['bookmarks']:
            if b['idx'] == old.idx and b['timestamp'] == old.timestamp:
                b['label'] = new_label
                b['timestamp'] = datetime.now().isoformat()
                self._save()
                return
    def get_notes(self, idx: int) -> List[Note]:
        notes_data = self._entry().get('notes', {}).get(str(idx), [])
        return [Note.from_dict(n) for n in notes_data]
    def add_note(self, idx: int, note: Note):
        entry = self._entry()
        notes = entry['notes'].setdefault(str(idx), [])
        notes.append(note.to_dict())
        self._save()
    def delete_note(self, idx: int, note: Note) -> bool:
        entry = self._entry()
        notes = entry['notes'].get(str(idx), [])
        original_len = len(notes)
        def match(n):
            n_time = n['timestamp'].split('.')[0]
            note_time = note.timestamp.split('.')[0]
            return n_time == note_time and n['content'] == note.content
        entry['notes'][str(idx)] = [n for n in notes if not match(n)]
        if len(entry['notes'][str(idx)]) == original_len:
            return False
        if not entry['notes'][str(idx)]:
            del entry['notes'][str(idx)]
        self._save()
        return True
    def update_note(self, idx: int, old: Note, new_content: str):
        for n in self._entry()['notes'].get(str(idx), []):
            n_time = n['timestamp'].split('.')[0]
            old_time = old.timestamp.split('.')[0]
            if n_time == old_time and n['content'] == old.content:
                n['content'] = new_content
                n['timestamp'] = datetime.now().isoformat()
                self._save()
                return
    def get_last_position(self) -> Optional[int]:
        return self._entry().get('last_position', 0)
    def set_last_position(self, position: int):
        self._entry()['last_position'] = position
        self._save()


# ============================================================================
# 文件读取
# ============================================================================

class FileReader:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.offsets, self.encoding = self._build_index()
    def _build_index(self):
        offsets = array('Q')
        encoding = 'utf-8'
        with open(self.file_path, 'rb') as f:
            bom = f.read(3)
            if bom == b'\xef\xbb\xbf':
                encoding = 'utf-8-sig'
            else:
                f.seek(0)
            while True:
                pos = f.tell()
                line = f.readline()
                if not line:
                    break
                if line.strip():
                    offsets.append(pos)
        return offsets, encoding
    def get_paragraph(self, idx: int) -> str:
        with open(self.file_path, 'rb') as f:
            f.seek(self.offsets[idx])
            return f.readline().decode(self.encoding).rstrip('\n\r')
    @property
    def total(self) -> int:
        return len(self.offsets)


# ============================================================================
# 服务层
# ============================================================================

class ReadingService:
    def __init__(self, reader: FileReader):
        self.reader = reader
        self.current_idx = 0
    def go_to(self, idx: int):
        if 0 <= idx < self.reader.total:
            self.current_idx = idx
    def next(self):
        if self.current_idx < self.reader.total - 1:
            self.current_idx += 1
    def prev(self):
        if self.current_idx > 0:
            self.current_idx -= 1
    def get_current(self) -> str:
        return self.reader.get_paragraph(self.current_idx)
    @property
    def total(self) -> int:
        return self.reader.total
    @property
    def current(self) -> int:
        return self.current_idx

class BookmarkService:
    def __init__(self, repo: IMetadataRepository):
        self.repo = repo
    def get_all(self) -> List[Bookmark]:
        return self.repo.get_bookmarks()
    def add(self, idx: int, label: str = "") -> Bookmark:
        bm = Bookmark(idx, datetime.now().isoformat(), label)
        self.repo.add_bookmark(bm)
        return bm
    def delete(self, bookmark: Bookmark) -> bool:
        return self.repo.delete_bookmark(bookmark)
    def update_label(self, bookmark: Bookmark, new_label: str):
        self.repo.update_bookmark(bookmark, new_label)
    def has_at(self, idx: int) -> bool:
        return any(b.idx == idx for b in self.get_all())

class NoteService:
    def __init__(self, repo: IMetadataRepository):
        self.repo = repo
    def get_all(self, idx: int) -> List[Note]:
        return self.repo.get_notes(idx)
    def add(self, idx: int, content: str) -> Note:
        note = Note(datetime.now().isoformat(), content)
        self.repo.add_note(idx, note)
        return note
    def delete(self, idx: int, note: Note) -> bool:
        return self.repo.delete_note(idx, note)
    def update(self, idx: int, old: Note, new_content: str):
        self.repo.update_note(idx, old, new_content)
    def has_at(self, idx: int) -> bool:
        return len(self.get_all(idx)) > 0


# ============================================================================
# 渲染器
# ============================================================================

class Renderer:
    def __init__(self, kb: KeyBinding, terminal_width: int):
        self.kb = kb
        self.term_width = terminal_width

    def _sep_len(self) -> int:
        return min(self.term_width, 80)

    def _wrap(self, text: str) -> str:
        if LAYOUT['max_width'] <= 0:
            return text
        wrap_width = min(LAYOUT['max_width'], self.term_width)
        return textwrap.fill(text, width=wrap_width, break_long_words=False) if wrap_width > 0 else text

    def _apply_layout(self, text: str) -> str:
        indent = ' ' * LAYOUT['left_margin']
        return '\n'.join(indent + line for line in text.split('\n'))

    def _format_actions(self, cmds: List[Command]) -> str:
        return TEXT['action_separator'].join(f"{Style.key(sym)} {desc}" for sym, desc in (self.kb.get_display(c) for c in cmds))

    def render_list(self, items: List, selected: int, title: str, empty_msg: str,
                    format_func: Callable[[Any, int, bool], str]) -> str:
        lines = [Style.title(title), ""]
        if not items:
            lines.append(empty_msg)
            cancel_key = self.kb.get_display(Command.CANCEL)[0]
            lines.append(TEXT['bookmark_list_cancel'].format(key=Style.key(cancel_key)))
            return self._apply_layout('\n'.join(lines))
        for i, item in enumerate(items):
            lines.append(format_func(item, i, i == selected))
        lines.append("")
        lines.append(Style.separator(TEXT['separator_line'] * self._sep_len()))
        return self._apply_layout('\n'.join(lines))

    def render_bookmarks(self, items: List[Bookmark], selected: int) -> str:
        actions = self._format_actions([Command.UP, Command.DOWN, Command.SELECT,
                                        Command.EDIT, Command.DELETE, Command.CANCEL])
        title = TEXT['bookmark_list_title'].format(actions=actions)
        def fmt(item, i, sel):
            prefix = Style.selected("→") if sel else "  "
            dt = datetime.fromisoformat(item.timestamp)
            ts = format_timestamp(dt)
            tags = TEXT['bookmark_tag_format'].format(label=Style.bookmark_label(item.label)) if item.label else ""
            return TEXT['bookmark_list_format'].format(
                prefix=prefix, idx=Style.progress(str(item.idx+1)), ts=Style.timestamp(ts), tags=tags)
        return self.render_list(items, selected, title, TEXT['bookmark_list_empty'], fmt)

    def render_notes(self, items: List[Note], idx: int, selected: int) -> str:
        actions = self._format_actions([Command.UP, Command.DOWN, Command.EDIT,
                                        Command.DELETE, Command.CANCEL])
        title = TEXT['note_management_title'].format(idx=idx+1, actions=actions)
        def fmt(item, i, sel):
            prefix = Style.selected("→") if sel else "  "
            dt = datetime.fromisoformat(item.timestamp)
            ts = format_timestamp(dt)
            return TEXT['note_management_format'].format(
                prefix=prefix, ts=Style.timestamp(ts), content=Style.note(item.content))
        return self.render_list(items, selected, title, TEXT['note_management_empty'], fmt)

    def render_detail(self, bookmarks: List[Bookmark], notes: List[Note], idx: int) -> str:
        lines = []
        sep = Style.separator(TEXT['separator_thick'] * self._sep_len())
        lines.append(sep)
        lines.append(Style.subtitle(TEXT['detail_title'].format(idx=idx+1)))
        lines.append(sep)
        labels = [b.label for b in bookmarks if b.idx == idx]
        if labels:
            lines.append("")
            lines.append(TEXT['detail_bookmark_section'].format(word_bookmark=TEXT['word_bookmark'], word_label=TEXT['word_label']))
            lines.extend(f"  {Style.bookmark_label(lab)}" for lab in labels)
        else:
            lines.append("")
            lines.append(TEXT['detail_none'].format(word_bookmark=TEXT['word_bookmark'], word_none=TEXT['word_none']))
        if notes:
            lines.append("")
            lines.append(TEXT['detail_note_section'].format(word_note=TEXT['word_note']))
            for note in notes:
                dt = datetime.fromisoformat(note.timestamp)
                ts = format_timestamp(dt)
                lines.append(f"  {Style.timestamp(ts)} {Style.note(note.content)}")
        else:
            lines.append("")
            lines.append(TEXT['detail_note_none'].format(word_note=TEXT['word_note'], word_none=TEXT['word_none']))
        lines.append("")
        lines.append(sep)
        cancel_key = self.kb.get_display(Command.CANCEL)[0]
        lines.append(TEXT['detail_return'].format(key=Style.key(cancel_key)))
        return self._apply_layout('\n'.join(lines))

    def render_main(self, paragraph: str, notes: List[Note], cur: int, total: int,
                    show_notes: bool, has_bookmark: bool, has_note: bool, hint: str) -> str:
        wrapped = self._wrap(paragraph)
        lines = [Style.body(line) for line in wrapped.split('\n')]
        if show_notes and notes:
            lines.append("")
            sep = Style.separator(TEXT['separator_thick'] * self._sep_len())
            lines.append(sep)
            toggle_key = self.kb.get_display(Command.TOGGLE_NOTES)[0]
            header = TEXT['main_notes_header'].format(
                word_note=TEXT['word_note'], key=Style.key(toggle_key), word_hide=TEXT['word_hide'])
            lines.append(header)
            for note in notes:
                dt = datetime.fromisoformat(note.timestamp)
                ts = format_timestamp(dt)
                truncated = truncate_text(note.content)
                lines.append(f"  {Style.timestamp(ts)} {Style.note(truncated)}")
            lines.append(sep)
        lines.append("")
        sep_line = Style.separator(TEXT['separator_line'] * self._sep_len())
        lines.append(sep_line)
        marks = ""
        if has_bookmark:
            marks += Style.badge_bookmark(TEXT['word_bookmark'])
        if has_note:
            marks += Style.badge_note(TEXT['word_note'])
        status = TEXT['main_status'].format(
            marks=marks,
            cur=cur+1,
            total=total,
            hint=hint
        )
        lines.append(status)
        return self._apply_layout('\n'.join(lines))


# ============================================================================
# 通用列表控制器
# ============================================================================

class ListController:
    def __init__(self, items: List, kb: KeyBinding, platform: Platform,
                 render_func: Callable[[List, int], str],
                 on_select: Callable[[int], None],
                 on_delete: Callable[[int], bool],
                 on_edit: Callable[[int], None]):
        self.items = items
        self.kb = kb
        self.platform = platform
        self.render_func = render_func
        self.on_select = on_select
        self.on_delete = on_delete
        self.on_edit = on_edit
        self.selected = 0

    def run(self) -> bool:
        while True:
            clear_screen()
            print(self.render_func(self.items, self.selected))
            key = self.platform.get_key()
            cmd = self.kb.get_command(key)

            if cmd == Command.UP and self.selected > 0:
                self.selected -= 1
            elif cmd == Command.DOWN and self.selected < len(self.items) - 1:
                self.selected += 1
            elif cmd == Command.CANCEL:
                return False
            elif cmd == Command.SELECT:
                self.on_select(self.selected)
                return True
            elif cmd == Command.DELETE:
                if self.on_delete(self.selected):
                    self.items.pop(self.selected)
                    if not self.items:
                        return False
                    if self.selected >= len(self.items):
                        self.selected = len(self.items) - 1
            elif cmd == Command.EDIT:
                self.on_edit(self.selected)
                return False


# ============================================================================
# 命令处理器
# ============================================================================

class ICommandHandler(ABC):
    @abstractmethod
    def execute(self) -> None:
        pass

class UpHandler(ICommandHandler):
    def __init__(self, reading: ReadingService):
        self.reading = reading
    def execute(self):
        self.reading.prev()

class DownHandler(ICommandHandler):
    def __init__(self, reading: ReadingService):
        self.reading = reading
    def execute(self):
        self.reading.next()

class JumpHandler(ICommandHandler):
    def __init__(self, reading: ReadingService, platform: Platform):
        self.reading, self.platform = reading, platform
    def execute(self):
        clear_screen()
        try:
            num = int(self.platform.input_line(TEXT['prompt_jump'].format(total=self.reading.total)))
            if 1 <= num <= self.reading.total:
                self.reading.go_to(num - 1)
        except (ValueError, EOFError):
            pass

class AddHandler(ICommandHandler):
    def __init__(self, add_func, idx_getter, prompt_template, success_msg, platform):
        self.add_func = add_func
        self.idx_getter = idx_getter
        self.prompt = prompt_template
        self.msg = success_msg
        self.platform = platform
    def execute(self):
        clear_screen()
        idx = self.idx_getter()
        content = self.platform.input_line(self.prompt.format(idx=idx+1)).strip()
        if content:
            self.add_func(idx, content)
            print(Style.success(self.msg))
            print(TEXT['message_press_any'])
            self.platform.get_key()

class ShowListHandler(ICommandHandler):
    """通用列表展示（书签列表 / 笔记管理）"""
    def __init__(self, get_items_func: Callable[[], List],
                 render_func: Callable[[List, int], str],
                 on_select: Callable[[Any], None],
                 on_delete: Callable[[Any], bool],
                 on_edit: Callable[[Any], None],
                 sort_key: Optional[Callable] = None,
                 kb: KeyBinding = None, platform: Platform = None):
        self.get_items = get_items_func
        self.render_func = render_func
        self.on_select = on_select
        self.on_delete = on_delete
        self.on_edit = on_edit
        self.sort_key = sort_key
        self.kb = kb
        self.platform = platform

    def execute(self):
        items = self.get_items()
        if self.sort_key:
            items.sort(key=self.sort_key)
        if not items:
            clear_screen()
            print(self.render_func(items, 0))
            self.platform.get_key()
            return

        def select_cb(idx):
            self.on_select(items[idx])
        def delete_cb(idx):
            return self.on_delete(items[idx])
        def edit_cb(idx):
            self.on_edit(items[idx])

        ctrl = ListController(items, self.kb, self.platform, self.render_func,
                              select_cb, delete_cb, edit_cb)
        ctrl.run()

class ToggleNotesHandler(ICommandHandler):
    def __init__(self, controller):
        self.controller = controller
    def execute(self):
        self.controller.show_notes = not self.controller.show_notes

class ShowDetailsHandler(ICommandHandler):
    def __init__(self, bookmark_svc, note_svc, reading, renderer, platform):
        self.bookmarks = bookmark_svc
        self.notes = note_svc
        self.reading = reading
        self.renderer = renderer
        self.platform = platform
    def execute(self):
        idx = self.reading.current
        clear_screen()
        print(self.renderer.render_detail(self.bookmarks.get_all(), self.notes.get_all(idx), idx))
        self.platform.get_key()


# ============================================================================
# 主控制器
# ============================================================================

class MainController:
    def __init__(self, reading, bookmark_svc, note_svc, repo, file_path, kb, platform, term_width):
        self.reading = reading
        self.bookmarks = bookmark_svc
        self.notes = note_svc
        self.repo = repo
        self.file_path = file_path
        self.kb = kb
        self.platform = platform
        self.term_width = term_width
        self.show_notes = True
        self.renderer = Renderer(kb, term_width)

        self.handlers = {
            Command.UP: UpHandler(reading),
            Command.DOWN: DownHandler(reading),
            Command.JUMP: JumpHandler(reading, platform),
            Command.ADD_NOTE: AddHandler(note_svc.add, lambda: reading.current, TEXT['prompt_add_note'], TEXT['message_note_added'], platform),
            Command.ADD_BOOKMARK: AddHandler(bookmark_svc.add, lambda: reading.current, TEXT['prompt_add_bookmark'], TEXT['message_bookmark_added'], platform),
            Command.TOGGLE_NOTES: ToggleNotesHandler(self),
            Command.DETAILS: ShowDetailsHandler(bookmark_svc, note_svc, reading, self.renderer, platform),
            Command.BOOKMARK_LIST: ShowListHandler(
                get_items_func=bookmark_svc.get_all,
                sort_key=lambda b: b.timestamp,
                render_func=self.renderer.render_bookmarks,
                on_select=lambda bm: reading.go_to(bm.idx),
                on_delete=lambda bm: bookmark_svc.delete(bm),
                on_edit=self._edit_bookmark_label,
                kb=kb, platform=platform
            ),
            Command.MANAGE_NOTES: ShowListHandler(
                get_items_func=lambda: note_svc.get_all(reading.current),
                sort_key=None,
                render_func=lambda items, sel: self.renderer.render_notes(items, reading.current, sel),
                on_select=lambda _: None,
                on_delete=lambda note: note_svc.delete(reading.current, note),
                on_edit=self._edit_note,
                kb=kb, platform=platform
            ),
        }

    def _edit_bookmark_label(self, bm):
        clear_screen()
        print(TEXT['message_current_label'].format(label=bm.label))
        new_label = self.platform.input_line(TEXT['prompt_edit_label']).strip()
        self.bookmarks.update_label(bm, new_label)

    def _edit_note(self, note):
        idx = self.reading.current
        clear_screen()
        print(TEXT['message_current_content'].format(content=note.content))
        new_content = self.platform.input_line(TEXT['prompt_edit_content']).strip()
        if new_content:
            self.notes.update(idx, note, new_content)

    def _build_hint(self) -> str:
        parts = []
        status = TEXT['word_show'] if self.show_notes else TEXT['word_hide']
        for cmd in self.kb.top_level():
            sym, desc = self.kb.get_display(cmd)
            if cmd == Command.TOGGLE_NOTES:
                desc = TEXT['main_toggle_desc'].format(status=status)
            parts.append(f"{Style.key(sym)} {desc}")
        return '  '.join(parts)

    def run(self):
        total = self.reading.total
        while True:
            clear_screen()
            paragraph = self.reading.get_current()
            notes = self.notes.get_all(self.reading.current)
            has_bookmark = self.bookmarks.has_at(self.reading.current)
            has_note = self.notes.has_at(self.reading.current)
            hint = self._build_hint()

            frame = self.renderer.render_main(
                paragraph=paragraph,
                notes=notes,
                cur=self.reading.current,
                total=total,
                show_notes=self.show_notes,
                has_bookmark=has_bookmark,
                has_note=has_note,
                hint=hint
            )
            print(frame)

            key = self.platform.get_key()
            cmd = self.kb.get_command(key)
            if cmd == Command.QUIT or cmd == Command.CANCEL:
                self.bookmarks.add(self.reading.current)
                self.repo.set_last_position(self.reading.current)
                break
            elif cmd in self.handlers:
                self.handlers[cmd].execute()


# ============================================================================
# 入口
# ============================================================================

def main():
    enable_ansi()
    if len(sys.argv) < 2:
        print('用法: python read-book.py <文本文件>')
        sys.exit(1)

    file_path = os.path.abspath(sys.argv[1])
    reader = FileReader(file_path)
    if reader.total == 0:
        print("文件中没有非空行。")
        sys.exit(0)

    repo = JsonMetadataRepository(file_path)
    reading = ReadingService(reader)
    last_pos = repo.get_last_position()
    if last_pos is not None and 0 <= last_pos < reader.total:
        reading.current_idx = last_pos

    bookmark_svc = BookmarkService(repo)
    note_svc = NoteService(repo)

    kb = KeyBinding()
    platform = create_platform()
    term_width = 80
    try:
        term_width = os.get_terminal_size().columns
    except OSError:
        pass

    controller = MainController(reading, bookmark_svc, note_svc, repo, file_path,
                                kb, platform, term_width)
    controller.run()

if __name__ == '__main__':
    main()
