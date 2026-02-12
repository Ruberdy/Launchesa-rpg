import sys
import json
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QLabel, QScrollArea, QPushButton, QLineEdit, QComboBox,
                            QGraphicsDropShadowEffect, QStackedWidget, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, QSize, QTimer, QDate, QUrl
from PyQt5.QtGui import QPixmap, QFont, QIcon, QColor, QFontDatabase
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from io import BytesIO
from quest import QuestPanel

class RPGNewsPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Crónicas del Reino - RPG Legends")
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #e2e8f0);
            }
        """)
        
        # Variables
        self.all_news = []
        self.filtered_news = []
        self.all_events = []
        self.news_url = "https://raw.githubusercontent.com/Ruberdy/FosterGames/main/news_data.json"
        self.events_url = "https://raw.githubusercontent.com/Ruberdy/FosterGames/main/events.json"
        self.categories = ["Todas", "Expansión", "Evento", "Actualización", "Comunidad"]
        self.network_manager = QNetworkAccessManager()
        self.image_cache = {}
        self.news_container = None
        self.news_layout = None
        self.quest_panel = None
        
        # Widget central con QStackedWidget
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)
        
        # Crear vistas
        self.create_news_list_view()
        self.create_news_detail_view()
        self.create_quest_detail_view()
        
        # Mostrar la vista de lista inicialmente
        self.central_widget.setCurrentWidget(self.news_list_widget)
        
        # Cargar datos
        self.load_news_from_url()
        self.load_events_from_url()
        
        # Temporizador para actualizaciones
        self.news_timer = QTimer()
        self.news_timer.timeout.connect(self.load_news_from_url)
        self.news_timer.start(60000)
        
        self.events_timer = QTimer()
        self.events_timer.timeout.connect(self.load_events_from_url)
        self.events_timer.start(60000)
    
    def create_news_list_view(self):
        """Crear vista de lista de noticias"""
        self.news_list_widget = QWidget()
        main_layout = QHBoxLayout(self.news_list_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.create_sidebar(main_layout)
        self.create_main_content(main_layout)
        
        self.central_widget.addWidget(self.news_list_widget)
    
    def create_news_detail_view(self):
        """Crear vista de detalles de noticia"""
        self.news_detail_widget = QWidget()
        detail_main_layout = QHBoxLayout(self.news_detail_widget)
        detail_main_layout.setContentsMargins(15, 15, 15, 15)
        detail_main_layout.setSpacing(10)
        
        self.news_index = QListWidget()
        self.news_index.setMaximumWidth(200)
        self.news_index.setStyleSheet("""
            QListWidget {
                background: #ffffff;
                border: none;
                border-radius: 10px;
                padding: 5px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                color: #1e3a8a;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
            }
            QListWidget::item {
                padding: 8px;
                border: none;
            }
            QListWidget::item:selected {
                background: #3b82f6;
                color: #ffffff;
                border-radius: 6px;
            }
            QListWidget::item:hover {
                background: #f1f5f9;
                border-radius: 6px;
            }
        """)
        self.news_index.itemClicked.connect(self.on_index_item_clicked)
        detail_main_layout.addWidget(self.news_index)
        
        detail_content = QWidget()
        self.detail_layout = QVBoxLayout(detail_content)
        self.detail_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_layout.setSpacing(10)
        
        self.cover_image_label = QLabel()
        self.cover_image_label.setAlignment(Qt.AlignCenter)
        self.cover_image_label.setStyleSheet("""
            QLabel {
                background: #f1f5f9;
                border-radius: 10px;
                border: none;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
            }
        """)
        self.detail_layout.addWidget(self.cover_image_label)
        
        self.detail_title = QLabel()
        self.detail_title.setStyleSheet("""
            QLabel {
                color: #1e3a8a;
                font-size: 24px;
                font-weight: 700;
                font-family: 'Georgia', serif;
                border: none;
            }
        """)
        self.detail_title.setWordWrap(True)
        self.detail_layout.addWidget(self.detail_title)
        
        meta_widget = QWidget()
        meta_layout = QHBoxLayout(meta_widget)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(5)
        
        self.detail_category = QLabel()
        self.detail_category.setStyleSheet("""
            QLabel {
                color: #3b82f6;
                font-size: 12px;
                font-weight: 600;
                font-family: 'Segoe UI', sans-serif;
                border: none;
            }
        """)
        
        self.detail_date = QLabel()
        self.detail_date.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 12px;
                font-style: italic;
                font-family: 'Segoe UI', sans-serif;
                border: none;
            }
        """)
        
        self.detail_author = QLabel()
        self.detail_author.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 12px;
                font-family: 'Segoe UI', sans-serif;
                border: none;
            }
        """)
        
        meta_layout.addWidget(self.detail_category)
        meta_layout.addWidget(self.detail_date)
        meta_layout.addWidget(self.detail_author)
        meta_layout.addStretch()
        self.detail_layout.addWidget(meta_widget)
        
        self.detail_content = QLabel()
        self.detail_content.setStyleSheet("""
            QLabel {
                color: #334155;
                font-size: 13px;
                font-family: 'Segoe UI', sans-serif;
                border: none;
            }
        """)
        self.detail_content.setWordWrap(True)
        self.detail_layout.addWidget(self.detail_content)
        
        back_button = QPushButton("Volver a Crónicas")
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
        back_button.clicked.connect(self.show_news_list)
        self.detail_layout.addWidget(back_button, 0, Qt.AlignLeft)
        
        self.detail_layout.addStretch()
        detail_main_layout.addWidget(detail_content, 1)
        
        self.central_widget.addWidget(self.news_detail_widget)
    
    def create_quest_detail_view(self):
        """Crear vista de detalles de quest"""
        self.quest_detail_widget = QWidget()
        detail_main_layout = QHBoxLayout(self.quest_detail_widget)
        detail_main_layout.setContentsMargins(15, 15, 15, 15)
        detail_main_layout.setSpacing(10)
        
        self.quest_index = QListWidget()
        self.quest_index.setMaximumWidth(200)
        self.quest_index.setStyleSheet("""
            QListWidget {
                background: #ffffff;
                border: none;
                border-radius: 10px;
                padding: 5px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                color: #1e3a8a;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
            }
            QListWidget::item {
                padding: 8px;
                border: none;
            }
            QListWidget::item:selected {
                background: #3b82f6;
                color: #ffffff;
                border-radius: 6px;
            }
            QListWidget::item:hover {
                background: #f1f5f9;
                border-radius: 6px;
            }
        """)
        self.quest_index.itemClicked.connect(self.on_quest_index_clicked)
        detail_main_layout.addWidget(self.quest_index)
        
        detail_content = QWidget()
        self.quest_detail_layout = QVBoxLayout(detail_content)
        self.quest_detail_layout.setContentsMargins(0, 0, 0, 0)
        self.quest_detail_layout.setSpacing(10)
        
        self.quest_cover_image_label = QLabel()
        self.quest_cover_image_label.setAlignment(Qt.AlignCenter)
        self.quest_cover_image_label.setStyleSheet("""
            QLabel {
                background: #f1f5f9;
                border-radius: 10px;
                border: none;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
            }
        """)
        self.quest_detail_layout.addWidget(self.quest_cover_image_label)
        
        self.quest_detail_title = QLabel()
        self.quest_detail_title.setStyleSheet("""
            QLabel {
                color: #1e3a8a;
                font-size: 24px;
                font-weight: 700;
                font-family: 'Georgia', serif;
                border: none;
            }
        """)
        self.quest_detail_title.setWordWrap(True)
        self.quest_detail_layout.addWidget(self.quest_detail_title)
        
        meta_widget = QWidget()
        meta_layout = QHBoxLayout(meta_widget)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(5)
        
        self.quest_detail_category = QLabel()
        self.quest_detail_category.setStyleSheet("""
            QLabel {
                color: #3b82f6;
                font-size: 12px;
                font-weight: 600;
                font-family: 'Segoe UI', sans-serif;
                border: none;
            }
        """)
        
        self.quest_detail_date = QLabel()
        self.quest_detail_date.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 12px;
                font-style: italic;
                font-family: 'Segoe UI', sans-serif;
                border: none;
            }
        """)
        
        self.quest_detail_author = QLabel()
        self.quest_detail_author.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 12px;
                font-family: 'Segoe UI', sans-serif;
                border: none;
            }
        """)
        
        meta_layout.addWidget(self.quest_detail_category)
        meta_layout.addWidget(self.quest_detail_date)
        meta_layout.addWidget(self.quest_detail_author)
        meta_layout.addStretch()
        self.quest_detail_layout.addWidget(meta_widget)
        
        self.quest_detail_content = QLabel()
        self.quest_detail_content.setStyleSheet("""
            QLabel {
                color: #334155;
                font-size: 13px;
                font-family: 'Segoe UI', sans-serif;
                border: none;
            }
        """)
        self.quest_detail_content.setWordWrap(True)
        self.quest_detail_layout.addWidget(self.quest_detail_content)
        
        back_button = QPushButton("Volver a Misiones")
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
        back_button.clicked.connect(self.show_quest_list)
        self.quest_detail_layout.addWidget(back_button, 0, Qt.AlignLeft)
        
        self.quest_detail_layout.addStretch()
        detail_main_layout.addWidget(detail_content, 1)
        
        self.central_widget.addWidget(self.quest_detail_widget)
    
    def show_news_list(self):
        """Volver a la vista de lista de noticias"""
        self.central_widget.setCurrentWidget(self.news_list_widget)
    
    def show_quest_list(self):
        """Volver a la vista de lista de quests"""
        if self.quest_panel is None:
            self.quest_panel = QuestPanel(self)
            self.central_widget.addWidget(self.quest_panel)
        self.central_widget.setCurrentWidget(self.quest_panel)
    
    def show_news_detail(self, news_item):
        """Mostrar detalles de una noticia"""
        self.detail_title.setText(news_item.get("title", ""))
        self.detail_category.setText(news_item.get("category", "").upper())
        self.detail_date.setText(news_item.get("date", ""))
        self.detail_author.setText(f"Por: {news_item.get('author', 'Anónimo')}")
        self.detail_content.setText(news_item.get("full_content", news_item.get("content", "")))
        
        cover_image_url = news_item.get("cover_image_url", news_item.get("image_url", ""))
        if cover_image_url:
            self.load_image_from_url(cover_image_url, self.cover_image_label, is_cover=True)
        else:
            self.set_placeholder_image(self.cover_image_label)
        
        self.update_news_index(news_item.get("id"))
        self.central_widget.setCurrentWidget(self.news_detail_widget)
    
    def update_news_index(self, selected_id):
        """Actualizar el índice de noticias"""
        self.news_index.clear()
        for news in self.filtered_news:
            item = QListWidgetItem(news.get("title", ""))
            item.setData(Qt.UserRole, news.get("id"))
            self.news_index.addItem(item)
            if news.get("id") == selected_id:
                self.news_index.setCurrentItem(item)
    
    def on_index_item_clicked(self, item):
        """Manejar clic en el índice de noticias"""
        selected_id = item.data(Qt.UserRole)
        for news in self.all_news:
            if news.get("id") == selected_id:
                self.show_news_detail(news)
                break
    
    def update_quest_index(self, selected_id):
        """Actualizar el índice de quests"""
        if self.quest_panel:
            quest_panel = self.central_widget.widget(self.central_widget.indexOf(self.quest_panel))
            if quest_panel and hasattr(quest_panel, 'quest_index'):
                quest_panel.quest_index.clear()
                for quest in quest_panel.filtered_quests:
                    item = QListWidgetItem(quest.get("title", ""))
                    item.setData(Qt.UserRole, quest.get("id"))
                    quest_panel.quest_index.addItem(item)
                    if quest.get("id") == selected_id:
                        quest_panel.quest_index.setCurrentItem(item)
    
    def on_quest_index_clicked(self, item):
        """Manejar clic en el índice de quests"""
        selected_id = item.data(Qt.UserRole)
        if self.quest_panel:
            quest_panel = self.central_widget.widget(self.central_widget.indexOf(self.quest_panel))
            if quest_panel:
                for quest in quest_panel.all_quests:
                    if quest.get("id") == selected_id:
                        quest_panel.show_quest_detail(quest)
                        break
    
    def load_news_from_url(self):
        """Cargar noticias desde URL remota"""
        if not hasattr(self, 'news_layout') or self.news_layout is None:
            print("Error: news_layout no está inicializado en load_news_from_url")
            return
        try:
            request = QNetworkRequest(QUrl(self.news_url))
            reply = self.network_manager.get(request)
            reply.finished.connect(lambda: self.on_news_loaded(reply))
        except Exception as e:
            print(f"Error iniciando carga de noticias: {e}")
            self.create_default_news()
    
    def load_events_from_url(self):
        """Cargar eventos desde URL remota"""
        try:
            request = QNetworkRequest(QUrl(self.events_url))
            reply = self.network_manager.get(request)
            reply.finished.connect(lambda: self.on_events_loaded(reply))
        except Exception as e:
            print(f"Error iniciando carga de eventos: {e}")
            self.create_default_events()
    
    def on_news_loaded(self, reply):
        """Procesar respuesta de la carga de noticias"""
        if not hasattr(self, 'news_layout') or self.news_layout is None:
            print("Error: news_layout no está inicializado en on_news_loaded")
            self.create_main_content(self.news_list_widget.layout())
            return
        
        try:
            if reply.error() == QNetworkReply.NoError:
                data = json.loads(reply.readAll().data().decode('utf-8'))
                self.all_news = [
                    news for news in data.get('news', [])
                    if self.validate_news_item(news)
                ]
                self.filtered_news = self.all_news.copy()
                self.display_news()
            else:
                print(f"Error de red (noticias): {reply.errorString()}")
                self.create_default_news()
        except json.JSONDecodeError as e:
            print(f"Error en formato JSON (noticias): {e}")
            self.create_default_news()
        except Exception as e:
            print(f"Error procesando noticias: {e}")
            self.create_default_news()
        finally:
            reply.deleteLater()
    
    def on_events_loaded(self, reply):
        """Procesar respuesta de la carga de eventos"""
        try:
            if reply.error() == QNetworkReply.NoError:
                data = json.loads(reply.readAll().data().decode('utf-8'))
                self.all_events = [
                    event for event in data.get('events', [])
                    if self.validate_event_item(event)
                ]
                self.display_events()
            else:
                print(f"Error de red (eventos): {reply.errorString()}")
                self.create_default_events()
        except json.JSONDecodeError as e:
            print(f"Error en formato JSON (eventos): {e}")
            self.create_default_events()
        except Exception as e:
            print(f"Error procesando eventos: {e}")
            self.create_default_events()
        finally:
            reply.deleteLater()
    
    def validate_news_item(self, news):
        """Validar estructura de item de noticia"""
        required_fields = ['id', 'title', 'date', 'content', 'category', 'image_url']
        return all(field in news for field in required_fields)
    
    def validate_event_item(self, event):
        """Validar estructura de item de evento"""
        required_fields = ['title', 'date', 'color', 'icon', 'description']
        return all(field in event for field in required_fields)
    
    def create_default_news(self):
        """Crear noticias por defecto si falla la carga"""
        if not hasattr(self, 'news_layout') or self.news_layout is None:
            print("Error: news_layout no está inicializado en create_default_news")
            return
        
        self.all_news = [
            {
                "id": 0,
                "title": "Bienvenidos a RPG Legends",
                "date": QDate.currentDate().toString("dd/MM/yyyy"),
                "content": "¡Explora el reino mágico de RPG Legends! Nuevas aventuras te esperan.",
                "full_content": "Bienvenidos al mundo de RPG Legends, donde la magia y la aventura se entrelazan. Explora un reino lleno de misterios, enfréntate a enemigos formidables y forja tu leyenda. ¡Comienza tu viaje hoy!",
                "category": "Comunidad",
                "image_url": "https://raw.githubusercontent.com/Ruberdy/FosterGames/main/images/default.jpg",
                "cover_image_url": "https://raw.githubusercontent.com/Ruberdy/FosterGames/main/images/default_cover.jpg",
                "author": "Equipo RPG"
            }
        ]
        self.filtered_news = self.all_news.copy()
        self.display_news()
    
    def create_default_events(self):
        """Crear eventos por defecto si falla la carga"""
        self.all_events = [
            {
                "title": "TORNEO REAL",
                "date": "Hoy - 20:00",
                "color": "#3b82f6",
                "icon": "tournament",
                "description": "Compite por el trono"
            },
            {
                "title": "INVASIÓN DE DRAGONES",
                "date": "Activo",
                "color": "#ef4444",
                "icon": "dragon",
                "description": "Defiende el reino"
            },
            {
                "title": "FESTIVAL LUNA LLENA",
                "date": "Mañana",
                "color": "#8b5cf6",
                "icon": "moon",
                "description": "Celebra bajo las estrellas"
            }
        ]
        self.display_events()
    
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
                    scaled_size = self.cover_image_label.size() if is_cover else QSize(200, 100)
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
                font-size: 12px;
                font-style: italic;
                font-family: 'Segoe UI', sans-serif;
                text-align: center;
                border: none;
            }
        """)
    
    def create_sidebar(self, main_layout):
        """Crear barra lateral mejorada"""
        sidebar = QWidget()
        sidebar.setFixedWidth(80)
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
        
        # Logo con manejo de error
        logo = QLabel()
        pixmap = QPixmap(":/icons/sword-shield.png")
        if pixmap.isNull():
            print("Error: No se pudo cargar sword-shield.png. Usando placeholder.")
            logo.setText("Logo")
            logo.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-size: 16px;
                    font-weight: 700;
                    font-family: 'Georgia', serif;
                    border: none;
                }
            """)
        else:
            logo.setPixmap(pixmap.scaledToWidth(40, Qt.SmoothTransformation))
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("margin-bottom: 10px; border: none;")
        sidebar_layout.addWidget(logo)
        
        # Botones de navegación
        nav_items = [
            ("home", "Inicio", True),
            ("map", "Mapa", False),
            ("scroll", "Crónicas", False),
            ("quest", "Misiones", False),
            ("guild", "Clanes", False)
        ]
        
        self.sidebar_buttons = []
        
        for icon_name, tooltip, active in nav_items:
            btn = QPushButton()
            btn.setIcon(QIcon(f":/icons/{icon_name}.png"))
            btn.setIconSize(QSize(30, 30))
            btn.setMinimumSize(60, 50)
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.setChecked(active)
            
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(15)
            shadow.setColor(QColor(0, 0, 0, 100))
            shadow.setOffset(0, 2)
            btn.setGraphicsEffect(shadow)
            
            base_style = """
                QPushButton {
                    background: transparent;
                    border-radius: 10px;
                    border: none;
                    padding: 5px;
                    transition: all 0.3s;
                }
                QPushButton:hover {
                    background: rgba(59, 130, 246, 0.4);
                    transform: scale(1.1);
                }
            """
            active_style = """
                QPushButton:checked {
                    background: #3b82f6;
                }
            """ if active else ""
            
            btn.setStyleSheet(base_style + active_style)
            
            if tooltip == "Crónicas":
                btn.clicked.connect(self.show_news_list)
            elif tooltip == "Misiones":
                btn.clicked.connect(self.show_quest_list)
            
            sidebar_layout.addWidget(btn, 0, Qt.AlignHCenter)
            self.sidebar_buttons.append(btn)
        
        sidebar_layout.addStretch()
        
        profile_btn = QPushButton()
        profile_btn.setIcon(QIcon(":/icons/knight.png"))
        profile_btn.setIconSize(QSize(30, 30))
        profile_btn.setMinimumSize(60, 50)
        profile_btn.setToolTip("Mi Personaje")
        profile_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border-radius: 10px;
                border: none;
                padding: 5px;
                transition: all 0.3s;
            }
            QPushButton:hover {
                background: rgba(59, 130, 246, 0.4);
                transform: scale(1.1);
            }
        """)
        profile_btn.setGraphicsEffect(shadow)
        sidebar_layout.addWidget(profile_btn, 0, Qt.AlignHCenter)
        
        main_layout.addWidget(sidebar)
    
    def create_main_content(self, main_layout):
        """Crear contenido principal mejorado"""
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)
        
        # Header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        title = QLabel("CRÓNICAS DEL REINO")
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
        self.search_bar.setPlaceholderText("Buscar en las crónicas...")
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
        self.search_bar.textChanged.connect(self.filter_news)
        
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
        self.category_filter.currentTextChanged.connect(self.filter_news)
        
        search_layout.addWidget(self.search_bar)
        search_layout.addWidget(self.category_filter)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(search_container)
        
        content_layout.addWidget(header)
        
        self.events_scroll = QScrollArea()
        self.events_scroll.setWidgetResizable(True)
        self.events_scroll.setMaximumHeight(100)  # Límite máximo de altura
        self.events_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # Deshabilitar scroll horizontal
        self.events_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # Deshabilitar scroll vertical
        self.events_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:horizontal {
                background: #f1f5f9;
                height: 0;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 0;
                border: none;
            }
        """)
        
        self.events_container = QWidget()
        self.events_layout = QHBoxLayout(self.events_container)
        self.events_layout.setContentsMargins(5, 5, 5, 5)
        self.events_layout.setSpacing(5)
        
        self.events_scroll.setWidget(self.events_container)
        content_layout.addWidget(self.events_scroll)
        
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
        
        self.news_container = QWidget()
        self.news_layout = QVBoxLayout(self.news_container)
        self.news_layout.setContentsMargins(0, 0, 0, 0)
        self.news_layout.setSpacing(10)
        
        self.scroll.setWidget(self.news_container)
        content_layout.addWidget(self.scroll)
        
        main_layout.addWidget(content)
    
    def filter_news(self):
        """Filtrar noticias por búsqueda y categoría"""
        if not hasattr(self, 'news_layout') or self.news_layout is None:
            print("Error: news_layout no está inicializado en filter_news")
            return
        
        search_text = self.search_bar.text().lower()
        category = self.category_filter.currentText()
        
        self.filtered_news = [
            news for news in self.all_news
            if (not search_text or
                search_text in news.get('title', '').lower() or
                search_text in news.get('content', '').lower() or
                search_text in news.get('category', '').lower()) and
            (category == "Todas" or news.get('category') == category)
        ]
        self.display_news()
    
    def display_news(self):
        """Mostrar noticias con animaciones"""
        if not hasattr(self, 'news_layout') or self.news_layout is None:
            print("Error: news_layout no está inicializado en display_news")
            return
        
        while self.news_layout.count() > 0:
            item = self.news_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        
        for item in self.filtered_news:
            news_card = self.create_news_card(item)
            news_card.setGraphicsEffect(self.create_shadow_effect())
            self.news_layout.addWidget(news_card)
        
        self.news_layout.addStretch()
    
    def display_events(self):
        """Mostrar eventos destacados, distribuyendo 3 a lo largo del ancho"""
        while self.events_layout.count() > 0:
            item = self.events_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        
        # Limitar a los primeros 3 eventos para mostrar
        events_to_display = self.all_events[:3]
        if events_to_display:
            # Calcular el ancho disponible y dividir entre 3
            total_width = self.events_container.width() - (len(events_to_display) - 1) * self.events_layout.spacing() - self.events_layout.contentsMargins().left() - self.events_layout.contentsMargins().right()
            card_width = total_width // len(events_to_display)
            
            for event in events_to_display:
                event_card = self.create_event_card(event, card_width)
                event_card.setGraphicsEffect(self.create_shadow_effect())
                self.events_layout.addWidget(event_card)
        
        self.events_layout.addStretch()
    
    def create_shadow_effect(self):
        """Crear efecto de sombra para tarjetas"""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        return shadow
    
    def create_event_card(self, event, card_width):
        """Crear tarjeta de evento con ancho ajustable"""
        event_card = QWidget()
        event_card.setMinimumHeight(70)
        event_card.setMinimumWidth(card_width)  # Ajustar ancho dinámicamente
        event_card.setStyleSheet(f"""
            QWidget {{
                background: #ffffff;
                border-radius: 8px;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
                border: none;
            }}
            QWidget:hover {{
                background: #f8fafc;
                transform: scale(1.03);
                transition: all 0.3s;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
            }}
        """)
        
        card_layout = QHBoxLayout(event_card)
        card_layout.setContentsMargins(5, 5, 5, 5)
        card_layout.setSpacing(5)
        
        icon = QLabel()
        pixmap = QPixmap(f":/icons/{event['icon']}.png")
        if pixmap.isNull():
            icon.setText("Icon")
            icon.setStyleSheet("color: #64748b; font-size: 12px;")
        else:
            icon.setPixmap(pixmap.scaled(25, 25, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon.setStyleSheet("border: none;")
        
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        
        title = QLabel(event["title"])
        title.setStyleSheet(f"""
            QLabel {{
                color: {event['color']};
                font-size: 14px;  /* Aumentar tamaño de fuente */
                font-weight: 600;
                font-family: 'Georgia', serif;
                border: none;
            }}
        """)
        
        date = QLabel(event["date"])
        date.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 11px;  /* Aumentar tamaño de fuente */
                font-family: 'Segoe UI', sans-serif;
                border: none;
            }
        """)
        
        desc = QLabel(event["description"])
        desc.setStyleSheet("""
            QLabel {
                color: #475569;
                font-size: 11px;  /* Aumentar tamaño de fuente */
                font-style: italic;
                font-family: 'Segoe UI', sans-serif;
                border: none;
            }
        """)
        
        text_layout.addWidget(title)
        text_layout.addWidget(date)
        text_layout.addWidget(desc)
        text_layout.addStretch()
        
        card_layout.addWidget(icon)
        card_layout.addWidget(text_widget, 1)  # Expandir el texto para llenar el espacio
        
        return event_card
    
    def create_news_card(self, item):
        """Crear tarjeta de noticia mejorada"""
        card = QWidget()
        card.setMinimumHeight(140)
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
        
        btn = QPushButton("Leer Crónica")
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
        btn.clicked.connect(lambda: self.show_news_detail(item))
        
        text_layout.addWidget(category)
        text_layout.addWidget(title)
        text_layout.addWidget(meta)
        text_layout.addWidget(content)
        text_layout.addWidget(btn, 0, Qt.AlignLeft)
        text_layout.addStretch()
        
        image_container = QWidget()
        image_container.setMinimumSize(150, 80)
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

    @staticmethod
    def get_news_data():
        """Devolver las noticias cargadas o predeterminadas"""
        instance = RPGNewsPanel()
        if not instance.all_news:
            instance.create_default_news()
        return instance.all_news

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("QWidget { border: none; }")
    
    font_db = QFontDatabase()
    font_db.addApplicationFont(":/fonts/SegoeUI.ttf")
    font_db.addApplicationFont(":/fonts/Georgia.ttf")
    
    app.setFont(QFont("Segoe UI", 10))
    
    window = RPGNewsPanel()
    window.show()
    sys.exit(app.exec_())