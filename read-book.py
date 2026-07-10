#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
read-book - 命令行阅读器（命令处理器模式）
支持超大文本、书签（含标签）、笔记（完整CRUD）、自动进度记录。
所有显示均为纯文本，兼容所有终端。
"""

import sys
import os
import textwrap
import platform
import json
from datetime import datetime
from array import array
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum, auto


# ============================================================================
# 工具层 - 平台抽象
# ============================================================================

class IPlatform(ABC):
    @abstractmethod
    def get_key(self) -> Optional[str]:
        pass

    @abstractmethod
    def input_line(self, prompt: str = "") -> str:
        pass

class WindowsPlatform(IPlatform):
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

    def input_line(self, prompt: str = "") -> str:
        return input(prompt)

class UnixPlatform(IPlatform):
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
            else:
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

class PlatformFactory:
    @staticmethod
    def create() -> IPlatform:
        return WindowsPlatform() if platform.system() == 'Windows' else UnixPlatform()


# ============================================================================
# 工具层 - 命令与配置
# ============================================================================

class Command(Enum):
    UP = auto()
    DOWN = auto()
    JUMP = auto()
    BOOKMARK_LIST = auto()
    ADD_BOOKMARK = auto()
    ADD_NOTE = auto()
    TOGGLE_NOTES = auto()
    MANAGE_NOTES = auto()
    DETAILS = auto()
    QUIT = auto()
    SELECT = auto()
    DELETE = auto()
    EDIT = auto()
    CANCEL = auto()

class KeyBinding:
    def __init__(self):
        self._key_map = {
            'UP': Command.UP,
            'DOWN': Command.DOWN,
            'G': Command.JUMP,
            'g': Command.JUMP,
            'B': Command.BOOKMARK_LIST,
            'b': Command.BOOKMARK_LIST,
            'n': Command.ADD_NOTE,
            'N': Command.TOGGLE_NOTES,
            'M': Command.ADD_BOOKMARK,
            'm': Command.ADD_BOOKMARK,
            'L': Command.MANAGE_NOTES,
            'l': Command.MANAGE_NOTES,
            'I': Command.DETAILS,
            'i': Command.DETAILS,
            'Q': Command.QUIT,
            'q': Command.QUIT,
            'ESC': Command.CANCEL,
            'ENTER': Command.SELECT,
            'D': Command.DELETE,
            'd': Command.DELETE,
            'E': Command.EDIT,
            'e': Command.EDIT,
        }
        self._display_map = {
            Command.UP: ('↑', '上一段'),
            Command.DOWN: ('↓', '下一段'),
            Command.JUMP: ('g', '跳转'),
            Command.BOOKMARK_LIST: ('b', '书签列表'),
            Command.ADD_BOOKMARK: ('m', '添加书签'),
            Command.ADD_NOTE: ('n', '添加笔记'),
            Command.TOGGLE_NOTES: ('N', '切换笔记'),
            Command.MANAGE_NOTES: ('l', '笔记管理'),
            Command.DETAILS: ('i', '详情'),
            Command.QUIT: ('q', '退出'),
            Command.SELECT: ('Enter', '选择'),
            Command.DELETE: ('d', '删除'),
            Command.EDIT: ('e', '编辑'),
            Command.CANCEL: ('ESC', '取消'),
        }

    def get_command(self, key: str) -> Optional[Command]:
        return self._key_map.get(key)

    def get_display_key(self, cmd: Command) -> str:
        return self._display_map.get(cmd, ('?', '?'))[0]

    def get_description(self, cmd: Command) -> str:
        return self._display_map.get(cmd, ('?', '?'))[1]

    def bookmark_list_title(self) -> str:
        items = [
            f"{self.get_display_key(Command.UP)}/{self.get_display_key(Command.DOWN)} 选择",
            f"{self.get_display_key(Command.SELECT)} 跳转",
            f"{self.get_display_key(Command.EDIT)} 编辑标签",
            f"{self.get_display_key(Command.DELETE)} 删除",
            f"{self.get_display_key(Command.CANCEL)} 取消"
        ]
        return f"=== 书签列表 ({'  '.join(items)}) ==="

    def note_management_title(self, idx: int) -> str:
        items = [
            f"{self.get_display_key(Command.UP)}/{self.get_display_key(Command.DOWN)} 选择",
            f"{self.get_display_key(Command.EDIT)} 编辑",
            f"{self.get_display_key(Command.DELETE)} 删除",
            f"{self.get_display_key(Command.CANCEL)} 返回"
        ]
        return f"=== 笔记管理 - 段落 {idx+1} ({'  '.join(items)}) ==="

    def notes_display_header(self) -> str:
        return f"[笔记] (按 {self.get_display_key(Command.TOGGLE_NOTES)} 隐藏)："

    TOP_LEVEL_COMMANDS = [
        Command.UP, Command.DOWN, Command.JUMP,
        Command.BOOKMARK_LIST, Command.ADD_BOOKMARK,
        Command.ADD_NOTE, Command.TOGGLE_NOTES,
        Command.MANAGE_NOTES, Command.DETAILS,
        Command.QUIT,
    ]

class ConsoleHelper:
    @staticmethod
    def clear():
        os.system('cls' if os.name == 'nt' else 'clear')

    @staticmethod
    def get_terminal_width() -> int:
        try:
            return os.get_terminal_size().columns
        except OSError:
            return 80

    @staticmethod
    def truncate(text: str, max_len: int = 50) -> str:
        return text if len(text) <= max_len else text[:max_len] + '...'

    @staticmethod
    def wait_for_any_key(platform: IPlatform):
        platform.get_key()


# ============================================================================
# 核心层
# ============================================================================

class Bookmark:
    def __init__(self, idx: int, timestamp: str, label: str = ""):
        self.idx = idx
        self.timestamp = timestamp
        self.label = label
    def to_dict(self) -> Dict:
        return {'idx': self.idx, 'timestamp': self.timestamp, 'label': self.label}
    @classmethod
    def from_dict(cls, data: Dict) -> 'Bookmark':
        return cls(data['idx'], data['timestamp'], data.get('label', ''))

class Note:
    def __init__(self, timestamp: str, content: str):
        self.timestamp = timestamp
        self.content = content
    def to_dict(self) -> Dict:
        return {'timestamp': self.timestamp, 'content': self.content}
    @classmethod
    def from_dict(cls, data: Dict) -> 'Note':
        return cls(data['timestamp'], data['content'])

class IMetadataRepository(ABC):
    @abstractmethod
    def get_bookmarks(self, file_path: str) -> List[Bookmark]: pass
    @abstractmethod
    def add_bookmark(self, file_path: str, bookmark: Bookmark): pass
    @abstractmethod
    def delete_bookmark(self, file_path: str, bookmark: Bookmark): pass
    @abstractmethod
    def update_bookmark(self, file_path: str, old: Bookmark, new_label: str): pass
    @abstractmethod
    def get_notes(self, file_path: str, idx: int) -> List[Note]: pass
    @abstractmethod
    def add_note(self, file_path: str, idx: int, note: Note): pass
    @abstractmethod
    def delete_note(self, file_path: str, idx: int, note: Note): pass
    @abstractmethod
    def update_note(self, file_path: str, idx: int, old: Note, new_content: str): pass


# ============================================================================
# 实现层
# ============================================================================

class JsonMetadataRepository(IMetadataRepository):
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_file = os.path.join(data_dir, '.read-book-data.json')
        self._data = {}
        self._load()

    def _load(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
        else:
            self._data = {}

    def _save(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def _get_file_meta(self, file_path: str) -> Dict:
        if file_path not in self._data:
            self._data[file_path] = {'bookmarks': [], 'notes': {}}
        return self._data[file_path]

    def get_bookmarks(self, file_path: str) -> List[Bookmark]:
        meta = self._data.get(file_path, {})
        return [Bookmark.from_dict(bm) for bm in meta.get('bookmarks', [])]

    def add_bookmark(self, file_path: str, bookmark: Bookmark):
        meta = self._get_file_meta(file_path)
        meta['bookmarks'].append(bookmark.to_dict())
        self._save()

    def delete_bookmark(self, file_path: str, bookmark: Bookmark):
        meta = self._get_file_meta(file_path)
        meta['bookmarks'] = [bm for bm in meta['bookmarks']
                             if not (bm['idx'] == bookmark.idx and
                                     bm['timestamp'] == bookmark.timestamp)]
        self._save()

    def update_bookmark(self, file_path: str, old: Bookmark, new_label: str):
        meta = self._get_file_meta(file_path)
        for bm in meta['bookmarks']:
            if bm['idx'] == old.idx and bm['timestamp'] == old.timestamp:
                bm['label'] = new_label
                bm['timestamp'] = datetime.now().isoformat()
                self._save()
                return

    def get_notes(self, file_path: str, idx: int) -> List[Note]:
        meta = self._data.get(file_path, {})
        notes_data = meta.get('notes', {}).get(str(idx), [])
        return [Note.from_dict(n) for n in notes_data]

    def add_note(self, file_path: str, idx: int, note: Note):
        meta = self._get_file_meta(file_path)
        notes = meta['notes'].setdefault(str(idx), [])
        notes.append(note.to_dict())
        self._save()

    def delete_note(self, file_path: str, idx: int, note: Note):
        meta = self._get_file_meta(file_path)
        notes = meta['notes'].get(str(idx), [])
        meta['notes'][str(idx)] = [n for n in notes
                                   if not (n['timestamp'] == note.timestamp and
                                           n['content'] == note.content)]
        if not meta['notes'][str(idx)]:
            del meta['notes'][str(idx)]
        self._save()

    def update_note(self, file_path: str, idx: int, old: Note, new_content: str):
        meta = self._get_file_meta(file_path)
        notes = meta['notes'].get(str(idx), [])
        for note in notes:
            if note['timestamp'] == old.timestamp and note['content'] == old.content:
                note['content'] = new_content
                note['timestamp'] = datetime.now().isoformat()
                self._save()
                return


class FileReader:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.offsets, self.encoding = self._build_index()

    def _build_index(self) -> Tuple[array, str]:
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
        offset = self.offsets[idx]
        with open(self.file_path, 'rb') as f:
            f.seek(offset)
            line = f.readline()
            return line.decode(self.encoding).rstrip('\n\r')

    @property
    def total(self) -> int:
        return len(self.offsets)


# ============================================================================
# 业务层
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

    def get_current_paragraph(self) -> str:
        return self.reader.get_paragraph(self.current_idx)

    @property
    def total_paragraphs(self) -> int:
        return self.reader.total

    @property
    def current(self) -> int:
        return self.current_idx

class BookmarkService:
    def __init__(self, repo: IMetadataRepository, file_path: str):
        self.repo = repo
        self.file_path = file_path

    def get_all(self) -> List[Bookmark]:
        return self.repo.get_bookmarks(self.file_path)

    def add(self, idx: int, label: str = "") -> Bookmark:
        bm = Bookmark(idx, datetime.now().isoformat(), label)
        self.repo.add_bookmark(self.file_path, bm)
        return bm

    def delete(self, bookmark: Bookmark):
        self.repo.delete_bookmark(self.file_path, bookmark)

    def update_label(self, bookmark: Bookmark, new_label: str):
        self.repo.update_bookmark(self.file_path, bookmark, new_label)

    def has_at(self, idx: int) -> bool:
        return any(b.idx == idx for b in self.get_all())

class NoteService:
    def __init__(self, repo: IMetadataRepository, file_path: str):
        self.repo = repo
        self.file_path = file_path

    def get_all(self, idx: int) -> List[Note]:
        return self.repo.get_notes(self.file_path, idx)

    def add(self, idx: int, content: str) -> Note:
        note = Note(datetime.now().isoformat(), content)
        self.repo.add_note(self.file_path, idx, note)
        return note

    def delete(self, idx: int, note: Note):
        self.repo.delete_note(self.file_path, idx, note)

    def update(self, idx: int, old: Note, new_content: str):
        self.repo.update_note(self.file_path, idx, old, new_content)

    def has_at(self, idx: int) -> bool:
        return len(self.get_all(idx)) > 0


# ============================================================================
# 表现层 - 视图（保持不变）
# ============================================================================

class BookmarkListView:
    def __init__(self, key_binding: KeyBinding, platform: IPlatform):
        self.key_binding = key_binding
        self.platform = platform

    def render(self, bookmarks: List[Bookmark], selected: int) -> None:
        ConsoleHelper.clear()
        print(self.key_binding.bookmark_list_title())
        print()
        if not bookmarks:
            print("没有书签记录。")
            print(f"按 {self.key_binding.get_display_key(Command.CANCEL)} 取消")
            return
        for i, bm in enumerate(bookmarks):
            prefix = "->" if i == selected else "  "
            dt = datetime.fromisoformat(bm.timestamp).strftime('%Y-%m-%d %H:%M:%S')
            label_str = f" [{bm.label}]" if bm.label else ""
            print(f"{prefix} 段落 {bm.idx+1}  -  {dt}{label_str}")
        print("\n" + "-" * 40)

    def get_key(self) -> Optional[str]:
        return self.platform.get_key()

class NoteManagementView:
    def __init__(self, key_binding: KeyBinding, platform: IPlatform):
        self.key_binding = key_binding
        self.platform = platform

    def render(self, notes: List[Note], idx: int, selected: int) -> None:
        ConsoleHelper.clear()
        print(self.key_binding.note_management_title(idx))
        print()
        if not notes:
            print("当前段落没有笔记。")
            print(f"按 {self.key_binding.get_display_key(Command.CANCEL)} 返回")
            return
        for i, note in enumerate(notes):
            prefix = "->" if i == selected else "  "
            dt = datetime.fromisoformat(note.timestamp).strftime('%Y-%m-%d %H:%M:%S')
            print(f"{prefix} [{dt}] {note.content}")
        print("\n" + "-" * 40)

    def get_key(self) -> Optional[str]:
        return self.platform.get_key()

class DetailView:
    @staticmethod
    def render(bookmark_svc: BookmarkService, note_svc: NoteService,
               idx: int, width: int) -> None:
        ConsoleHelper.clear()
        print("=" * width)
        print(f"段落 {idx+1} 详情")
        print("=" * width)

        bookmarks = bookmark_svc.get_all()
        labels = [b.label for b in bookmarks if b.idx == idx]
        if labels:
            print("\n[书签] 标签:")
            for lab in labels:
                print(f"  {lab}")
        else:
            print("\n[书签] 无")

        notes = note_svc.get_all(idx)
        if notes:
            print("\n[笔记]:")
            for note in notes:
                dt = datetime.fromisoformat(note.timestamp).strftime('%Y-%m-%d %H:%M:%S')
                print(f"  [{dt}] {note.content}")
        else:
            print("\n[笔记] 无")

        print("\n" + "-" * width)
        print(f"按 {KeyBinding().get_display_key(Command.CANCEL)} 返回...")


# ============================================================================
# 命令处理器（Use Cases）
# ============================================================================

class ICommandHandler(ABC):
    @abstractmethod
    def execute(self) -> None:
        pass

class UpHandler(ICommandHandler):
    def __init__(self, reading_svc: ReadingService):
        self.reading = reading_svc
    def execute(self):
        self.reading.prev()

class DownHandler(ICommandHandler):
    def __init__(self, reading_svc: ReadingService):
        self.reading = reading_svc
    def execute(self):
        self.reading.next()

class JumpHandler(ICommandHandler):
    def __init__(self, reading_svc: ReadingService, platform: IPlatform):
        self.reading = reading_svc
        self.platform = platform
    def execute(self):
        ConsoleHelper.clear()
        try:
            num = int(self.platform.input_line(f'跳转到段落 (1-{self.reading.total_paragraphs}): '))
            if 1 <= num <= self.reading.total_paragraphs:
                self.reading.go_to(num - 1)
        except (ValueError, EOFError):
            pass

class ShowBookmarkListHandler(ICommandHandler):
    def __init__(self, bookmark_svc: BookmarkService, reading_svc: ReadingService,
                 key_binding: KeyBinding, platform: IPlatform):
        self.bookmarks = bookmark_svc
        self.reading = reading_svc
        self.key_binding = key_binding
        self.view = BookmarkListView(key_binding, platform)

    def execute(self):
        bookmarks = self.bookmarks.get_all()
        if not bookmarks:
            self.view.render(bookmarks, 0)
            self.view.get_key()  # 等待取消
            return

        bookmarks.sort(key=lambda b: b.timestamp)
        total = len(bookmarks)
        selected = 0

        while True:
            self.view.render(bookmarks, selected)
            key = self.view.get_key()
            cmd = self.key_binding.get_command(key)

            if cmd == Command.UP and selected > 0:
                selected -= 1
            elif cmd == Command.DOWN and selected < total - 1:
                selected += 1
            elif cmd == Command.CANCEL:
                break
            elif cmd == Command.SELECT:
                self.reading.go_to(bookmarks[selected].idx)
                break
            elif cmd == Command.DELETE:
                self.bookmarks.delete(bookmarks[selected])
                bookmarks = self.bookmarks.get_all()
                if not bookmarks:
                    self.view.render(bookmarks, 0)
                    self.view.get_key()
                    break
                total = len(bookmarks)
                if selected >= total:
                    selected = total - 1
            elif cmd == Command.EDIT:
                ConsoleHelper.clear()
                current = bookmarks[selected].label
                print(f"当前标签: {current}")
                new_label = self.view.platform.input_line("输入新标签（空字符串清除）: ").strip()
                self.bookmarks.update_label(bookmarks[selected], new_label)
                bookmarks = self.bookmarks.get_all()
                bookmarks.sort(key=lambda b: b.timestamp)
                total = len(bookmarks)
                # 重新定位选中项
                for i, bm in enumerate(bookmarks):
                    if bm.idx == bookmarks[selected].idx:
                        selected = i
                        break

class AddNoteHandler(ICommandHandler):
    def __init__(self, note_svc: NoteService, reading_svc: ReadingService, platform: IPlatform):
        self.notes = note_svc
        self.reading = reading_svc
        self.platform = platform

    def execute(self):
        ConsoleHelper.clear()
        content = self.platform.input_line(f"为段落 {self.reading.current+1} 添加笔记 (空行取消): ").strip()
        if content:
            self.notes.add(self.reading.current, content)
            print("笔记已添加。按任意键继续...")
            ConsoleHelper.wait_for_any_key(self.platform)

class ToggleNotesHandler(ICommandHandler):
    def __init__(self, controller: 'MainController'):
        self.controller = controller
    def execute(self):
        self.controller.show_notes = not self.controller.show_notes

class AddBookmarkHandler(ICommandHandler):
    def __init__(self, bookmark_svc: BookmarkService, reading_svc: ReadingService, platform: IPlatform):
        self.bookmarks = bookmark_svc
        self.reading = reading_svc
        self.platform = platform

    def execute(self):
        ConsoleHelper.clear()
        label = self.platform.input_line(f"为段落 {self.reading.current+1} 添加书签标签 (空行取消): ").strip()
        if label:
            self.bookmarks.add(self.reading.current, label)
            print("书签已添加。按任意键继续...")
            ConsoleHelper.wait_for_any_key(self.platform)

class ManageNotesHandler(ICommandHandler):
    def __init__(self, note_svc: NoteService, reading_svc: ReadingService,
                 key_binding: KeyBinding, platform: IPlatform):
        self.notes = note_svc
        self.reading = reading_svc
        self.key_binding = key_binding
        self.view = NoteManagementView(key_binding, platform)

    def execute(self):
        idx = self.reading.current
        notes = self.notes.get_all(idx)
        if not notes:
            self.view.render(notes, idx, 0)
            self.view.get_key()
            return

        selected = 0
        while True:
            self.view.render(notes, idx, selected)
            key = self.view.get_key()
            cmd = self.key_binding.get_command(key)

            if cmd == Command.UP and selected > 0:
                selected -= 1
            elif cmd == Command.DOWN and selected < len(notes) - 1:
                selected += 1
            elif cmd == Command.CANCEL:
                break
            elif cmd == Command.DELETE:
                self.notes.delete(idx, notes[selected])
                notes = self.notes.get_all(idx)
                if not notes:
                    self.view.render(notes, idx, 0)
                    self.view.get_key()
                    break
                if selected >= len(notes):
                    selected = len(notes) - 1
            elif cmd == Command.EDIT:
                ConsoleHelper.clear()
                current = notes[selected].content
                print(f"当前内容: {current}")
                new_content = self.view.platform.input_line("输入新内容: ").strip()
                if new_content:
                    self.notes.update(idx, notes[selected], new_content)
                    notes = self.notes.get_all(idx)
                    if selected >= len(notes):
                        selected = len(notes) - 1

class ShowDetailsHandler(ICommandHandler):
    def __init__(self, bookmark_svc: BookmarkService, note_svc: NoteService,
                 reading_svc: ReadingService, platform: IPlatform, width: int):
        self.bookmarks = bookmark_svc
        self.notes = note_svc
        self.reading = reading_svc
        self.platform = platform
        self.width = width

    def execute(self):
        DetailView.render(self.bookmarks, self.notes, self.reading.current, self.width)
        self.platform.get_key()

class QuitHandler(ICommandHandler):
    def __init__(self, bookmark_svc: BookmarkService, reading_svc: ReadingService):
        self.bookmarks = bookmark_svc
        self.reading = reading_svc

    def execute(self):
        self.bookmarks.add(self.reading.current)
        # 我们通过抛出自定义异常来通知控制器退出，但这里保持简单：设置标志
        # 为保持整洁，我们让控制器检测到 Quit 命令后退出，而不是由处理器控制。
        # 所以这个处理器实际上不需要做任何事情，只是作为一个标记，控制器会处理退出。
        pass


# ============================================================================
# 主控制器（精简后）
# ============================================================================

class MainController:
    def __init__(self, reading_svc: ReadingService, bookmark_svc: BookmarkService,
                 note_svc: NoteService, key_binding: KeyBinding,
                 platform: IPlatform, width: int):
        self.reading = reading_svc
        self.bookmarks = bookmark_svc
        self.notes = note_svc
        self.key_binding = key_binding
        self.platform = platform
        self.width = width
        self.show_notes = True

        # 构建命令处理器映射
        self.handlers = {
            Command.UP: UpHandler(reading_svc),
            Command.DOWN: DownHandler(reading_svc),
            Command.JUMP: JumpHandler(reading_svc, platform),
            Command.BOOKMARK_LIST: ShowBookmarkListHandler(bookmark_svc, reading_svc, key_binding, platform),
            Command.ADD_NOTE: AddNoteHandler(note_svc, reading_svc, platform),
            Command.TOGGLE_NOTES: ToggleNotesHandler(self),
            Command.ADD_BOOKMARK: AddBookmarkHandler(bookmark_svc, reading_svc, platform),
            Command.MANAGE_NOTES: ManageNotesHandler(note_svc, reading_svc, key_binding, platform),
            Command.DETAILS: ShowDetailsHandler(bookmark_svc, note_svc, reading_svc, platform, width),
        }

    def _build_hint(self) -> str:
        parts = []
        notes_status = "显示" if self.show_notes else "隐藏"
        for cmd in KeyBinding.TOP_LEVEL_COMMANDS:
            key = self.key_binding.get_display_key(cmd)
            desc = self.key_binding.get_description(cmd)
            if cmd == Command.TOGGLE_NOTES:
                desc = f"切换笔记({notes_status})"
            parts.append(f"{key} {desc}")
        return '  '.join(parts)

    def run(self):
        total = self.reading.total_paragraphs
        while True:
            ConsoleHelper.clear()

            # 渲染段落
            content = self.reading.get_current_paragraph()
            wrapped = textwrap.fill(content, width=self.width, break_long_words=False)
            print(wrapped)

            # 渲染笔记
            if self.show_notes:
                notes = self.notes.get_all(self.reading.current)
                if notes:
                    print("\n" + "=" * self.width)
                    print(self.key_binding.notes_display_header())
                    for note in notes:
                        dt = datetime.fromisoformat(note.timestamp).strftime('%Y-%m-%d %H:%M')
                        truncated = ConsoleHelper.truncate(note.content)
                        print(f"  [{dt}] {truncated}")
                    print("=" * self.width)

            # 状态栏
            print('\n' + '-' * self.width)
            mark = ""
            if self.bookmarks.has_at(self.reading.current):
                mark += "[书签]"
            if self.notes.has_at(self.reading.current):
                mark += "[笔记]"
            hint = self._build_hint()
            print(f'{mark} 第 {self.reading.current+1} / {total} 段    {hint}')

            # 获取按键并执行对应处理器
            key = self.platform.get_key()
            cmd = self.key_binding.get_command(key)

            if cmd == Command.QUIT or cmd == Command.CANCEL:
                # 退出时记录书签
                self.bookmarks.add(self.reading.current)
                break
            elif cmd in self.handlers:
                self.handlers[cmd].execute()
            # 其他未知命令忽略


# ============================================================================
# 程序入口
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print('用法: python read-book.py <文本文件>')
        sys.exit(1)

    file_path = os.path.abspath(sys.argv[1])
    reader = FileReader(file_path)
    if reader.total == 0:
        print("文件中没有非空行。")
        sys.exit(0)

    repo = JsonMetadataRepository()
    reading_svc = ReadingService(reader)
    bookmark_svc = BookmarkService(repo, file_path)
    note_svc = NoteService(repo, file_path)
    key_binding = KeyBinding()
    platform = PlatformFactory.create()
    width = ConsoleHelper.get_terminal_width()

    controller = MainController(reading_svc, bookmark_svc, note_svc, key_binding, platform, width)
    controller.run()

if __name__ == '__main__':
    main()
