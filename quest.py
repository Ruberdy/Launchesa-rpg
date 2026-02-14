import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QPushButton, QLineEdit, QComboBox, QGraphicsDropShadowEffect,
    QStackedWidget, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QSize, QUrl
from PyQt5.QtGui import QPixmap, QColor
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply


class QuestPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.all_quests = []
        self.filtered_quests = []
        self.quest_url = "https://raw.githubusercontent.com/Ruberdy/FosterGames/main/quests.json"
        self.categories = ["Todas", "Principal", "Secundaria", "Épica"]

        self.network_manager = QNetworkAccessManager()
        self.image_cache = {}

        self.apply_theme()

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.create_sidebar(root_layout)

        self.content_stack = QStackedWidget()
        root_layout.addWidget(self.content_stack, 1)

        self.create_list_view()
        self.create_detail_view()
        self.content_stack.setCurrentWidget(self.list_view)

        self.load_quests_from_url()

    def apply_theme(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1F2630;
                color: #F2F2F2;
                font-family: 'Segoe UI';
            }
            #questSidebar {
                background: #2B3442;
                border-right: 1px solid #3A4556;
            }
            QPushButton#sidebarButton {
                background: #2E3746;
                border: 1px solid #3A4556;
                border-radius: 10px;
                color: #F2F2F2;
                font-weight: 600;
                text-align: left;
                padding: 10px;
            }
            QPushButton#sidebarButton:hover {
                background: #5C6778;
                border: 1px solid #6D7A8E;
            }
            QPushButton#sidebarButton:checked {
                background: #5C6778;
                border: 1px solid #C8A45C;
            }
            QPushButton#backToLauncherButton {
                background: #3A4556;
                border: 1px solid #C8A45C;
                border-radius: 10px;
                color: #F2F2F2;
                font-weight: 700;
                padding: 10px;
            }
            QPushButton#backToLauncherButton:hover {
                background: #5C6778;
            }
            #questHeaderCard, #questDetailContainer, #questCard {
                background: #2E3746;
                border: 1px solid #3A4556;
                border-radius: 10px;
            }
            QLineEdit, QComboBox, QListWidget {
                background-color: #2E3746;
                border: 1px solid #3A4556;
                border-radius: 8px;
                color: #F2F2F2;
                padding: 6px;
            }
            QComboBox QAbstractItemView {
                background: #2E3746;
                color: #F2F2F2;
                selection-background-color: #5C6778;
            }
            QScrollArea { border: none; background: transparent; }
        """)

    def create_sidebar(self, root_layout):
        sidebar = QWidget()
        sidebar.setObjectName("questSidebar")
        sidebar.setFixedWidth(220)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        logo = QLabel("⚔️  FOSTER QUESTS")
        logo.setStyleSheet("color: #C8A45C; font-size: 15px; font-weight: 700;")
        layout.addWidget(logo)

        back_btn = QPushButton("← Volver al Launcher")
        back_btn.setObjectName("backToLauncherButton")
        back_btn.clicked.connect(self.back_to_launcher)
        layout.addWidget(back_btn)

        self.sidebar_buttons = []
        nav = [
            ("📜  Misiones", self.show_list_view, True),
            ("⭐  Destacadas", self.show_list_view, False),
            ("🧭  Progreso", None, False),
        ]
        for text, handler, active in nav:
            btn = QPushButton(text)
            btn.setObjectName("sidebarButton")
            btn.setCheckable(True)
            btn.setChecked(active)
            btn.setMinimumHeight(44)
            if handler:
                btn.clicked.connect(handler)
            btn.clicked.connect(lambda _=False, b=btn: self._set_sidebar_active(b))
            layout.addWidget(btn)
            self.sidebar_buttons.append(btn)

        layout.addStretch()
        root_layout.addWidget(sidebar)

    def _set_sidebar_active(self, active_btn):
        for btn in self.sidebar_buttons:
            btn.setChecked(btn is active_btn)

    def back_to_launcher(self):
        if self.parent and hasattr(self.parent, 'show_main_page'):
            self.parent.show_main_page()

    def create_list_view(self):
        self.list_view = QWidget()
        layout = QVBoxLayout(self.list_view)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header = QWidget()
        header.setObjectName("questHeaderCard")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)

        title = QLabel("MISIONES ÉPICAS")
        title.setStyleSheet("color:#C8A45C;font-size:24px;font-weight:700;")

        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(10)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Buscar misiones...")
        self.search_bar.setMinimumHeight(34)
        self.search_bar.textChanged.connect(self.filter_quests)

        self.category_filter = QComboBox()
        self.category_filter.addItems(self.categories)
        self.category_filter.setMinimumWidth(170)
        self.category_filter.setMinimumHeight(34)
        self.category_filter.currentTextChanged.connect(self.filter_quests)

        controls_layout.addWidget(self.search_bar)
        controls_layout.addWidget(self.category_filter)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(controls)
        layout.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.quest_container = QWidget()
        self.quest_layout = QVBoxLayout(self.quest_container)
        self.quest_layout.setContentsMargins(0, 0, 0, 0)
        self.quest_layout.setSpacing(10)

        self.scroll.setWidget(self.quest_container)
        layout.addWidget(self.scroll)

        self.content_stack.addWidget(self.list_view)

    def create_detail_view(self):
        self.detail_view = QWidget()
        main_layout = QHBoxLayout(self.detail_view)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        self.quest_index = QListWidget()
        self.quest_index.setMaximumWidth(260)
        self.quest_index.itemClicked.connect(self.on_index_item_clicked)
        main_layout.addWidget(self.quest_index)

        detail_container = QWidget()
        detail_container.setObjectName("questDetailContainer")
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(12, 12, 12, 12)
        detail_layout.setSpacing(10)

        self.detail_image = QLabel()
        self.detail_image.setAlignment(Qt.AlignCenter)
        self.detail_image.setMinimumHeight(180)

        self.detail_title = QLabel()
        self.detail_title.setStyleSheet("color:#F2F2F2;font-size:24px;font-weight:700;")
        self.detail_title.setWordWrap(True)

        self.detail_meta = QLabel()
        self.detail_meta.setStyleSheet("color:#B8C1CC;font-size:12px;")

        self.detail_content = QLabel()
        self.detail_content.setStyleSheet("color:#B8C1CC;font-size:13px;")
        self.detail_content.setWordWrap(True)

        row = QHBoxLayout()
        back_list_btn = QPushButton("Volver a Misiones")
        back_list_btn.setObjectName("sidebarButton")
        back_list_btn.clicked.connect(self.show_list_view)

        back_launcher_btn = QPushButton("← Volver al Launcher")
        back_launcher_btn.setObjectName("backToLauncherButton")
        back_launcher_btn.clicked.connect(self.back_to_launcher)

        row.addWidget(back_list_btn)
        row.addWidget(back_launcher_btn)
        row.addStretch()

        detail_layout.addWidget(self.detail_image)
        detail_layout.addWidget(self.detail_title)
        detail_layout.addWidget(self.detail_meta)
        detail_layout.addWidget(self.detail_content)
        detail_layout.addLayout(row)
        detail_layout.addStretch()

        main_layout.addWidget(detail_container, 1)
        self.content_stack.addWidget(self.detail_view)

    def show_list_view(self):
        self.content_stack.setCurrentWidget(self.list_view)

    def load_quests_from_url(self):
        if self.quest_layout is None:
            return
        try:
            reply = self.network_manager.get(QNetworkRequest(QUrl(self.quest_url)))
            reply.finished.connect(lambda: self.on_quests_loaded(reply))
        except Exception:
            self.create_default_quests()

    def on_quests_loaded(self, reply):
        try:
            if reply.error() == QNetworkReply.NoError:
                data = json.loads(reply.readAll().data().decode('utf-8'))
                self.all_quests = [q for q in data.get('quests', []) if self.validate_quest_item(q)]
                if not self.all_quests:
                    self.create_default_quests()
                    return
            else:
                self.create_default_quests()
                return
        except Exception:
            self.create_default_quests()
            return
        finally:
            reply.deleteLater()

        self.filtered_quests = self.all_quests.copy()
        self.display_quests()

    def validate_quest_item(self, quest):
        required = ['id', 'title', 'date', 'content', 'category', 'image_url']
        return all(field in quest for field in required)

    def create_default_quests(self):
        self.all_quests = [{
            'id': 0,
            'title': 'Misión de Prueba',
            'date': '17/07/2025',
            'content': 'Completa esta misión de prueba para ganar experiencia.',
            'full_content': 'Derrota a un enemigo básico y recoge recursos. Recompensa: 100 EXP.',
            'category': 'Principal',
            'image_url': '',
            'cover_image_url': '',
            'author': 'Maestro de Misiones'
        }]
        self.filtered_quests = self.all_quests.copy()
        self.display_quests()

    def filter_quests(self):
        text = self.search_bar.text().lower()
        cat = self.category_filter.currentText()
        self.filtered_quests = [
            q for q in self.all_quests
            if (not text or text in q.get('title', '').lower() or text in q.get('content', '').lower())
            and (cat == 'Todas' or q.get('category') == cat)
        ]
        self.display_quests()

    def display_quests(self):
        while self.quest_layout.count() > 0:
            item = self.quest_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for quest in self.filtered_quests:
            card = self.create_quest_card(quest)
            card.setGraphicsEffect(self.create_shadow_effect())
            self.quest_layout.addWidget(card)

        self.quest_layout.addStretch()

    def create_shadow_effect(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        return shadow

    def create_quest_card(self, item):
        card = QWidget()
        card.setObjectName("questCard")
        card.setMinimumHeight(130)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        text_col = QVBoxLayout()
        category = QLabel(item.get('category', '').upper())
        category.setStyleSheet("color:#C8A45C;font-size:12px;font-weight:700;")

        title = QLabel(item.get('title', ''))
        title.setStyleSheet("color:#F2F2F2;font-size:18px;font-weight:700;")
        title.setWordWrap(True)

        meta = QLabel(f"{item.get('date','')}  •  Por: {item.get('author', 'Anónimo')}")
        meta.setStyleSheet("color:#B8C1CC;font-size:11px;")

        content = QLabel(item.get('content', ''))
        content.setStyleSheet("color:#B8C1CC;font-size:12px;")
        content.setWordWrap(True)

        btn = QPushButton("Ver Detalle")
        btn.setObjectName("sidebarButton")
        btn.setMinimumWidth(130)
        btn.clicked.connect(lambda: self.show_quest_detail(item))

        text_col.addWidget(category)
        text_col.addWidget(title)
        text_col.addWidget(meta)
        text_col.addWidget(content)
        text_col.addWidget(btn, 0, Qt.AlignLeft)

        image_box = QLabel()
        image_box.setFixedSize(140, 90)
        image_box.setAlignment(Qt.AlignCenter)
        image_box.setStyleSheet("background:#2B3442;border:1px solid #3A4556;border-radius:8px;")
        if item.get('image_url'):
            self.load_image_from_url(item['image_url'], image_box)
        else:
            self.set_placeholder_image(image_box)

        layout.addLayout(text_col, 2)
        layout.addWidget(image_box, 1)
        return card

    def show_quest_detail(self, quest_item):
        self.detail_title.setText(quest_item.get('title', ''))
        self.detail_meta.setText(
            f"{quest_item.get('category', '').upper()}  •  {quest_item.get('date', '')}  •  Por: {quest_item.get('author', 'Anónimo')}"
        )
        self.detail_content.setText(quest_item.get('full_content', quest_item.get('content', '')))

        cover_image_url = quest_item.get('cover_image_url', quest_item.get('image_url', ''))
        if cover_image_url:
            self.load_image_from_url(cover_image_url, self.detail_image, is_cover=True)
        else:
            self.set_placeholder_image(self.detail_image)

        self.update_quest_index(quest_item.get('id'))
        self.content_stack.setCurrentWidget(self.detail_view)

    def update_quest_index(self, selected_id):
        self.quest_index.clear()
        for quest in self.filtered_quests:
            item = QListWidgetItem(quest.get('title', ''))
            item.setData(Qt.UserRole, quest.get('id'))
            self.quest_index.addItem(item)
            if quest.get('id') == selected_id:
                self.quest_index.setCurrentItem(item)

    def on_index_item_clicked(self, item):
        selected_id = item.data(Qt.UserRole)
        for quest in self.all_quests:
            if quest.get('id') == selected_id:
                self.show_quest_detail(quest)
                break

    def load_image_from_url(self, image_url, image_label, is_cover=False):
        if image_url in self.image_cache:
            image_label.setPixmap(self.image_cache[image_url])
            return

        try:
            reply = self.network_manager.get(QNetworkRequest(QUrl(image_url)))
            reply.finished.connect(lambda: self.on_image_loaded(reply, image_label, image_url, is_cover))
        except Exception:
            self.set_placeholder_image(image_label)

    def on_image_loaded(self, reply, image_label, image_url, is_cover):
        try:
            if reply.error() == QNetworkReply.NoError:
                data = reply.readAll().data()
                pixmap = QPixmap()
                pixmap.loadFromData(data)
                if not pixmap.isNull():
                    size = QSize(460, 220) if is_cover else QSize(140, 90)
                    scaled = pixmap.scaled(size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    image_label.setPixmap(scaled)
                    self.image_cache[image_url] = scaled
                    return
        except Exception:
            pass
        finally:
            reply.deleteLater()

        self.set_placeholder_image(image_label)

    def set_placeholder_image(self, image_label):
        image_label.setPixmap(QPixmap())
        image_label.setText('SIN IMAGEN')
        image_label.setStyleSheet(
            "color:#B8C1CC;font-size:11px;font-style:italic;background:#2B3442;border:1px solid #3A4556;border-radius:8px;"
        )