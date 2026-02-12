import sys
import json
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
                            QPushButton, QLineEdit, QComboBox, QGraphicsDropShadowEffect,
                            QStackedWidget, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, QSize, QUrl
from PyQt5.QtGui import QPixmap, QFont, QColor
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from io import BytesIO

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
        self.quest_container = None
        self.quest_layout = None
        
        # Layout principal
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.create_sidebar(main_layout)
        self.create_main_content(main_layout)
        
        # Cargar quests
        self.load_quests_from_url()
    
    def create_sidebar(self, main_layout):
        """Crear barra lateral para Quest"""
        sidebar = QWidget()
        sidebar.setFixedWidth(80)  # Reducido para mejor visualización
        sidebar.setStyleSheet("""
            QWidget {
                background: #1e40af;
                border: none;
            }
        """)
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 10, 0, 10)
        sidebar_layout.setSpacing(10)
        sidebar_layout.setAlignment(Qt.AlignTop)
        
        # Logo
        logo = QLabel()
        logo.setPixmap(QPixmap(":/icons/quest.png").scaledToWidth(40, Qt.SmoothTransformation))
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("margin-bottom: 10px; border: none;")
        sidebar_layout.addWidget(logo)
        
        main_layout.addWidget(sidebar)
    
    def create_main_content(self, main_layout):
        """Crear contenido principal de Quest"""
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(15)
        
        # Header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        title = QLabel("MISIONES ÉPICAS")
        title.setStyleSheet("""
            QLabel {
                color: #1e3a8a;
                font-size: 24px;
                font-weight: 700;
                font-family: 'Georgia', serif;
                letter-spacing: 1px;
                border: none;
            }
        """)
        
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setSpacing(10)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Buscar misiones...")
        self.search_bar.setMinimumHeight(30)
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 0 10px;
                color: #1e3a8a;
                font-size: 12px;
                font-family: 'Segoe UI', sans-serif;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
            }
            QLineEdit:focus {
                box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
            }
        """)
        self.search_bar.textChanged.connect(self.filter_quests)
        
        self.category_filter = QComboBox()
        self.category_filter.addItems(self.categories)
        self.category_filter.setMinimumWidth(150)
        self.category_filter.setMinimumHeight(30)
        self.category_filter.setStyleSheet("""
            QComboBox {
                background: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 0 10px;
                color: #1e3a8a;
                font-size: 12px;
                font-family: 'Segoe UI', sans-serif;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(:/icons/chevron-down.png);
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background: #ffffff;
                border: none;
                selection-background-color: #3b82f6;
                color: #1e3a8a;
            }
        """)
        self.category_filter.currentTextChanged.connect(self.filter_quests)
        
        search_layout.addWidget(self.search_bar)
        search_layout.addWidget(self.category_filter)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(search_container)
        
        content_layout.addWidget(header)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #f1f5f9;
                width: 8px;
                margin: 0 2px 0 2px;
                border-radius: 4px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #3b82f6;
                min-height: 20px;
                border-radius: 4px;
                border: none;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
                border: none;
            }
        """)
        
        self.quest_container = QWidget()
        self.quest_layout = QVBoxLayout(self.quest_container)
        self.quest_layout.setContentsMargins(0, 0, 0, 0)
        self.quest_layout.setSpacing(10)
        
        self.scroll.setWidget(self.quest_container)
        content_layout.addWidget(self.scroll)
        
        # Botón de regreso al inicio
        back_button = QPushButton("Volver al Inicio")
        back_button.setMinimumWidth(120)
        back_button.setMinimumHeight(30)
        back_button.setStyleSheet("""
            QPushButton {
                background: #3b82f6;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 12px;
                font-family: 'Segoe UI', sans-serif;
                padding: 5px;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
            }
            QPushButton:hover {
                background: #2563eb;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
                transform: scale(1.05);
                transition: all 0.3s;
            }
        """)
        back_button.clicked.connect(self.parent.show_news_list)
        content_layout.addWidget(back_button, 0, Qt.AlignLeft)
        
        content_layout.addStretch()
        main_layout.addWidget(content)
    
    def load_quests_from_url(self):
        """Cargar quests desde URL remota"""
        if not hasattr(self, 'quest_layout') or self.quest_layout is None:
            print("Error: quest_layout no está inicializado en load_quests_from_url")
            return
        try:
            request = QNetworkRequest(QUrl(self.quest_url))
            reply = self.network_manager.get(request)
            reply.finished.connect(lambda: self.on_quests_loaded(reply))
        except Exception as e:
            print(f"Error iniciando carga de quests: {e}")
            self.create_default_quests()
    
    def on_quests_loaded(self, reply):
        """Procesar respuesta de la carga de quests"""
        if not hasattr(self, 'quest_layout') or self.quest_layout is None:
            print("Error: quest_layout no está inicializado en on_quests_loaded")
            return
        
        try:
            if reply.error() == QNetworkReply.NoError:
                data = reply.readAll().data().decode('utf-8')
                print(f"Datos recibidos: {data}")
                data = json.loads(data)
                self.all_quests = [
                    quest for quest in data.get('quests', [])
                    if self.validate_quest_item(quest)
                ]
                self.filtered_quests = self.all_quests.copy()
                self.display_quests()
            else:
                print(f"Error de red (quests): {reply.errorString()}")
                self.create_default_quests()
        except json.JSONDecodeError as e:
            print(f"Error en formato JSON (quests): {e}, Datos: {reply.readAll().data().decode('utf-8')}")
            self.create_default_quests()
        except Exception as e:
            print(f"Error procesando quests: {e}")
            self.create_default_quests()
        finally:
            reply.deleteLater()
    
    def validate_quest_item(self, quest):
        """Validar estructura de item de quest"""
        required_fields = ['id', 'title', 'date', 'content', 'category', 'image_url']
        return all(field in quest for field in required_fields)
    
    def create_default_quests(self):
        """Crear quests por defecto si falla la carga"""
        if not hasattr(self, 'quest_layout') or self.quest_layout is None:
            print("Error: quest_layout no está inicializado en create_default_quests")
            return
        
        self.all_quests = [
            {
                "id": 0,
                "title": "Misión de Prueba",
                "date": "17/07/2025",
                "content": "Completa esta misión de prueba para ganar experiencia.",
                "full_content": "Esta es una misión de prueba diseñada para ayudarte a familiarizarte con el sistema. Derrota a un enemigo básico y recoge recursos. ¡Recompensa: 100 puntos de experiencia!",
                "category": "Principal",
                "image_url": "https://raw.githubusercontent.com/Ruberdy/FosterGames/main/images/default.jpg",
                "cover_image_url": "https://raw.githubusercontent.com/Ruberdy/FosterGames/main/images/default_cover.jpg",
                "author": "Maestro de Misiones"
            }
        ]
        self.filtered_quests = self.all_quests.copy()
        self.display_quests()
    
    def filter_quests(self):
        """Filtrar quests por búsqueda y categoría"""
        if not hasattr(self, 'quest_layout') or self.quest_layout is None:
            print("Error: quest_layout no está inicializado en filter_quests")
            return
        
        search_text = self.search_bar.text().lower()
        category = self.category_filter.currentText()
        
        self.filtered_quests = [
            quest for quest in self.all_quests
            if (not search_text or
                search_text in quest.get('title', '').lower() or
                search_text in quest.get('content', '').lower() or
                search_text in quest.get('category', '').lower()) and
            (category == "Todas" or quest.get('category') == category)
        ]
        self.display_quests()
    
    def display_quests(self):
        """Mostrar quests con animaciones"""
        if not hasattr(self, 'quest_layout') or self.quest_layout is None:
            print("Error: quest_layout no está inicializado en display_quests")
            return
        
        while self.quest_layout.count() > 0:
            item = self.quest_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        
        for item in self.filtered_quests:
            quest_card = self.create_quest_card(item)
            quest_card.setGraphicsEffect(self.create_shadow_effect())
            self.quest_layout.addWidget(quest_card)
        
        self.quest_layout.addStretch()
    
    def create_shadow_effect(self):
        """Crear efecto de sombra para tarjetas"""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        return shadow
    
    def create_quest_card(self, item):
        """Crear tarjeta de quest"""
        card = QWidget()
        card.setMinimumHeight(120)
        card.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border-radius: 8px;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
                border: none;
            }
            QWidget:hover {
                background: #f8fafc;
                transform: scale(1.02);
                transition: all 0.3s;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
            }
        """)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        card_layout.setSpacing(10)
        
        text_content = QWidget()
        text_layout = QVBoxLayout(text_content)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(5)
        
        category = QLabel(item.get("category", "").upper())
        category.setStyleSheet("""
            QLabel {
                color: #3b82f6;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 1px;
                font-family: 'Segoe UI', sans-serif;
                border: none;
            }
        """)
        
        title = QLabel(item.get("title", ""))
        title.setStyleSheet("""
            QLabel {
                color: #1e3a8a;
                font-size: 18px;
                font-weight: 700;
                font-family: 'Georgia', serif;
                border: none;
            }
        """)
        title.setWordWrap(True)
        
        meta = QWidget()
        meta_layout = QHBoxLayout(meta)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(5)
        
        date = QLabel(item.get("date", ""))
        date.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 11px;
                font-style: italic;
                font-family: 'Segoe UI', sans-serif;
                border: none;
            }
        """)
        
        author = QLabel(f"Por: {item.get('author', 'Anónimo')}")
        author.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 11px;
                font-family: 'Segoe UI', sans-serif;
                border: none;
            }
        """)
        
        meta_layout.addWidget(date)
        meta_layout.addWidget(author)
        meta_layout.addStretch()
        
        content = QLabel(item.get("content", ""))
        content.setStyleSheet("""
            QLabel {
                color: #334155;
                font-size: 12px;
                font-family: 'Segoe UI', sans-serif;
                border: none;
            }
        """)
        content.setWordWrap(True)
        
        btn = QPushButton("Ver Detalle")
        btn.setMinimumWidth(120)
        btn.setMinimumHeight(30)
        btn.setStyleSheet("""
            QPushButton {
                background: #3b82f6;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 11px;
                font-family: 'Segoe UI', sans-serif;
                padding: 5px;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
            }
            QPushButton:hover {
                background: #2563eb;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
                transform: scale(1.05);
                transition: all 0.3s;
            }
        """)
        btn.clicked.connect(lambda: self.show_quest_detail(item))
        
        text_layout.addWidget(category)
        text_layout.addWidget(title)
        text_layout.addWidget(meta)
        text_layout.addWidget(content)
        text_layout.addWidget(btn, 0, Qt.AlignLeft)
        text_layout.addStretch()
        
        image_container = QWidget()
        image_container.setMinimumSize(120, 60)
        image_container.setStyleSheet("""
            QWidget {
                background: #f1f5f9;
                border-radius: 8px;
                border: none;
            }
        """)
        
        image_layout = QVBoxLayout(image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setAlignment(Qt.AlignCenter)
        
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)
        
        if item.get("image_url"):
            self.load_image_from_url(item["image_url"], image_label)
        else:
            self.set_placeholder_image(image_label)
        
        image_layout.addWidget(image_label)
        
        card_layout.addWidget(text_content, 2)
        card_layout.addWidget(image_container, 1)
        
        return card
    
    def load_image_from_url(self, image_url, image_label, is_cover=False):
        """Cargar imagen desde URL"""
        if image_url in self.image_cache:
            image_label.setPixmap(self.image_cache[image_url])
            return
        
        try:
            request = QNetworkRequest(QUrl(image_url))
            reply = self.network_manager.get(request)
            reply.finished.connect(lambda: self.on_image_loaded(reply, image_label, image_url, is_cover))
        except Exception as e:
            print(f"Error cargando imagen: {e}")
            self.set_placeholder_image(image_label)
    
    def on_image_loaded(self, reply, image_label, image_url, is_cover):
        """Procesar imagen cargada"""
        try:
            if reply.error() == QNetworkReply.NoError:
                data = reply.readAll().data()
                pixmap = QPixmap()
                pixmap.loadFromData(data)
                if not pixmap.isNull():
                    scaled_size = self.parent.quest_cover_image_label.size() if is_cover else QSize(100, 50)
                    scaled_pixmap = pixmap.scaled(scaled_size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    image_label.setPixmap(scaled_pixmap)
                    self.image_cache[image_url] = scaled_pixmap
                else:
                    self.set_placeholder_image(image_label)
            else:
                self.set_placeholder_image(image_label)
        except Exception as e:
            print(f"Error procesando imagen: {e}")
            self.set_placeholder_image(image_label)
        finally:
            reply.deleteLater()
    
    def set_placeholder_image(self, image_label):
        """Establecer imagen de marcador de posición"""
        image_label.setPixmap(QPixmap())
        image_label.setText("SIN IMAGEN")
        image_label.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                font-size: 10px;
                font-style: italic;
                font-family: 'Segoe UI', sans-serif;
                text-align: center;
                border: none;
            }
        """)
    
    def show_quest_detail(self, quest_item):
        """Mostrar detalles de una quest"""
        if not hasattr(self.parent, 'quest_detail_widget') or self.parent.quest_detail_widget is None:
            self.parent.create_quest_detail_view()
        
        self.parent.quest_detail_title.setText(quest_item.get("title", ""))
        self.parent.quest_detail_category.setText(quest_item.get("category", "").upper())
        self.parent.quest_detail_date.setText(quest_item.get("date", ""))
        self.parent.quest_detail_author.setText(f"Por: {quest_item.get('author', 'Anónimo')}")
        self.parent.quest_detail_content.setText(quest_item.get("full_content", quest_item.get("content", "")))
        
        cover_image_url = quest_item.get("cover_image_url", quest_item.get("image_url", ""))
        if cover_image_url:
            self.load_image_from_url(cover_image_url, self.parent.quest_cover_image_label, is_cover=True)
        else:
            self.set_placeholder_image(self.parent.quest_cover_image_label)
        
        self.parent.update_quest_index(quest_item.get("id"))
        self.parent.central_widget.setCurrentWidget(self.parent.quest_detail_widget)