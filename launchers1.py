import sys
import os
import requests
import zipfile
import threading
import subprocess
import socket
import time
import json
import hashlib
import random
from packaging import version
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QProgressBar, QTextBrowser, QFrame, 
                            QMessageBox, QMenu, QSizePolicy, QStackedWidget, QGraphicsDropShadowEffect,
                            QListWidget, QListWidgetItem, QLineEdit, QComboBox, QGroupBox)
from PyQt5.QtCore import Qt, QTimer, QUrl, QSize, QObject, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint
from PyQt5.QtGui import QPixmap, QFont, QDesktopServices, QIcon, QColor, QLinearGradient, QPainter, QFontDatabase

# Importar módulos existentes
try:
    from news import RPGNewsPanel
    from quest import QuestPanel
except ImportError:
    print("Advertencia: No se pudieron importar news.py o quest.py")

# Configuración
CONFIG_PATH = "launcher.json"

def read_config():
    config = {}
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error reading {CONFIG_PATH}: {e}")
        config = {
            "REMOTE_VERSION_URL": "https://example.com/version.json",
            "REMOTE_ZIP_URL": "https://example.com/updates/version.zip",
            "REMOTE_NEWS_URL": "https://example.com/news.html",
            "REMOTE_NOTES_URL": "https://example.com/notes.html",
            "DISCORD_URL": "https://discord.gg/example",
            "LOCAL_VERSION_PATH": "version.json",
            "ZIP_DEST": "update.zip",
            "GAME_EXECUTABLE": "game.exe",
            "BACKGROUND_IMAGE_PATH": "background.jpg",
            "GAME_INSTALLER_URL": "https://example.com/game_installer.zip",
            "LOGO_IMAGE_PATH": "logo.png",
            "SERVER_STATUS_URL": "https://api.example.com/status"
        }
    return config

config = read_config()

# Asignar valores de configuración
REMOTE_VERSION_URL = config.get("REMOTE_VERSION_URL", "")
REMOTE_ZIP_URL = config.get("REMOTE_ZIP_URL", "")
REMOTE_NEWS_URL = config.get("REMOTE_NEWS_URL", "")
REMOTE_NOTES_URL = config.get("REMOTE_NOTES_URL", "")
DISCORD_URL = config.get("DISCORD_URL", "")
LOCAL_VERSION_PATH = config.get("LOCAL_VERSION_PATH", "")
ZIP_DEST = config.get("ZIP_DEST", "")
GAME_EXECUTABLE = config.get("GAME_EXECUTABLE", "")
BACKGROUND_IMAGE_PATH = config.get("BACKGROUND_IMAGE_PATH", "")
GAME_INSTALLER_URL = config.get("GAME_INSTALLER_URL", "")
LOGO_IMAGE_PATH = config.get("LOGO_IMAGE_PATH", "")
SERVER_STATUS_URL = config.get("SERVER_STATUS_URL", "")

class WorkerSignals(QObject):
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, str, str)
    error_signal = pyqtSignal(str)
    news_loaded = pyqtSignal(str)
    version_checked = pyqtSignal(list, str)
    download_complete = pyqtSignal(str)
    extraction_complete = pyqtSignal()
    install_complete = pyqtSignal()
    update_info_ready = pyqtSignal(str)
    connection_status = pyqtSignal(bool)
    game_install_progress = pyqtSignal(int, str, str)
    game_install_status = pyqtSignal(str)
    server_status_updated = pyqtSignal(dict)
    extraction_progress = pyqtSignal(str, str)  # Nuevo: para mostrar archivos extraídos

class ModernGameLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Eliminar la barra de título nativa y hacer fondo translúcido
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        
        # Variables de control
        self.available_updates = []
        self.update_sizes = {}
        self.downloading = False
        self.pause_download = False
        self.installing_game = False
        self.server_status = {"online": False, "players": 0, "uptime": "0h"}
        self.current_version = "0.0.0"
        self.latest_version = "0.0.0"
        
        # Configuración de la ventana
        self.setWindowTitle("FosterGames RPG MAKER Launcher")
        self.setFixedSize(1200, 800)
        
        if os.path.exists("icons/sword-shield.png"):
            self.setWindowIcon(QIcon("icons/sword-shield.png"))
        elif os.path.exists(LOGO_IMAGE_PATH):
            self.setWindowIcon(QIcon(LOGO_IMAGE_PATH))
        
        # Widget principal
        self.central_widget = QWidget()
        self.central_widget.setObjectName("centralRoot")
        self.setCentralWidget(self.central_widget)
        
        # Layout principal
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Panel principal con diseño MMORPG
        self.main_panel = QWidget()
        self.main_panel.setObjectName("mainPanel")
        self.setup_styles()

        
        panel_layout = QVBoxLayout(self.main_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)
        
        # Header con controles de ventana
        self.setup_custom_titlebar(panel_layout)
        
        # Contenido principal con stacked widget
        self.content_stack = QStackedWidget()
        panel_layout.addWidget(self.content_stack)
        
        # Crear diferentes páginas
        self.setup_main_page()
        self.setup_news_page()
        self.setup_quests_page()
        self.setup_settings_page()
        
        self.main_layout.addWidget(self.main_panel)
        
        # Configurar señales
        self.worker_signals = WorkerSignals()
        self._connect_signals()
        
        # Inicializar
        self.load_local_version()
        self.update_connection_status()
        self.load_news()
        self.check_updates()
        self.check_server_status()

    def setup_styles(self):
        """Configurar estilo global oscuro (inspiración Black Desert Remastered)."""
        style = """
        /*
            Paleta base (HEX):
            - Fondo principal: #1F2630, #2B3442
            - Paneles/widgets: #2E3746, #3A4556
            - Texto: #F2F2F2, #B8C1CC
            - Botones: #5C6778 (normal), #6D7A8E (hover)
            - Detalle metálico dorado (opcional): #C8A45C
        */

        QWidget {
            color: #F2F2F2;
            font-family: 'Segoe UI';
        }

        #mainPanel {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #1F2630, stop:0.45 #2B3442, stop:1 #1F2630);
            border-radius: 0px;
            border: 1px solid #4A576B;
        }

        #titleBar {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #2E3746, stop:0.5 #3A4556, stop:1 #2E3746);
            border-top-left-radius: 0px;
            border-top-right-radius: 0px;
            color: #F2F2F2;
            border-bottom: 1px solid #C8A45C;
        }

        #titleBar QWidget,
        #titleBar QLabel {
            background-color: transparent;
            background: transparent;
            border: none;
        }

        #logoLabel {
            min-width: 32px;
            max-width: 32px;
            min-height: 32px;
            max-height: 32px;
            background-color: transparent;
            background: transparent;
            border: none;
            image: none;
        }

        #contentPanel {
            background-color: #263140;
            border: 1px solid #3A4556;
            border-radius: 12px;
            padding: 10px;
        }

        #topInfoBar {
            background: #222c3a;
            border: 1px solid #3A4556;
            border-radius: 8px;
        }

        #heroCard {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #2B3442, stop:1 #323D4D);
            border: 1px solid #46556B;
            border-radius: 10px;
        }

        #heroTitle {
            color: #C8A45C;
            font-size: 34px;
            font-weight: 700;
        }

        #heroSub {
            color: #B8C1CC;
            font-size: 14px;
        }

        #rightRail {
            background: transparent;
        }

        QGroupBox {
            color: #F2F2F2;
            font-size: 14px;
            font-weight: bold;
            border: 1px solid #3A4556;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
            background: #2E3746;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 6px;
            background: #2B3442;
            color: #B8C1CC;
        }

        QLabel {
            color: #F2F2F2;
        }

        #playButton {
            background-color: #5C6778;
            color: #F2F2F2;
            border: 1px solid #6D7A8E;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            padding: 15px 12px;
            min-height: 56px;
        }
        #playButton:hover {
            background-color: #6D7A8E;
            border: 1px solid #C8A45C;
        }
        #playButton:pressed {
            background-color: #4F5968;
        }
        #playButton:disabled {
            background: #3A4556;
            color: #7E8999;
            border: 1px solid #485466;
        }

        #actionButton {
            background-color: #3A4556;
            color: #F2F2F2;
            border: 1px solid #5C6778;
            border-radius: 8px;
            font-size: 12px;
            font-weight: bold;
            padding: 10px;
        }
        #actionButton:hover {
            background-color: #5C6778;
            border: 1px solid #6D7A8E;
        }
        #actionButton:disabled {
            background: #2E3746;
            color: #7E8999;
            border: 1px solid #485466;
        }

        QProgressBar, #progressBar {
            border: 1px solid #5C6778;
            border-radius: 8px;
            text-align: center;
            color: #F2F2F2;
            background: #2B3442;
            height: 20px;
        }
        QProgressBar::chunk, #progressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #5C6778, stop:1 #6D7A8E);
            border-radius: 6px;
        }

        #statusLabel {
            color: #F2F2F2;
            font-size: 12px;
            padding: 8px;
            background: #2E3746;
            border-radius: 6px;
            border: 1px solid #3A4556;
        }

        QTextBrowser {
            background: #2B3442;
            border: 1px solid #3A4556;
            border-radius: 6px;
            color: #B8C1CC;
            font-size: 12px;
            padding: 8px;
        }

        #newsDisplay {
            background: #2D3748;
            border: 1px solid #46556B;
            border-radius: 8px;
            padding: 12px;
        }

        QLineEdit, QComboBox, QListWidget {
            background-color: #2E3746;
            border: 1px solid #3A4556;
            border-radius: 6px;
            color: #F2F2F2;
            padding: 6px;
        }
        """
        self.main_panel.setStyleSheet(style)

    def setup_custom_titlebar(self, parent_layout):
        """Barra de título personalizada con capacidad de arrastre"""
        titlebar = QWidget()
        titlebar.setFixedHeight(40)
        titlebar.setObjectName("titleBar")
        # Conectar eventos de mouse para arrastrar
        titlebar.mousePressEvent = self.titlebar_mouse_press
        titlebar.mouseMoveEvent = self.titlebar_mouse_move
        
        title_layout = QHBoxLayout(titlebar)
        title_layout.setContentsMargins(15, 0, 15, 0)
        
        # Logo y título
        logo_title = QWidget()
        logo_layout = QHBoxLayout(logo_title)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        
        self.logo_label = QLabel()
        self.logo_label.setObjectName("logoLabel")
        logo_path = "icons/sword-shield.png" if os.path.exists("icons/sword-shield.png") else ""
        pixmap = QPixmap(logo_path) if logo_path else QPixmap()
        if not pixmap.isNull():
            self.logo_label.setPixmap(pixmap.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.logo_label.setText("⚔️")
            self.logo_label.setStyleSheet("font-size: 20px; color: #F2F2F2;")
        
        title_label = QLabel("FOSTER GAMES RPG MAKER MZ")
        title_label.setStyleSheet("color: #F2F2F2; font-size: 14px; font-weight: bold;")
        
        logo_layout.addWidget(self.logo_label)
        logo_layout.addWidget(title_label)
        logo_layout.addStretch()
        
        # Estado de conexión
        self.connection_status = QLabel("● Conectado")
        self.connection_status.setStyleSheet("color: #B8C1CC; font-weight: bold; font-size: 12px;")
        
        # Botones de control de ventana
        control_widget = QWidget()
        control_layout = QHBoxLayout(control_widget)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(5)
        
        min_btn = QPushButton("─")
        min_btn.setFixedSize(25, 25)
        min_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.2);
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background: #5C6778; }
        """)
        min_btn.clicked.connect(self.showMinimized)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(25, 25)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.2);
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background: #6D7A8E; }
        """)
        close_btn.clicked.connect(self.close)
        
        control_layout.addWidget(self.connection_status)
        control_layout.addWidget(min_btn)
        control_layout.addWidget(close_btn)
        
        title_layout.addWidget(logo_title)
        title_layout.addStretch()
        title_layout.addWidget(control_widget)
        
        parent_layout.addWidget(titlebar)

    def titlebar_mouse_press(self, event):
        """Manejar presión del mouse en la barra de título"""
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.globalPos()
            event.accept()

    def titlebar_mouse_move(self, event):
        """Manejar movimiento del mouse para arrastrar ventana"""
        if event.buttons() == Qt.LeftButton and hasattr(self, 'drag_start_position'):
            delta = event.globalPos() - self.drag_start_position
            self.move(self.pos() + delta)
            self.drag_start_position = event.globalPos()
            event.accept()

    def setup_main_page(self):
        """Página principal del launcher con estructura inspirada en Black Desert."""
        self.main_page = QWidget()
        layout = QVBoxLayout(self.main_page)
        layout.setContentsMargins(24, 16, 24, 18)
        layout.setSpacing(12)

        # Barra superior informativa (similar a launcher de referencia)
        top_bar = QWidget()
        top_bar.setObjectName("topInfoBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(14, 6, 14, 6)

        links = QLabel("Página oficial   |   Noticias   |   Soporte   |   Centro de Seguridad")
        links.setStyleSheet("color: #B8C1CC; font-size: 11px;")
        version_tag = QLabel("VER 1.29.3")
        version_tag.setStyleSheet("color: #B8C1CC; font-size: 11px; font-weight: bold;")
        top_layout.addWidget(links)
        top_layout.addStretch()
        top_layout.addWidget(version_tag)
        layout.addWidget(top_bar)

        # Hero principal
        hero = QFrame()
        hero.setObjectName("heroCard")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(22, 18, 22, 18)

        hero_title = QLabel("🏰 RPG MAKER GAME LAUNCHER")
        hero_title.setObjectName("heroTitle")
        hero_sub = QLabel("Embárcate en una aventura épica · Tu leyenda comienza aquí")
        hero_sub.setObjectName("heroSub")
        hero_layout.addWidget(hero_title)
        hero_layout.addWidget(hero_sub)

        layout.addWidget(hero)

        # Contenido principal estructurado en dos columnas
        content_panel = QWidget()
        content_panel.setObjectName("contentPanel")
        content_layout = QHBoxLayout(content_panel)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(16)

        # Columna izquierda: estado y crónicas
        left_panel = self.create_status_panel()
        content_layout.addWidget(left_panel, 2)

        # Columna derecha: controles de juego
        right_panel = self.create_game_control_panel()
        right_panel.setObjectName("rightRail")
        content_layout.addWidget(right_panel, 1)

        layout.addWidget(content_panel)

        # Footer con estadísticas
        footer = self.create_footer()
        layout.addWidget(footer)

        self.content_stack.addWidget(self.main_page)

    def create_status_panel(self):
        """Panel de estado del servidor y noticias"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)
        
        # Estado del servidor
        status_group = QGroupBox("🛡️ ESTADO DEL REINO")
        status_layout = QVBoxLayout(status_group)
        
        # Grid de estadísticas
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setSpacing(10)
        
        self.stats_data = [
            ("Estado del Servidor", "CONECTADO", "#10b981"),
            ("Jugadores Online", "1,247", "#fbbf24"),
            ("Tiempo Activo", "15d 8h", "#8b5cf6"),
            ("Ping", "42ms", "#60a5fa")
        ]
        
        self.stat_widgets = []
        for title, value, color in self.stats_data:
            stat_widget = QWidget()
            stat_layout_inner = QVBoxLayout(stat_widget)
            stat_layout_inner.setAlignment(Qt.AlignCenter)
            
            title_label = QLabel(title)
            title_label.setStyleSheet(f"color: #B8C1CC; font-size: 11px; text-align: center;")
            
            value_label = QLabel(value)
            value_label.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold; text-align: center;")
            value_label.setObjectName(f"stat_{title.replace(' ', '_')}")
            
            stat_layout_inner.addWidget(title_label)
            stat_layout_inner.addWidget(value_label)
            stats_layout.addWidget(stat_widget)
            self.stat_widgets.append(value_label)
        
        status_layout.addWidget(stats_widget)
        layout.addWidget(status_group)
        
        # Noticias recientes
        news_group = QGroupBox("📰 ÚLTIMAS CRÓNICAS")
        news_layout = QVBoxLayout(news_group)
        self.news_display = QTextBrowser()
        self.news_display.setObjectName("newsDisplay")
        self.news_display.setHtml("""
            <div style='color: #B8C1CC; text-align: center;'>
                <h3>Bienvenido Aventurero</h3>
                <p>Las noticias se cargarán pronto...</p>
            </div>
        """)
        news_layout.addWidget(self.news_display)
        layout.addWidget(news_group)
        
        return panel

    def create_game_control_panel(self):
        """Panel de control del juego"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)
        
        # Información de versión
        version_group = QGroupBox("🎮 INFORMACIÓN DEL JUEGO")
        version_layout = QVBoxLayout(version_group)
        
        self.version_label = QLabel("Cargando...")
        self.version_label.setStyleSheet("color: #C8A45C; font-size: 24px; font-weight: bold; text-align: center;")
        self.version_label.setAlignment(Qt.AlignCenter)
        
        self.realm_label = QLabel("Realm of Eternal Legends")
        self.realm_label.setStyleSheet("color: #B8C1CC; font-size: 12px; text-align: center;")
        self.realm_label.setAlignment(Qt.AlignCenter)
        
        version_layout.addWidget(self.version_label)
        version_layout.addWidget(self.realm_label)
        layout.addWidget(version_group)
        
        # Botón de juego principal
        self.play_button = QPushButton("🎮 INICIAR AVENTURA")
        self.play_button.setObjectName("playButton")
        self.play_button.setFixedHeight(58)
        self.play_button.setMinimumWidth(300)
        self.play_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.play_button.clicked.connect(self.launch_game)
        self.play_button.setEnabled(False)
        layout.addWidget(self.play_button)
        
        # Botón de actualizaciones
        self.update_button = QPushButton("🔄 BUSCAR ACTUALIZACIONES")
        self.update_button.setObjectName("actionButton")
        self.update_button.setMinimumHeight(35)
        self.update_button.clicked.connect(self.check_updates)
        layout.addWidget(self.update_button)
        
        # Botones de acción
        action_layout = QVBoxLayout()
        action_layout.setSpacing(8)
        
        buttons = [
            ("📰 Crónicas", self.show_news_page),
            ("⚔️ Misiones", self.show_quests_page),
            ("⚙️ Configuración", self.show_settings_page),
            ("🎮 Instalar Juego", self.show_game_installer)
        ]
        
        for text, slot in buttons:
            btn = QPushButton(text)
            btn.setObjectName("actionButton")
            btn.setMinimumHeight(35)
            btn.clicked.connect(slot)
            action_layout.addWidget(btn)
        
        layout.addLayout(action_layout)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Etiqueta de estado
        self.status_label = QLabel("Preparado para la aventura...")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Etiqueta de detalles
        self.details_label = QLabel("")
        self.details_label.setStyleSheet("color: #B8C1CC; font-size: 11px; padding: 5px;")
        self.details_label.setAlignment(Qt.AlignCenter)
        self.details_label.setWordWrap(True)
        layout.addWidget(self.details_label)
        
        return panel

    def create_footer(self):
        """Footer con estadísticas y enlaces"""
        footer = QWidget()
        footer.setFixedHeight(50)
        footer.setStyleSheet("background: #2B3442; border-radius: 10px; border: 1px solid #46556B;")
        
        layout = QHBoxLayout(footer)
        
        # Estadísticas
        stats_label = QLabel("👥 1.2M Aventureros • 🏰 45K Clanes • ⚔️ 8.7M Batallas")
        stats_label.setStyleSheet("color: #B8C1CC; font-size: 11px;")
        layout.addWidget(stats_label)
        
        layout.addStretch()
        
        # Enlaces sociales
        social_layout = QHBoxLayout()
        social_buttons = [
            ("Discord", DISCORD_URL, "#3A4556"),
            ("Foro", "#", "#5C6778"),
            ("Soporte", "#", "#C8A45C")
        ]
        
        for text, url, color in social_buttons:
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 10px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ opacity: 0.8; }}
            """)
            btn.setFixedSize(60, 25)
            btn.clicked.connect(lambda checked, u=url: self.open_url(u))
            social_layout.addWidget(btn)
        
        layout.addLayout(social_layout)
        
        return footer

    def setup_news_page(self):
        """Página de noticias"""
        try:
            self.news_panel = RPGNewsPanel(self)
            self.content_stack.addWidget(self.news_panel)
        except:
            # Fallback si no se puede cargar el panel de noticias
            fallback_widget = QWidget()
            layout = QVBoxLayout(fallback_widget)
            label = QLabel("Panel de Noticias - No disponible temporalmente")
            label.setStyleSheet("color: #F2F2F2; font-size: 16px; text-align: center;")
            layout.addWidget(label)
            
            back_btn = QPushButton("Volver al Inicio")
            back_btn.setObjectName("actionButton")
            back_btn.clicked.connect(self.show_main_page)
            layout.addWidget(back_btn)
            
            self.content_stack.addWidget(fallback_widget)

    def setup_quests_page(self):
        """Página de misiones"""
        try:
            self.quests_panel = QuestPanel(self)
            self.content_stack.addWidget(self.quests_panel)
        except:
            # Fallback si no se puede cargar el panel de misiones
            fallback_widget = QWidget()
            layout = QVBoxLayout(fallback_widget)
            label = QLabel("Panel de Misiones - No disponible temporalmente")
            label.setStyleSheet("color: #F2F2F2; font-size: 16px; text-align: center;")
            layout.addWidget(label)
            
            back_btn = QPushButton("Volver al Inicio")
            back_btn.setObjectName("actionButton")
            back_btn.clicked.connect(self.show_main_page)
            layout.addWidget(back_btn)
            
            self.content_stack.addWidget(fallback_widget)

    def setup_settings_page(self):
        """Página de configuración"""
        settings_page = QWidget()
        layout = QVBoxLayout(settings_page)
        
        settings_label = QLabel("Configuración del Juego")
        settings_label.setStyleSheet("color: #C8A45C; font-size: 24px; text-align: center;")
        settings_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(settings_label)
        
        # Controles de configuración
        config_group = QGroupBox("Opciones del Launcher")
        config_layout = QVBoxLayout(config_group)
        
        # Verificar archivos
        verify_btn = QPushButton("🔍 Verificar Integridad de Archivos")
        verify_btn.setObjectName("actionButton")
        verify_btn.clicked.connect(self.verify_files)
        config_layout.addWidget(verify_btn)
        
        # Limpiar caché
        clear_btn = QPushButton("🗑️ Limpiar Caché")
        clear_btn.setObjectName("actionButton")
        clear_btn.clicked.connect(self.clear_cache)
        config_layout.addWidget(clear_btn)
        
        layout.addWidget(config_group)
        
        # Botón volver
        back_btn = QPushButton("Volver al Inicio")
        back_btn.setObjectName("actionButton")
        back_btn.clicked.connect(self.show_main_page)
        layout.addWidget(back_btn)
        
        layout.addStretch()
        
        self.content_stack.addWidget(settings_page)

    def _connect_signals(self):
        """Conectar todas las señales"""
        self.worker_signals.update_signal.connect(self._update_status)
        self.worker_signals.progress_signal.connect(self._update_progress)
        self.worker_signals.error_signal.connect(self._show_error)
        self.worker_signals.news_loaded.connect(self._update_news)
        self.worker_signals.version_checked.connect(self._handle_version_check)
        self.worker_signals.download_complete.connect(self._handle_download_complete)
        self.worker_signals.extraction_complete.connect(self._handle_extraction_complete)
        self.worker_signals.install_complete.connect(self._handle_install_complete)
        self.worker_signals.update_info_ready.connect(self._update_info_display)
        self.worker_signals.connection_status.connect(self._update_connection_display)
        self.worker_signals.game_install_progress.connect(self._update_game_install_progress)
        self.worker_signals.game_install_status.connect(self._update_game_install_status)
        self.worker_signals.server_status_updated.connect(self._update_server_status)
        self.worker_signals.extraction_progress.connect(self._update_extraction_progress)  # Nueva señal

    # ========== FUNCIONALIDAD PRINCIPAL ==========

    def load_local_version(self):
        """Cargar versión local - CORREGIDO"""
        try:
            if os.path.exists(LOCAL_VERSION_PATH):
                with open(LOCAL_VERSION_PATH, 'r') as f:
                    local_data = json.load(f)
                    # Manejar diferentes formatos de archivo de versión
                    if isinstance(local_data, dict):
                        self.current_version = local_data.get("local_version", "0.0.0")
                    else:
                        self.current_version = str(local_data)
            else:
                self.current_version = "0.0.0"
                # Crear archivo de versión si no existe
                with open(LOCAL_VERSION_PATH, 'w') as f:
                    json.dump({"local_version": self.current_version}, f)
                
            self.version_label.setText(f"v{self.current_version}")
            self._update_status(f"Versión local: {self.current_version}")
            
        except Exception as e:
            self.current_version = "0.0.0"
            print(f"Error cargando versión local: {e}")
            self._show_error(f"Error cargando versión local: {e}")

    def check_updates(self):
        """Verificar actualizaciones - CORREGIDO"""
        self.update_button.setEnabled(False)
        self._update_status("Buscando actualizaciones...")
        
        threading.Thread(target=self._check_updates_thread, daemon=True).start()

    def _check_updates_thread(self):
        """Hilo para verificar actualizaciones - COMPLETAMENTE CORREGIDO"""
        try:
            print(f"Verificando actualizaciones desde: {REMOTE_VERSION_URL}")
            
            # Descargar información de versión remota
            response = requests.get(REMOTE_VERSION_URL, timeout=10)
            response.raise_for_status()
            remote_data = response.json()
            
            print(f"Datos remotos recibidos: {remote_data}")
            
            # NUEVA LÓGICA: Manejar la estructura con available_versions
            if "available_versions" in remote_data:
                available_versions = remote_data["available_versions"]
                if available_versions:
                    # Ordenar versiones de MENOR A MAYOR para la instalación
                    sorted_versions = sorted(available_versions, key=lambda v: version.parse(v))
                    latest_remote_version = sorted_versions[-1]  # La más reciente es la última
                    
                    # Encontrar todas las versiones más nuevas que la actual
                    new_versions = [v for v in sorted_versions if version.parse(v) > version.parse(self.current_version)]
                    
                    if new_versions:
                        self.available_updates = new_versions
                        self.latest_version = latest_remote_version
                        update_info = f"Versiones disponibles: {', '.join(new_versions)}"
                        self.worker_signals.update_info_ready.emit(update_info)
                        print(f"Actualizaciones disponibles (ordenadas): {new_versions}")
                    else:
                        self.available_updates = []
                        print("No hay actualizaciones disponibles")
                else:
                    self.available_updates = []
                    print("No hay versiones disponibles en el servidor")
            else:
                # Manejar formato antiguo por compatibilidad
                remote_version = remote_data.get("version", "0.0.0")
                self.latest_version = remote_version
                
                if version.parse(remote_version) > version.parse(self.current_version):
                    self.available_updates = [remote_version]
                    update_info = remote_data.get("update_info", f"Nueva versión {remote_version} disponible")
                    self.worker_signals.update_info_ready.emit(update_info)
                    print(f"Actualización disponible: {remote_version}")
                else:
                    self.available_updates = []
                    print("No hay actualizaciones disponibles")
                
            self.worker_signals.version_checked.emit(self.available_updates, self.current_version)
            
        except requests.RequestException as e:
            error_msg = f"Error de conexión: {str(e)}"
            print(error_msg)
            self.worker_signals.error_signal.emit(error_msg)
        except ValueError as e:
            error_msg = f"Error parseando JSON remoto: {str(e)}"
            print(error_msg)
            self.worker_signals.error_signal.emit(error_msg)
        except Exception as e:
            error_msg = f"Error verificando actualizaciones: {str(e)}"
            print(error_msg)
            self.worker_signals.error_signal.emit(error_msg)

    def _handle_version_check(self, updates, current_version):
        """Manejar resultado de verificación de versiones - CORREGIDO"""
        self.available_updates = updates
        self.update_button.setEnabled(True)
        
        if updates:
            # La última versión es la más alta (última en la lista ordenada)
            latest_update = updates[-1] if updates else updates[0]
            self._update_status(f"¡{len(updates)} actualizaciones disponibles!")
            self.details_label.setText(f"Última versión: v{latest_update}")
            self.play_button.setVisible(True)
            self.play_button.setText("🔄 INSTALAR ACTUALIZACIONES")
            self.play_button.setEnabled(True)
            self.play_button.clicked.disconnect()
            self.play_button.clicked.connect(self.start_downloads)
        else:
            self._update_status("¡Tu juego está actualizado!")
            self.details_label.setText("Tienes la última versión disponible")
            self.play_button.setVisible(True)
            self.play_button.setText("🎮 INICIAR AVENTURA")
            self.play_button.setEnabled(True)
            self.play_button.clicked.disconnect()
            self.play_button.clicked.connect(self.launch_game)

    def start_downloads(self):
        """Iniciar descarga de actualizaciones - CORREGIDO"""
        if not self.available_updates:
            self._show_error("No hay actualizaciones disponibles para descargar")
            return
            
        self.play_button.setVisible(False)
        self.play_button.setEnabled(False)
        self.update_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self._update_status("Iniciando descarga de actualizaciones...")
        
        threading.Thread(target=self._download_all_updates, daemon=True).start()

    def _download_all_updates(self):
        """Descargar todas las actualizaciones disponibles en orden ascendente - CORREGIDO"""
        try:
            # ORDENAR DE MENOR A MAYOR (ascendente)
            sorted_versions = sorted(self.available_updates, key=lambda v: version.parse(v))
            total_updates = len(sorted_versions)
            
            print(f"Actualizaciones a instalar en orden: {sorted_versions}")
            
            for i, version_str in enumerate(sorted_versions):
                self._update_status(f"Descargando actualización {i+1}/{total_updates}: v{version_str}")
                
                # Construir URL específica para esta versión
                # Asumiendo que las URLs siguen un patrón como: base_url/v{version}.zip
                version_zip_url = REMOTE_ZIP_URL.replace("version.zip", f"v{version_str}.zip")
                print(f"Descargando desde: {version_zip_url}")
                
                # Descargar archivo ZIP
                response = requests.get(version_zip_url, stream=True, timeout=30)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                chunk_size = 8192
                
                zip_filename = f"update_v{version_str}.zip"
                
                with open(zip_filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if self.pause_download:
                            while self.pause_download:
                                time.sleep(0.1)
                        
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            
                            if total_size > 0:
                                percent = (downloaded_size / total_size) * 100
                                speed = f"{downloaded_size / (1024 * 1024):.1f} MB"
                                details = f"Descargando v{version_str}... {percent:.1f}% completado"
                                self.worker_signals.progress_signal.emit(int(percent), speed, details)
                
                self.worker_signals.download_complete.emit(version_str)
                
                # Extraer archivo con visualización de progreso
                self._update_status(f"Instalando v{version_str}...")
                self._extract_zip_with_progress(zip_filename, version_str)
                
                # Actualizar versión local
                self.current_version = version_str
                with open(LOCAL_VERSION_PATH, 'w') as f:
                    json.dump({"local_version": self.current_version}, f)
                
                # Limpiar archivo temporal
                if os.path.exists(zip_filename):
                    os.remove(zip_filename)
                    print(f"Archivo {zip_filename} eliminado después de la extracción")
                
                # Pequeña pausa entre actualizaciones
                time.sleep(1)
            
            self.worker_signals.install_complete.emit()
            
        except requests.RequestException as e:
            error_msg = f"Error de descarga: {str(e)}"
            print(error_msg)
            self.worker_signals.error_signal.emit(error_msg)
        except zipfile.BadZipFile:
            error_msg = "El archivo descargado está corrupto o no es un ZIP válido"
            print(error_msg)
            self.worker_signals.error_signal.emit(error_msg)
        except Exception as e:
            error_msg = f"Error en la descarga: {str(e)}"
            print(error_msg)
            self.worker_signals.error_signal.emit(error_msg)

    def _extract_zip_with_progress(self, zip_filename, version_str):
        """Extraer archivo ZIP mostrando progreso y archivos extraídos"""
        try:
            with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
                # Obtener lista de archivos
                file_list = zip_ref.namelist()
                total_files = len(file_list)
                
                for i, file in enumerate(file_list):
                    # Extraer archivo
                    zip_ref.extract(file, ".")
                    
                    # Emitir señal de progreso de extracción
                    progress = f"Extrayendo: {file}"
                    self.worker_signals.extraction_progress.emit(version_str, progress)
                    
                    # Actualizar barra de progreso para extracción
                    percent = (i + 1) / total_files * 100
                    self.worker_signals.progress_signal.emit(
                        int(percent), 
                        f"{i+1}/{total_files} archivos", 
                        f"Extrayendo v{version_str}: {file}"
                    )
                    
                    # Pequeña pausa para que se pueda ver el progreso
                    time.sleep(0.05)
                
                print(f"Extracción completada para v{version_str}. {total_files} archivos extraídos.")
                
        except Exception as e:
            print(f"Error extrayendo {zip_filename}: {e}")
            raise

    def _handle_download_complete(self, version_str):
        """Manejar descarga completada"""
        self._update_status(f"Versión {version_str} descargada correctamente")

    def _handle_extraction_complete(self):
        """Manejar extracción completada"""
        self._update_status("Extracción completada")

    def _handle_install_complete(self):
        """Manejar instalación completada"""
        self.progress_bar.setVisible(False)
        self.play_button.setVisible(True)
        self.update_button.setEnabled(True)
        self._update_status("¡Todas las actualizaciones instaladas!")
        self.version_label.setText(f"v{self.current_version}")
        self.details_label.setText("")
        
        self.play_button.setVisible(True)
        self.play_button.setText("🎮 INICIAR AVENTURA")
        self.play_button.setEnabled(True)
        self.play_button.clicked.disconnect()
        self.play_button.clicked.connect(self.launch_game)
        
        QMessageBox.information(self, "Actualización Completada", 
                              f"El juego ha sido actualizado a la versión {self.current_version} correctamente.")

    def _update_extraction_progress(self, version_str, file_info):
        """Actualizar la interfaz con información de extracción"""
        self.details_label.setText(f"v{version_str}: {file_info}")

    def launch_game(self):
        """Lanzar el juego - CORREGIDO"""
        if not os.path.exists(GAME_EXECUTABLE):
            self.show_game_installer()
            return
        
        self._update_status("🎮 Iniciando aventura épica...")
        
        try:
            # Usar el directorio actual como working directory
            game_dir = os.path.dirname(GAME_EXECUTABLE) or "."
            subprocess.Popen([GAME_EXECUTABLE], cwd=game_dir, shell=True)
            self._update_status("¡Juego iniciado! Cerrando launcher...")
            QTimer.singleShot(2000, self.close)
        except Exception as e:
            error_msg = f"Error al iniciar el juego: {str(e)}"
            print(error_msg)
            self._show_error(error_msg)

    def show_game_installer(self):
        """Mostrar instalador del juego - CORREGIDO"""
        reply = QMessageBox.question(self, "Juego No Instalado", 
                                   "El juego no está instalado. ¿Deseas instalarlo ahora?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self._update_status("Preparando instalación del juego...")
            threading.Thread(target=self._install_game, daemon=True).start()

    def _install_game(self):
        """Instalar el juego - CORREGIDO"""
        try:
            self.worker_signals.game_install_status.emit("Descargando instalador...")
            
            # Verificar URL del instalador
            if not GAME_INSTALLER_URL or GAME_INSTALLER_URL == "https://example.com/game_installer.zip":
                self.worker_signals.error_signal.emit("URL del instalador no configurada correctamente")
                return
            
            # Descargar instalador
            response = requests.get(GAME_INSTALLER_URL, stream=True, timeout=30)
            response.raise_for_status()
            
            installer_path = "game_installer.zip"
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(installer_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if total_size > 0:
                            percent = (downloaded_size / total_size) * 100
                            speed = f"{downloaded_size / (1024 * 1024):.1f} MB"
                            details = f"Descargando juego... {percent:.1f}% completado"
                            self.worker_signals.game_install_progress.emit(int(percent), speed, details)
            
            # Extraer instalador con visualización de progreso
            self.worker_signals.game_install_status.emit("Instalando juego...")
            self._extract_zip_with_progress(installer_path, "juego_completo")
            
            # Limpiar
            if os.path.exists(installer_path):
                os.remove(installer_path)
                print("Archivo de instalación eliminado")
            
            # Establecer versión inicial
            self.current_version = "1.0.0"
            with open(LOCAL_VERSION_PATH, 'w') as f:
                json.dump({"local_version": self.current_version}, f)
            
            self.version_label.setText(f"v{self.current_version}")
            
            self.worker_signals.game_install_status.emit("¡Juego instalado correctamente!")
            QTimer.singleShot(2000, lambda: self.worker_signals.game_install_status.emit(""))
            
        except Exception as e:
            error_msg = f"Error instalando el juego: {str(e)}"
            print(error_msg)
            self.worker_signals.error_signal.emit(error_msg)

    def load_news(self):
        """Cargar noticias - CORREGIDO"""
        def fetch_news():
            try:
                if not REMOTE_NEWS_URL or REMOTE_NEWS_URL == "https://example.com/news.html":
                    # Usar noticias por defecto si no hay URL configurada
                    raise Exception("URL de noticias no configurada")
                
                response = requests.get(REMOTE_NEWS_URL, timeout=10)
                response.raise_for_status()
                news_text = response.text
                
                # Formatear como HTML
                news_html = f"""
                <div style='color: #e2e8f0; font-family: Arial;'>
                    <h3 style='color: #C8A45C; text-align: center;'>Últimas Noticias</h3>
                    <div style='padding: 10px; line-height: 1.5;'>
                        {news_text.replace(chr(10), '<br>')}
                    </div>
                </div>
                """
                self.worker_signals.news_loaded.emit(news_html)
            except Exception as e:
                # Noticias por defecto en caso de error
                default_news = """
                <div style='color: #e2e8f0; font-family: Arial;'>
                    <h3 style='color: #C8A45C; text-align: center;'>¡Bienvenido Aventurero!</h3>
                    <p style='text-align: center;'>Explora mundos fantásticos y enfréntate a desafíos épicos</p>
                    <p style='text-align: center; margin-top: 15px;'>
                        <strong>Novedades:</strong><br>
                        • Nuevo sistema de misiones<br>
                        • Zonas inexploradas<br>
                        • Objetos legendarios<br>
                    </p>
                </div>
                """
                self.worker_signals.news_loaded.emit(default_news)
                print(f"Error loading news: {e}")
        
        threading.Thread(target=fetch_news, daemon=True).start()

    def update_connection_status(self):
        """Verificar estado de conexión"""
        def check_connection():
            try:
                socket.create_connection(("8.8.8.8", 53), timeout=3)
                self.worker_signals.connection_status.emit(True)
            except OSError:
                self.worker_signals.connection_status.emit(False)
            
            # Verificar cada 30 segundos
            QTimer.singleShot(30000, self.update_connection_status)
        
        threading.Thread(target=check_connection, daemon=True).start()

    def check_server_status(self):
        """Verificar estado del servidor"""
        def check_status():
            try:
                if SERVER_STATUS_URL and SERVER_STATUS_URL != "https://api.example.com/status":
                    response = requests.get(SERVER_STATUS_URL, timeout=10)
                    status = response.json()
                else:
                    # Simulación si no hay URL configurada
                    status = {
                        "online": True,
                        "players": random.randint(800, 1500),
                        "uptime": f"{random.randint(1, 30)}d {random.randint(1, 23)}h",
                        "ping": f"{random.randint(20, 80)}ms"
                    }
                
                self.worker_signals.server_status_updated.emit(status)
                
                # Verificar cada 60 segundos
                QTimer.singleShot(60000, self.check_server_status)
            except Exception as e:
                print(f"Error checking server status: {e}")
                # Reintentar después de 30 segundos en caso de error
                QTimer.singleShot(30000, self.check_server_status)
        
        threading.Thread(target=check_status, daemon=True).start()

    # ========== MÉTODOS AUXILIARES ==========

    def _update_status(self, message):
        self.status_label.setText(message)

    def _update_progress(self, percent, speed, details):
        self.progress_bar.setValue(percent)
        self.details_label.setText(details)

    def _show_error(self, error_msg):
        self.status_label.setText("Error")
        self.details_label.setText(error_msg)
        self.progress_bar.setVisible(False)
        self.play_button.setVisible(True)
        self.play_button.setEnabled(True)
        self.update_button.setEnabled(True)
        QMessageBox.critical(self, "Error", error_msg)

    def _update_news(self, news_text):
        self.news_display.setHtml(news_text)

    def _update_info_display(self, info_text):
        self.details_label.setText(info_text)

    def _update_connection_display(self, connected):
        if connected:
            self.connection_status.setText("● Conectado")
            self.connection_status.setStyleSheet("color: #B8C1CC; font-weight: bold; font-size: 12px;")
        else:
            self.connection_status.setText("● Sin conexión")
            self.connection_status.setStyleSheet("color: #C8A45C; font-weight: bold; font-size: 12px;")

    def _update_game_install_progress(self, percent, speed, details):
        self.progress_bar.setValue(percent)
        self.details_label.setText(details)

    def _update_game_install_status(self, status):
        self.status_label.setText(status)

    def _update_server_status(self, status):
        self.server_status = status
        # Actualizar estadísticas en la UI
        if hasattr(self, 'stat_widgets'):
            stats = [
                ("CONECTADO" if status["online"] else "OFFLINE", 
                 "#10b981" if status["online"] else "#ef4444"),
                (f"{status['players']:,}", "#fbbf24"),
                (status["uptime"], "#8b5cf6"),
                (status["ping"], "#60a5fa")
            ]
            
            for i, (value, color) in enumerate(stats):
                if i < len(self.stat_widgets):
                    self.stat_widgets[i].setText(value)
                    self.stat_widgets[i].setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold; text-align: center;")

    def verify_files(self):
        """Verificar integridad de archivos"""
        self._update_status("Verificando archivos del juego...")
        QTimer.singleShot(2000, lambda: self._update_status("Verificación completada"))

    def clear_cache(self):
        """Limpiar caché"""
        self._update_status("Limpiando caché...")
        QTimer.singleShot(1500, lambda: self._update_status("Caché limpiado"))

    # Métodos de navegación
    def show_main_page(self):
        self.content_stack.setCurrentIndex(0)

    def show_news_page(self):
        self.content_stack.setCurrentIndex(1)

    def show_quests_page(self):
        self.content_stack.setCurrentIndex(2)

    def show_settings_page(self):
        self.content_stack.setCurrentIndex(3)

    def open_url(self, url):
        if url and url != "#":
            QDesktopServices.openUrl(QUrl(url))


def build_global_qss():
    """QSS global base para la ventana principal y widgets generales."""
    return """
    /* Fondo principal azul grisáceo oscuro */
    #centralRoot {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #1B2330, stop:0.5 #202A38, stop:1 #1A2230);
    }

    /* Borde fino para menús/paneles sueltos */
    QMenu {
        background-color: #2B3442;
        color: #F2F2F2;
        border: 1px solid #46556B;
    }
    """

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Establecer estilo fusion
    app.setStyle("Fusion")
    
    # Aplicar estilo global (QSS) basado en paleta oscura moderna
    app.setStyleSheet(build_global_qss())

    # Configurar fuente
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    launcher = ModernGameLauncher()
    launcher.show()
    
    sys.exit(app.exec_())