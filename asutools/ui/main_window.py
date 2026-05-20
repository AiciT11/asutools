from collections import Counter

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import launcher, store, theme
from .grid import ToolGrid
from .tabs import ALL_ID, FAV_ID, RECENT_ID, CategoryTabs


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 默认宽度刚好容纳 4 张卡片 + 间距 + 滚动条
        # 4 × CARD_W(220) + 5 × spacing(4) + chrome ≈ 920
        self.setWindowTitle("asuTools")
        self.resize(940, 720)
        self.setMinimumSize(700, 500)

        settings = store.load_settings()
        self.theme = theme.LIGHT if settings.get("theme") == "light" else theme.DARK
        self.setStyleSheet(theme.qss(self.theme))

        self.tools: list[dict] = store.load_tools()
        self.categories: list[dict] = store.load_categories()
        self.environments: dict = store.load_environments()

        self._current_category: str = ALL_ID
        self._search_text: str = ""

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(60)
        self._search_timer.timeout.connect(self._apply_search)

        self._build_ui()
        self._build_menubar()
        self._build_shortcuts()
        self._refresh_tabs()
        self._refresh_list()
        self._update_status()
        self.tool_grid.setFocus()

    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("root")
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Top bar: search + buttons ---
        topbar = QFrame(self)
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(48)
        tl = QHBoxLayout(topbar)
        tl.setContentsMargins(16, 8, 16, 8)
        tl.setSpacing(8)

        self.search_input = QLineEdit(self)
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("搜索工具    ⌘K")
        self.search_input.textChanged.connect(self._on_search)
        self.search_input.returnPressed.connect(self._launch_first_visible)
        tl.addWidget(self.search_input, 1)

        add_btn = QPushButton("+ 新增")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self.action_new_tool)
        tl.addWidget(add_btn)

        settings_btn = QPushButton("设置")
        settings_btn.clicked.connect(self.action_settings)
        tl.addWidget(settings_btn)

        root_layout.addWidget(topbar)

        # --- Category tabs row ---
        tabs_wrap = QFrame(self)
        tabs_wrap.setObjectName("tabsWrap")
        tabs_wrap.setFixedHeight(36)
        twl = QHBoxLayout(tabs_wrap)
        twl.setContentsMargins(8, 0, 8, 0)
        twl.setSpacing(0)
        self.category_tabs = CategoryTabs(self.theme, self)
        self.category_tabs.category_changed.connect(self._on_category)
        twl.addWidget(self.category_tabs, 1)
        root_layout.addWidget(tabs_wrap)

        # --- Tool list (full width, grid layout) ---
        self.tool_grid = ToolGrid(self.theme, self)
        self.tool_grid.launch_requested.connect(self._on_launch)
        self.tool_grid.edit_requested.connect(self._on_edit_tool)
        self.tool_grid.delete_requested.connect(self._on_delete_tool)
        self.tool_grid.favorite_toggled.connect(self._on_toggle_favorite)
        self.tool_grid.copy_path_requested.connect(self._on_copy_path)
        self._refresh_env_names()
        root_layout.addWidget(self.tool_grid, 1)

        # --- Status bar ---
        statusbar = QFrame(self)
        statusbar.setObjectName("statusbar")
        statusbar.setFixedHeight(28)
        sl = QHBoxLayout(statusbar)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)
        self.status_label = QLabel("", self)
        self.status_label.setObjectName("statusLabel")
        sl.addWidget(self.status_label)
        sl.addStretch(1)
        self.env_label = QLabel("", self)
        self.env_label.setObjectName("statusLabel")
        sl.addWidget(self.env_label)
        root_layout.addWidget(statusbar)

    def _build_menubar(self) -> None:
        """Native Mac menu bar — gives us ⌘M / ⌘W / ⌘H and a proper app menu."""
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("文件")
        a_new = QAction("新增工具", self)
        a_new.setShortcut(QKeySequence("Ctrl+N"))
        a_new.triggered.connect(self.action_new_tool)
        file_menu.addAction(a_new)

        a_settings = QAction("偏好设置…", self)
        a_settings.setShortcut(QKeySequence("Ctrl+,"))
        a_settings.setMenuRole(QAction.MenuRole.PreferencesRole)
        a_settings.triggered.connect(self.action_settings)
        file_menu.addAction(a_settings)

        file_menu.addSeparator()
        a_close = QAction("关闭窗口", self)
        a_close.setShortcut(QKeySequence("Ctrl+W"))
        a_close.triggered.connect(self.close)
        file_menu.addAction(a_close)

        # Edit
        edit_menu = mb.addMenu("编辑")
        a_edit_tool = QAction("编辑当前工具", self)
        a_edit_tool.setShortcut(QKeySequence("Ctrl+E"))
        a_edit_tool.triggered.connect(self._edit_selected)
        edit_menu.addAction(a_edit_tool)
        a_fav = QAction("切换收藏", self)
        a_fav.setShortcut(QKeySequence("Ctrl+Shift+D"))
        a_fav.triggered.connect(self._toggle_favorite_selected)
        edit_menu.addAction(a_fav)

        # Window — the magic that brings back ⌘M etc.
        win_menu = mb.addMenu("窗口")
        a_min = QAction("最小化", self)
        a_min.setShortcut(QKeySequence("Ctrl+M"))
        a_min.triggered.connect(self.showMinimized)
        win_menu.addAction(a_min)
        a_max = QAction("缩放", self)
        a_max.triggered.connect(self._toggle_max)
        win_menu.addAction(a_max)
        a_hide = QAction("隐藏 asuTools", self)
        a_hide.setShortcut(QKeySequence("Ctrl+H"))
        a_hide.triggered.connect(self.hide)
        win_menu.addAction(a_hide)
        win_menu.addSeparator()
        a_full = QAction("进入全屏", self)
        a_full.setShortcut(QKeySequence("Ctrl+Ctrl+F"))  # ⌃⌘F is Mac standard
        a_full.triggered.connect(self._toggle_fullscreen)
        win_menu.addAction(a_full)

    def _toggle_max(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _build_shortcuts(self) -> None:
        # Direct shortcuts in addition to menubar items — works even if menubar
        # focus is weird. macOS: Qt's Ctrl = Cmd.
        for seq in ("Ctrl+K", "Meta+K", "Ctrl+F"):
            QShortcut(QKeySequence(seq), self, activated=self._focus_search)
        for seq in ("Ctrl+N", "Meta+N"):
            QShortcut(QKeySequence(seq), self, activated=self.action_new_tool)
        for seq in ("Ctrl+,", "Meta+,"):
            QShortcut(QKeySequence(seq), self, activated=self.action_settings)
        for seq in ("Ctrl+E", "Meta+E"):
            QShortcut(QKeySequence(seq), self, activated=self._edit_selected)
        for seq in ("Ctrl+Shift+D", "Meta+Shift+D"):
            QShortcut(QKeySequence(seq), self, activated=self._toggle_favorite_selected)

        # iTerm-style tab switch: Shift+Cmd+[ / Shift+Cmd+]
        for seq in ("Ctrl+Shift+[", "Meta+Shift+["):
            QShortcut(QKeySequence(seq), self, activated=lambda: self.category_tabs.select_offset(-1))
        for seq in ("Ctrl+Shift+]", "Meta+Shift+]"):
            QShortcut(QKeySequence(seq), self, activated=lambda: self.category_tabs.select_offset(+1))
        # Cmd+1..9 jump to tab
        for i in range(1, 10):
            for prefix in ("Ctrl", "Meta"):
                QShortcut(
                    QKeySequence(f"{prefix}+{i}"),
                    self,
                    activated=lambda idx=i - 1: self.category_tabs.select_index(idx),
                )

        QShortcut(QKeySequence("Return"), self.tool_grid, activated=self._launch_selected)
        QShortcut(QKeySequence("Enter"), self.tool_grid, activated=self._launch_selected)
        QShortcut(QKeySequence("Backspace"), self.tool_grid, activated=self._delete_selected)
        QShortcut(QKeySequence("Escape"), self, activated=self._clear_search)

        # Window management fallbacks (in case menubar doesn't get them)
        for seq in ("Ctrl+M", "Meta+M"):
            QShortcut(QKeySequence(seq), self, activated=self.showMinimized)
        for seq in ("Ctrl+W", "Meta+W"):
            QShortcut(QKeySequence(seq), self, activated=self.close)
        for seq in ("Ctrl+H", "Meta+H"):
            QShortcut(QKeySequence(seq), self, activated=self.hide)

    def _refresh_env_names(self) -> None:
        env_map = {e["id"]: e.get("name", "") for e in self.environments.get("environments", [])}
        self.tool_grid.set_env_names(env_map)

    def _focus_search(self) -> None:
        self.search_input.setFocus()
        self.search_input.selectAll()

    def _clear_search(self) -> None:
        if self.search_input.text():
            self.search_input.clear()
        else:
            self.search_input.clearFocus()
            self.tool_grid.setFocus()

    def _refresh_tabs(self) -> None:
        counts: Counter[str] = Counter()
        favs = 0
        recents = 0
        for t in self.tools:
            counts[t.get("category", "")] += 1
            if t.get("favorite"):
                favs += 1
            if t.get("last_used"):
                recents += 1
        d = dict(counts)
        d[FAV_ID] = favs
        d[RECENT_ID] = recents
        self.category_tabs.set_categories(self.categories, d)

    def _filter_tools(self) -> list[dict]:
        tools = self.tools
        if self._current_category == FAV_ID:
            tools = [t for t in tools if t.get("favorite")]
        elif self._current_category == RECENT_ID:
            tools = [t for t in tools if t.get("last_used")]
            tools = sorted(tools, key=lambda t: t.get("last_used", 0), reverse=True)
        elif self._current_category != ALL_ID:
            tools = [t for t in tools if t.get("category") == self._current_category]
        if self._search_text:
            q = self._search_text.lower()
            tools = [
                t for t in tools
                if q in t.get("name", "").lower()
                or q in t.get("description", "").lower()
                or any(q in tag.lower() for tag in t.get("tags", []))
            ]
        return tools

    def _refresh_list(self) -> None:
        filtered = self._filter_tools()
        self._last_filtered_count = len(filtered)
        self.tool_grid.set_tools(filtered)
        # Auto-select first item so arrow keys + Enter work immediately
        if filtered:
            self.tool_grid.setCurrentIndex(self.tool_grid.model().index(0, 0))

    def _on_category(self, cid: str) -> None:
        self._current_category = cid
        self._refresh_list()
        self._update_status()

    def _on_search(self, text: str) -> None:
        self._pending_search = text.strip()
        self._search_timer.start()

    def _apply_search(self) -> None:
        if getattr(self, "_pending_search", "") == self._search_text:
            return
        self._search_text = self._pending_search
        self._refresh_list()
        self._update_status()

    def _on_launch(self, tool: dict) -> None:
        ok, msg = launcher.launch(tool)
        self.status_label.setText(msg)
        if ok:
            launcher.record_recent(tool.get("id", ""))
            self.tools = store.load_tools()
        else:
            QMessageBox.warning(self, "启动失败", msg)

    def _launch_selected(self) -> None:
        idx = self.tool_grid.currentIndex()
        if not idx.isValid():
            return
        tool = idx.data(Qt.ItemDataRole.UserRole)
        if tool:
            self._on_launch(tool)

    def _launch_first_visible(self) -> None:
        tools = self._filter_tools()
        if tools:
            self._on_launch(tools[0])

    def action_new_tool(self) -> None:
        from .dialogs import ToolDialog
        envs = self.environments.get("environments", [])
        dlg = ToolDialog(self.theme, None, self.categories, envs, self)
        dlg.saved.connect(self._on_tool_saved)
        dlg.exec()

    def _on_tool_saved(self, tool: dict) -> None:
        idx = next((i for i, t in enumerate(self.tools) if t.get("id") == tool.get("id")), -1)
        if idx >= 0:
            self.tools[idx] = tool
        else:
            self.tools.append(tool)
        store.save_tools(self.tools)
        self._refresh_tabs()
        self._refresh_list()
        self._update_status()

    def action_settings(self) -> None:
        from .dialogs import SettingsDialog
        dlg = SettingsDialog(self.theme, self)
        dlg.settings_changed.connect(self._on_settings_changed)
        dlg.exec()

    def _selected_tool(self) -> dict | None:
        idx = self.tool_grid.currentIndex()
        if not idx.isValid():
            return None
        return idx.data(Qt.ItemDataRole.UserRole)

    def _edit_selected(self) -> None:
        t = self._selected_tool()
        if t:
            self._on_edit_tool(t)

    def _delete_selected(self) -> None:
        t = self._selected_tool()
        if t:
            self._on_delete_tool(t)

    def _toggle_favorite_selected(self) -> None:
        t = self._selected_tool()
        if t:
            self._on_toggle_favorite(t)

    def _on_edit_tool(self, tool: dict) -> None:
        from .dialogs import ToolDialog
        envs = self.environments.get("environments", [])
        dlg = ToolDialog(self.theme, tool, self.categories, envs, self)
        dlg.saved.connect(self._on_tool_saved)
        dlg.exec()

    def _on_delete_tool(self, tool: dict) -> None:
        reply = QMessageBox.question(
            self, "确认删除",
            f"删除工具「{tool.get('name', '')}」？\n（仅从启动器移除，不删除文件本身）",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        tid = tool.get("id")
        self.tools = [t for t in self.tools if t.get("id") != tid]
        store.save_tools(self.tools)
        self._refresh_tabs()
        self._refresh_list()
        self._update_status()

    def _on_toggle_favorite(self, tool: dict) -> None:
        tid = tool.get("id")
        for t in self.tools:
            if t.get("id") == tid:
                t["favorite"] = not t.get("favorite", False)
                break
        store.save_tools(self.tools)
        self._refresh_tabs()
        self._refresh_list()

    def _on_copy_path(self, tool: dict) -> None:
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(tool.get("path", ""))
        self.status_label.setText(f"已复制路径: {tool.get('path', '')}")

    def _on_settings_changed(self) -> None:
        self.environments = store.load_environments()
        self._refresh_env_names()
        self.tool_grid.viewport().update()
        self._update_status()

    def _update_status(self) -> None:
        n = getattr(self, "_last_filtered_count", len(self.tools))
        total = len(self.tools)
        self.status_label.setText(f"{n} / {total} 个工具")
        envs = self.environments.get("environments", [])
        defaults = self.environments.get("defaults", {})
        py_id = defaults.get("python", "")
        py_name = next((e.get("name", "") for e in envs if e.get("id") == py_id), "未设置")
        self.env_label.setText(f"Python: {py_name}    Envs: {len(envs)}")
