from PyQt6.QtCore import QAbstractListModel, QModelIndex, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QListView, QMenu, QStyle, QStyledItemDelegate


CARD_W = 220
CARD_H = 78


class ToolModel(QAbstractListModel):
    def __init__(self, tools: list[dict], parent=None):
        super().__init__(parent)
        self._tools = tools

    def set_tools(self, tools: list[dict]) -> None:
        self.beginResetModel()
        self._tools = tools
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._tools)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._tools):
            return None
        tool = self._tools[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return tool.get("name", "")
        if role == Qt.ItemDataRole.UserRole:
            return tool
        return None


class ToolDelegate(QStyledItemDelegate):
    """Card-style tool item: name + meta (type · env), with star for favorites."""

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.t = theme
        self._c_bg = QColor(theme["bg"])
        self._c_card = QColor(theme["bg_alt"])
        self._c_active = QColor(theme["bg_active"])
        self._c_hover = QColor(theme["bg_hover"])
        self._c_border = QColor(theme["border"])
        self._c_text = QColor(theme["text"])
        self._c_mute = QColor(theme["text_mute"])
        self._c_dim = QColor(theme["text_dim"])
        self._c_accent = QColor(theme["accent"])

        self._name_font = QFont()
        self._name_font.setPointSize(13)
        self._name_font.setWeight(QFont.Weight.Medium)
        self._meta_font = QFont()
        self._meta_font.setPointSize(11)
        self._star_font = QFont()
        self._star_font.setPointSize(12)

        # Env name lookup, populated by the grid before set_tools()
        self._env_names: dict[str, str] = {}

    def set_env_names(self, env_names: dict[str, str]) -> None:
        self._env_names = env_names

    def sizeHint(self, option, index) -> QSize:
        return QSize(CARD_W, CARD_H)

    def paint(self, painter: QPainter, option, index) -> None:
        tool = index.data(Qt.ItemDataRole.UserRole) or {}
        rect: QRect = option.rect

        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        # ALWAYS fill the cell (fixes 花屏 — uninitialized pixels otherwise)
        painter.fillRect(rect, self._c_bg)

        body = rect.adjusted(4, 4, -4, -4)

        # Card body
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if selected:
            painter.setBrush(self._c_active)
            painter.setPen(QPen(self._c_accent, 1))
        elif hovered:
            painter.setBrush(self._c_hover)
            painter.setPen(QPen(self._c_border, 1))
        else:
            painter.setBrush(self._c_card)
            painter.setPen(QPen(self._c_border, 1))
        painter.drawRoundedRect(body, 8, 8)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        # Name row (with star prefix if favorite)
        name_x = body.left() + 12
        name_y = body.top() + 8
        name_w = body.right() - name_x - 12
        if tool.get("favorite"):
            painter.setFont(self._star_font)
            painter.setPen(QPen(self._c_accent))
            painter.drawText(
                QRect(body.left() + 8, name_y, 14, 22),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                "★",
            )
            name_x += 14
            name_w -= 14

        painter.setFont(self._name_font)
        painter.setPen(QPen(self._c_text))
        name = tool.get("name", "")
        elided = painter.fontMetrics().elidedText(name, Qt.TextElideMode.ElideRight, name_w)
        painter.drawText(
            QRect(name_x, name_y, name_w, 22),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided,
        )

        # Meta row 1: type
        painter.setFont(self._meta_font)
        painter.setPen(QPen(self._c_mute))
        ttype = (tool.get("type") or "").lower()
        painter.drawText(
            QRect(body.left() + 12, body.top() + 30, body.width() - 24, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            ttype,
        )

        # Meta row 2: env name (or "默认")
        env_id = tool.get("env_id")
        if env_id and env_id in self._env_names:
            env_label = self._env_names[env_id]
        elif ttype in ("python", "java"):
            env_label = "默认环境"
        else:
            env_label = ""
        if env_label:
            painter.setPen(QPen(self._c_dim))
            elided_env = painter.fontMetrics().elidedText(
                env_label, Qt.TextElideMode.ElideMiddle, body.width() - 24
            )
            painter.drawText(
                QRect(body.left() + 12, body.top() + 50, body.width() - 24, 18),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                elided_env,
            )


class ToolGrid(QListView):
    launch_requested = pyqtSignal(dict)
    detail_requested = pyqtSignal(dict)
    edit_requested = pyqtSignal(dict)
    delete_requested = pyqtSignal(dict)
    favorite_toggled = pyqtSignal(dict)
    copy_path_requested = pyqtSignal(dict)

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.t = theme
        self.setObjectName("toolList")
        self.setMouseTracking(True)
        self.setSelectionMode(QListView.SelectionMode.SingleSelection)
        self.setUniformItemSizes(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)

        # Grid (icon) mode — items flow L→R then wrap.
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setFlow(QListView.Flow.LeftToRight)
        self.setWrapping(True)
        self.setResizeMode(QListView.ResizeMode.Adjust)  # re-flow on resize
        self.setMovement(QListView.Movement.Static)      # no drag-reorder
        self.setSpacing(4)

        self.verticalScrollBar().setSingleStep(16)

        self.setModel(ToolModel([]))
        self._delegate = ToolDelegate(theme, self)
        self.setItemDelegate(self._delegate)
        self.doubleClicked.connect(self._on_double)

    def set_env_names(self, env_names: dict[str, str]) -> None:
        self._delegate.set_env_names(env_names)

    def set_tools(self, tools: list[dict]) -> None:
        model = self.model()
        assert isinstance(model, ToolModel)
        self.setUpdatesEnabled(False)
        try:
            model.set_tools(tools)
        finally:
            self.setUpdatesEnabled(True)

    def _on_double(self, index: QModelIndex) -> None:
        tool = index.data(Qt.ItemDataRole.UserRole)
        if tool:
            self.detail_requested.emit(tool)

    def _show_menu(self, pos) -> None:
        idx = self.indexAt(pos)
        if not idx.isValid():
            return
        tool = idx.data(Qt.ItemDataRole.UserRole)
        if not tool:
            return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background: {self.t['bg_alt']};
                border: 1px solid {self.t['border']};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 18px;
                border-radius: 4px;
                color: {self.t['text']};
            }}
            QMenu::item:selected {{
                background: {self.t['bg_hover']};
            }}
            QMenu::separator {{
                height: 1px;
                background: {self.t['border']};
                margin: 4px 6px;
            }}
        """)

        detail = QAction("查看详情     ↵↵", menu)
        detail.triggered.connect(lambda: self.detail_requested.emit(tool))
        menu.addAction(detail)

        launch = QAction("启动", menu)
        launch.triggered.connect(lambda: self.launch_requested.emit(tool))
        menu.addAction(launch)

        fav_label = "取消收藏" if tool.get("favorite") else "加入收藏"
        fav = QAction(fav_label, menu)
        fav.triggered.connect(lambda: self.favorite_toggled.emit(tool))
        menu.addAction(fav)

        menu.addSeparator()

        edit = QAction("编辑 / 设置环境…     ⌘E", menu)
        edit.triggered.connect(lambda: self.edit_requested.emit(tool))
        menu.addAction(edit)

        copy_p = QAction("复制路径", menu)
        copy_p.triggered.connect(lambda: self.copy_path_requested.emit(tool))
        menu.addAction(copy_p)

        menu.addSeparator()

        delete = QAction("删除     ⌫", menu)
        delete.triggered.connect(lambda: self.delete_requested.emit(tool))
        menu.addAction(delete)

        menu.exec(self.viewport().mapToGlobal(pos))
