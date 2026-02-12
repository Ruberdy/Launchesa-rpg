import sys
import os
import requests
import zipfile
import threading
import subprocess
import socket
import time
import json
from packaging import version
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QProgressBar, QFrame, 
                            QMessageBox, QMenu, QSizePolicy, QScrollArea)
from PyQt5.QtCore import Qt, QTimer, QUrl, QSize, QObject, pyqtSignal, QPropertyAnimation
from PyQt5.QtGui import QPixmap, QFont, QDesktopServices, QIcon, QColor, QPainter, QFontInfo
from news import RPGNewsPanel  # Importar la clase de news.py

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
            "LOGO_IMAGE_PATH": "logo.png"
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

class WorkerSignals(QObject):
    update_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, str, str)
    error_signal = pyqtSignal(str)
    news_loaded = pyqtSignal(list)  # Cambiado a lista de noticias
    version_checked = pyqtSignal(list, str)
    download_complete = pyqtSignal(str)
    extraction_complete = pyqtSignal()
    install_complete = pyqtSignal()
    update_info_ready = pyqtSignal(str)
    connection_status = pyqtSignal(bool)
    game_install_progress = pyqtSignal(int, str, str)
    game_install_status = pyqtSignal(str)

class GradientWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#F9FAFB"))

class NewsCard(QWidget):
    def __init__(self, news_data, index, parent=None):
        super().__init__(parent)
        self.news_data = news_data
        self.index = index
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Imagen
        self.image_label = QLabel()
        if os.path.exists(self.news_data.get("image_url", "")):
            pixmap = QPixmap(self.news_data["image_url"]).scaled(200, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(pixmap)
        elif self.news_data.get("image_url"):
            self.image_label.setText("Cargando imagen...")
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label)

        # Título
        title_label = QLabel(self.news_data.get("title", "Sin título"))
        title_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #1E40AF;")
        layout.addWidget(title_label)

        # Botón o área clicable
        click_area = QPushButton("Leer más")
        click_area.setCursor(Qt.PointingHandCursor)
        click_area.clicked.connect(lambda: self.open_news_detail())
        click_area.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 15px;
                font-weight: 500;
                transition: all 0.3s ease;
            }
            QPushButton:hover {
                background-color: #2563EB;
                transform: translateY(-2px);
            }
            QPushButton:pressed {
                background-color: #1E40AF;
                transform: translateY(0);
            }
        """)
        layout.addWidget(click_area)

        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-radius: 10px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                border: 1px solid #E0E7FF;
                margin-bottom: 15px;
            }
        """)

    def open_news_detail(self):
        news_window = RPGNewsPanel()
        news_window.show_news_detail(self.news_data)
        news_window.show()

class ModernGameLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Variables de control
        self.available_updates = []
        self.update_sizes = {}
        self.downloading = False
        self.pause_download = False
        self.installing_game = False
        self.news_data = []
        
        # Configuración de la ventana
        self.setWindowTitle("FosterGames Launcher")
        self.setFixedSize(1200, 800)
        if os.path.exists(LOGO_IMAGE_PATH):
            self.setWindowIcon(QIcon(LOGO_IMAGE_PATH))
        
        # Widget de fondo neutro
        self.background = GradientWidget()
        self.setCentralWidget(self.background)
        
        # Layout principal
        self.main_layout = QVBoxLayout(self.background)
        self.main_layout.setContentsMargins(50, 50, 50, 40)
        self.main_layout.setSpacing(30)
        
        # Aplicar estilos CSS mejorados
        self.setStyleSheet("""
            /* Estilos generales */
            QWidget {
                font-family: 'Poppins', 'Roboto', sans-serif;
                font-size: 14px;
                color: #64748B;
            }
            
            /* Contenedores */
            .MainPanel {
                background-color: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
                border: 2px solid #E0E7FF;
                transition: all 0.3s ease;
            }
            
            .ContentPanel {
                background-color: #FFFFFF;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                border: 1px solid #E0E7FF;
                transition: all 0.3s ease;
            }
            
            /* Textos */
            .Title {
                color: #1E40AF;
                font-size: 36px;
                font-weight: 700;
                text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            
            .Subtitle {
                color: #2563EB;
                font-size: 20px;
                font-weight: 600;
            }
            
            .NormalText {
                color: #64748B;
                font-size: 15px;
            }
            
            /* Botones */
            QPushButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 12px 25px;
                font-weight: 600;
                min-width: 160px;
                transition: all 0.3s ease;
                box-shadow: 0 3px 6px rgba(59, 130, 246, 0.4);
            }
            
            QPushButton:hover {
                background-color: #2563EB;
                transform: translateY(-3px);
                box-shadow: 0 6px 12px rgba(59, 130, 246, 0.6);
            }
            
            QPushButton:pressed {
                background-color: #1E40AF;
                transform: translateY(0);
                box-shadow: 0 3px 6px rgba(59, 130, 246, 0.4);
            }
            
            QPushButton:disabled {
                background-color: #A3BFFA;
                box-shadow: none;
            }
            
            .MainButton {
                background-color: #1E40AF;
                font-size: 20px;
                padding: 15px 35px;
                min-width: 220px;
            }
            
            /* Barra de progreso */
            QProgressBar {
                border: 2px solid #E0E7FF;
                border-radius: 10px;
                text-align: center;
                color: #1E40AF;
                height: 25px;
                background-color: #F1F5F9;
                font-weight: 500;
            }
            
            QProgressBar::chunk {
                background-color: #3B82F6;
                border-radius: 8px;
                width: 12px;
            }
            
            /* Área de texto */
            QTextBrowser {
                background-color: #F9FAFB;
                color: #64748B;
                border: 1px solid #E0E7FF;
                border-radius: 10px;
                padding: 15px;
                font-size: 15px;
            }
            
            /* Menús */
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #E0E7FF;
                border-radius: 10px;
                padding: 12px;
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
            }
            
            QMenu::item {
                padding: 10px 25px;
                color: #64748B;
                font-weight: 500;
            }
            
            QMenu::item:selected {
                background-color: #E0E7FF;
                color: #1E40AF;
                border-radius: 8px;
            }
            
            QMenu::separator {
                height: 2px;
                background-color: #E0E7FF;
                margin: 8px 0;
            }
        """)
        
        # Configurar señales
        self.worker_signals = WorkerSignals()
        self._connect_signals()
        
        # Configurar interfaz
        self.setup_header()
        self.setup_content()
        self.setup_footer()
        
        # Inicializar
        self.update_connection_status()
        self.load_news()
        self.check_updates()

    def _connect_signals(self):
        self.worker_signals.update_signal.connect(self._update_status)
        self.worker_signals.progress_signal.connect(self._update_progress)
        self.worker_signals.error_signal.connect(self._show_error)
        self.worker_signals.news_loaded.connect(self._update_news_cards)
        self.worker_signals.version_checked.connect(self._handle_version_check)
        self.worker_signals.download_complete.connect(self._handle_download_complete)
        self.worker_signals.extraction_complete.connect(self._handle_extraction_complete)
        self.worker_signals.install_complete.connect(self._handle_install_complete)
        self.worker_signals.update_info_ready.connect(self._update_info_display)
        self.worker_signals.connection_status.connect(self._update_connection_display)
        self.worker_signals.game_install_progress.connect(self._update_game_install_progress)
        self.worker_signals.game_install_status.connect(self._update_game_install_status)

    def _update_status(self, message):
        self.status_label.setText(message)
        self._animate_status()

    def _update_progress(self, percent, speed, details):
        self.progress.setValue(percent)
        self.percent_label.setText(f"{percent}% • {speed}")
        self.details_label.setText(details)

    def _show_error(self, error_msg):
        self.status_label.setText("Error")
        self.details_label.setText(error_msg)
        QMessageBox.critical(self, "Error", error_msg)

    def _update_news_cards(self, news_data):
        self.news_data = news_data
        self.news_container.layout().removeWidget(self.news_placeholder)
        self.news_placeholder.deleteLater()
        self.news_placeholder = None

        for i in range(self.news_layout.count()):
            self.news_layout.itemAt(i).widget().deleteLater()
        self.news_layout.setAlignment(Qt.AlignTop)

        for index, news in enumerate(news_data):
            card = NewsCard(news, index, self)
            self.news_layout.addWidget(card)

    def _handle_version_check(self, updates, current_version):
        self.available_updates = updates
        self.version_label.setText(f"Versión actual: {current_version}")
        
        if updates:
            threading.Thread(target=self._prepare_update_info, args=(updates,), daemon=True).start()
        else:
            self.status_label.setText("Tu juego está actualizado")
            self.play_button.setText("▶ INICIAR JUEGO")
            self.play_button.setEnabled(True)
            self.play_button.clicked.disconnect()
            self.play_button.clicked.connect(self.launch_game)

    def _prepare_update_info(self, updates):
        self.update_sizes = {}
        total_size = 0
        info_lines = ["<b>Actualizaciones disponibles:</b>"]
        
        for version_str in updates:
            try:
                url = REMOTE_ZIP_URL.replace("version", version_str)
                head = requests.head(url, allow_redirects=True, timeout=5)
                size_bytes = int(head.headers.get('content-length', 0))
                self.update_sizes[version_str] = size_bytes
                total_size += size_bytes
                
                if size_bytes > 0:
                    size_mb = size_bytes / (1024 * 1024)
                    size_str = f"{size_mb:.1f} MB"
                else:
                    size_str = "Tamaño desconocido"
                
                info_lines.append(f"{len(info_lines)}. Versión {version_str} ({size_str})")
            except Exception as e:
                print(f"Error getting size for {version_str}: {e}")
                self.update_sizes[version_str] = 0
                info_lines.append(f"{len(info_lines)}. Versión {version_str} (Tamaño desconocido)")
        
        if total_size > 0:
            total_mb = total_size / (1024 * 1024)
            info_lines.append(f"<br><b>TOTAL:</b> {len(updates)} actualizaciones, {total_mb:.1f} MB")
        else:
            info_lines.append(f"<br><b>TOTAL:</b> {len(updates)} actualizaciones")
        
        self.worker_signals.update_info_ready.emit("<br>".join(info_lines))
        self.worker_signals.update_signal.emit("Actualizaciones disponibles!")

    def _update_info_display(self, info_text):
        self.details_label.setText(info_text)
        self.play_button.setText("INSTALAR ACTUALIZACIONES")
        self.play_button.setEnabled(True)
        self.play_button.clicked.disconnect()
        self.play_button.clicked.connect(self.start_downloads)

    def _handle_download_complete(self, version_str):
        self.status_label.setText(f"Instalando versión {version_str}...")
        threading.Thread(target=self._extract_update, daemon=True).start()

    def _extract_update(self):
        try:
            with zipfile.ZipFile(ZIP_DEST, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                total_files = len(file_list)
                
                for i, file in enumerate(file_list):
                    zip_ref.extract(file, ".")
                    percent = int(100 * (i + 1) / total_files)
                    
                    self.worker_signals.progress_signal.emit(
                        percent, 
                        f"Extrayendo... {percent}%", 
                        f"Instalando: {file}"
                    )
            
            self.worker_signals.extraction_complete.emit()
            
        except Exception as e:
            self.worker_signals.error_signal.emit(f"Error al extraer archivos: {str(e)}")

    def _handle_extraction_complete(self):
        os.remove(ZIP_DEST)
        if self.available_updates:
            with open(LOCAL_VERSION_PATH, 'w') as f:
                json.dump({"local_version": self.available_updates[-1]}, f)
            self.version_label.setText(f"Versión actual: {self.available_updates[-1]}")
        
        self._hide_progress_ui()
        self.worker_signals.install_complete.emit()

    def _handle_install_complete(self):
        self.play_button.setText("▶ INICIAR JUEGO")
        self.play_button.setEnabled(True)
        self.play_button.clicked.disconnect()
        self.play_button.clicked.connect(self.launch_game)
        QMessageBox.information(self, "Completado", "Las actualizaciones se instalaron correctamente.")

    def _update_connection_display(self, connected):
        if connected:
            self.connection_status.setText("● Conectado")
            self.connection_status.setStyleSheet("color: #10B981; font-weight: bold;")
        else:
            self.connection_status.setText("● Sin conexión")
            self.connection_status.setStyleSheet("color: #EF4444; font-weight: bold;")

    def _update_game_install_progress(self, percent, speed, details):
        self.install_progress.setValue(percent)
        self.install_percent.setText(f"{percent}% • {speed}")
        self.install_details.setText(details)

    def _update_game_install_status(self, status):
        self.install_status.setText(status)

    def _animate_status(self):
        anim = QPropertyAnimation(self.status_label, b"geometry")
        anim.setDuration(300)
        anim.setStartValue(self.status_label.geometry())
        anim.setEndValue(self.status_label.geometry().adjusted(0, -5, 0, 5))
        anim.setLoopCount(2)
        anim.start()

    def _animate_news(self):
        anim = QPropertyAnimation(self.news_container, b"geometry")
        anim.setDuration(400)
        anim.setStartValue(self.news_container.geometry())
        anim.setEndValue(self.news_container.geometry().adjusted(0, -10, 0, 10))
        anim.setLoopCount(2)
        anim.start()

    def setup_header(self):
        header_frame = QWidget()
        header_frame.setObjectName("MainPanel")
        header_frame.setLayout(QHBoxLayout())
        header_frame.layout().setContentsMargins(30, 25, 30, 25)
        
        # Logo y título
        logo_title_frame = QWidget()
        logo_title_frame.setLayout(QHBoxLayout())
        logo_title_frame.layout().setContentsMargins(0, 0, 0, 0)
        logo_title_frame.layout().setSpacing(25)
        
        # Logo
        self.logo = QLabel()
        if os.path.exists(LOGO_IMAGE_PATH):
            pixmap = QPixmap(LOGO_IMAGE_PATH).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo.setPixmap(pixmap)
        else:
            self.logo.setText("FG")
            self.logo.setStyleSheet("font-size: 40px; color: #3B82F6; font-weight: 700;")
        
        # Título
        title_frame = QWidget()
        title_frame.setLayout(QVBoxLayout())
        title_frame.layout().setContentsMargins(0, 0, 0, 0)
        title_frame.layout().setSpacing(10)
        
        self.title_label = QLabel("FOSTER GAMES LAUNCHER")
        self.title_label.setObjectName("Title")
        
        self.subtitle_label = QLabel("Bienvenido a la aventura")
        self.subtitle_label.setObjectName("Subtitle")
        
        title_frame.layout().addWidget(self.title_label)
        title_frame.layout().addWidget(self.subtitle_label)
        
        logo_title_frame.layout().addWidget(self.logo)
        logo_title_frame.layout().addWidget(title_frame)
        
        # Menú y estado
        menu_frame = QWidget()
        menu_frame.setLayout(QHBoxLayout())
        menu_frame.layout().setContentsMargins(0, 0, 0, 0)
        menu_frame.layout().setSpacing(20)
        
        self.help_btn = QPushButton("Ayuda")
        self.help_btn.setCursor(Qt.PointingHandCursor)
        self.help_btn.clicked.connect(self.show_help_menu)
        
        self.recovery_btn = QPushButton("Recuperación")
        self.recovery_btn.setCursor(Qt.PointingHandCursor)
        self.recovery_btn.clicked.connect(self.show_recovery_menu)
        
        self.connection_status = QLabel("● Comprobando...")
        self.connection_status.setObjectName("NormalText")
        
        menu_frame.layout().addWidget(self.help_btn)
        menu_frame.layout().addWidget(self.recovery_btn)
        menu_frame.layout().addWidget(self.connection_status)
        
        header_frame.layout().addWidget(logo_title_frame)
        header_frame.layout().addStretch()
        header_frame.layout().addWidget(menu_frame)
        
        self.main_layout.addWidget(header_frame)

    def setup_content(self):
        content_frame = QWidget()
        content_frame.setLayout(QHBoxLayout())
        content_frame.layout().setContentsMargins(0, 0, 0, 0)
        content_frame.layout().setSpacing(40)
        
        # Panel izquierdo (noticias)
        left_panel = QWidget()
        left_panel.setObjectName("ContentPanel")
        left_panel.setLayout(QVBoxLayout())
        left_panel.layout().setContentsMargins(25, 25, 25, 25)
        left_panel.layout().setSpacing(20)
        
        news_title = QLabel("ÚLTIMAS NOTICIAS")
        news_title.setObjectName("Subtitle")
        
        # Contenedor de noticias con scroll
        self.news_container = QWidget()
        self.news_layout = QVBoxLayout(self.news_container)
        self.news_layout.setAlignment(Qt.AlignTop)
        self.news_placeholder = QLabel("Cargando noticias...")
        self.news_layout.addWidget(self.news_placeholder)
        
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.news_container)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background: transparent; border: none;")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        left_panel.layout().addWidget(news_title)
        left_panel.layout().addWidget(scroll_area, 1)
        
        # Panel derecho (control del juego)
        right_panel = QWidget()
        right_panel.setObjectName("ContentPanel")
        right_panel.setLayout(QVBoxLayout())
        right_panel.layout().setContentsMargins(30, 30, 30, 30)
        right_panel.layout().setSpacing(25)
        
        # Información de versión
        version_frame = QWidget()
        version_frame.setLayout(QVBoxLayout())
        version_frame.layout().setContentsMargins(0, 0, 0, 0)
        version_frame.layout().setSpacing(15)
        
        version_title = QLabel("ESTADO DEL JUEGO")
        version_title.setObjectName("Subtitle")
        
        self.version_label = QLabel("Versión: Comprobando...")
        self.version_label.setObjectName("NormalText")
        
        version_frame.layout().addWidget(version_title)
        version_frame.layout().addWidget(self.version_label)
        
        # Barra de estado
        status_frame = QWidget()
        status_frame.setLayout(QVBoxLayout())
        status_frame.layout().setContentsMargins(0, 0, 0, 0)
        status_frame.layout().setSpacing(15)
        
        self.status_label = QLabel("Comprobando actualizaciones...")
        self.status_label.setObjectName("NormalText")
        self.status_label.setStyleSheet("""
            padding: 15px;
            background-color: #F9FAFB;
            border-radius: 10px;
            border: 1px solid #E0E7FF;
        """)
        
        status_frame.layout().addWidget(self.status_label)
        
        # Barra de progreso
        progress_frame = QWidget()
        progress_frame.setLayout(QVBoxLayout())
        progress_frame.layout().setContentsMargins(0, 0, 0, 0)
        progress_frame.layout().setSpacing(15)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        
        self.percent_label = QLabel()
        self.percent_label.setObjectName("NormalText")
        self.percent_label.setAlignment(Qt.AlignCenter)
        
        progress_frame.layout().addWidget(self.progress)
        progress_frame.layout().addWidget(self.percent_label)
        
        # Detalles
        details_frame = QWidget()
        details_frame.setLayout(QVBoxLayout())
        details_frame.layout().setContentsMargins(0, 0, 0, 0)
        details_frame.layout().setSpacing(15)
        
        self.details_label = QLabel()
        self.details_label.setObjectName("NormalText")
        self.details_label.setWordWrap(True)
        self.details_label.setStyleSheet("""
            padding: 15px;
            background-color: #F9FAFB;
            border-radius: 10px;
            border: 1px solid #E0E7FF;
        """)
        
        details_frame.layout().addWidget(self.details_label)
        
        # Botones
        button_area = QWidget()
        button_area.setLayout(QVBoxLayout())
        button_area.layout().setContentsMargins(0, 0, 0, 0)
        button_area.layout().setSpacing(20)
        
        self.play_button = QPushButton("▶ INICIAR JUEGO")
        self.play_button.setObjectName("MainButton")
        self.play_button.setCursor(Qt.PointingHandCursor)
        self.play_button.clicked.connect(self.check_updates)
        self.play_button.setMinimumHeight(60)
        
        self.pause_button = QPushButton("⏸ PAUSAR DESCARGA")
        self.pause_button.setCursor(Qt.PointingHandCursor)
        self.pause_button.clicked.connect(self.toggle_pause)
        self.pause_button.hide()
        
        button_area.layout().addWidget(self.play_button)
        button_area.layout().addWidget(self.pause_button)
        
        right_panel.layout().addWidget(version_frame)
        right_panel.layout().addWidget(status_frame)
        right_panel.layout().addWidget(progress_frame)
        right_panel.layout().addWidget(details_frame)
        right_panel.layout().addStretch()
        right_panel.layout().addWidget(button_area)
        
        content_frame.layout().addWidget(left_panel, 1)
        content_frame.layout().addWidget(right_panel, 1)
        
        self.main_layout.addWidget(content_frame, 1)

    def setup_footer(self):
        footer_frame = QWidget()
        footer_frame.setLayout(QHBoxLayout())
        footer_frame.layout().setContentsMargins(0, 0, 0, 0)
        
        copyright_label = QLabel("© 2025 FosterGames - Todos los derechos reservados")
        copyright_label.setObjectName("NormalText")
        
        version_label = QLabel("Launcher v1.0.0")
        version_label.setObjectName("NormalText")
        
        footer_frame.layout().addWidget(copyright_label)
        footer_frame.layout().addStretch()
        version_frame = QWidget()
        version_frame.setLayout(QHBoxLayout())
        version_frame.layout().addWidget(version_label)
        footer_frame.layout().addWidget(version_frame)
        
        self.main_layout.addWidget(footer_frame)

    def update_connection_status(self):
        def check_connection():
            connected = self.check_internet()
            self.worker_signals.connection_status.emit(connected)
            QTimer.singleShot(10000, self.update_connection_status)
        
        threading.Thread(target=check_connection, daemon=True).start()

    def check_internet(self):
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except OSError:
            return False

    def load_news(self):
        def fetch_news():
            try:
                news_data = RPGNewsPanel.get_news_data()
                self.worker_signals.news_loaded.emit(news_data)
            except Exception as e:
                self.worker_signals.news_loaded.emit([
                    {"title": "Error al cargar noticias", "image_url": "", "content": f"Error: {str(e)}"}
                ])
        
        threading.Thread(target=fetch_news, daemon=True).start()

    def check_updates(self):
        def fetch_version():
            try:
                local_version = "0.0.0"
                if os.path.exists(LOCAL_VERSION_PATH):
                    with open(LOCAL_VERSION_PATH, 'r') as f:
                        local_version = json.load(f).get("local_version", "0.0.0")
                
                response = requests.get(REMOTE_VERSION_URL, timeout=5)
                if response.status_code == 200:
                    remote_versions = response.json().get("versions", [])
                    updates = [v for v in remote_versions if version.parse(v) > version.parse(local_version)]
                    self.worker_signals.version_checked.emit(updates, local_version)
                else:
                    self.worker_signals.error_signal.emit("No se pudo conectar al servidor de actualizaciones.")
            except Exception as e:
                self.worker_signals.error_signal.emit(f"Error al verificar actualizaciones: {str(e)}")
        
        threading.Thread(target=fetch_version, daemon=True).start()

    def start_downloads(self):
        if self.downloading:
            return
        
        self.downloading = True
        self.play_button.setEnabled(False)
        self.pause_button.show()
        
        def download_update(version_str):
            try:
                url = REMOTE_ZIP_URL.replace("version", version_str)
                response = requests.get(url, stream=True, timeout=10)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                with open(ZIP_DEST, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if self.pause_download:
                            time.sleep(0.1)
                            continue
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            percent = int(100 * downloaded_size / total_size) if total_size else 0
                            speed = f"{downloaded_size / 1024:.1f} KB/s"
                            self.worker_signals.progress_signal.emit(
                                percent, speed, f"Descargando: {version_str}"
                            )
                
                self.worker_signals.download_complete.emit(version_str)
            except Exception as e:
                self.worker_signals.error_signal.emit(f"Error al descargar {version_str}: {str(e)}")
                self.downloading = False
                self.pause_download = False
                self.play_button.setEnabled(True)
                self.pause_button.hide()
        
        for version_str in self.available_updates:
            threading.Thread(target=download_update, args=(version_str,), daemon=True).start()

    def toggle_pause(self):
        self.pause_download = not self.pause_download
        self.pause_button.setText("⏸ PAUSAR DESCARGA" if self.pause_download else "▶ REANUDAR DESCARGA")

    def launch_game(self):
        if os.path.exists(GAME_EXECUTABLE):
            subprocess.Popen(GAME_EXECUTABLE)
        else:
            self.worker_signals.error_signal.emit("El juego no está instalado. Por favor, instálalo primero.")

    def show_help_menu(self):
        menu = QMenu(self)
        menu.addAction("Visitar Discord", lambda: QDesktopServices.openUrl(QUrl(DISCORD_URL)))
        menu.addAction("Ver notas de la versión", lambda: QDesktopServices.openUrl(QUrl(REMOTE_NOTES_URL)))
        menu.exec_(self.help_btn.mapToGlobal(QPoint(0, self.help_btn.height())))

    def show_recovery_menu(self):
        menu = QMenu(self)
        menu.addAction("Descargar instalador", self.download_installer)
        menu.exec_(self.recovery_btn.mapToGlobal(QPoint(0, self.recovery_btn.height())))

    def download_installer(self):
        if self.installing_game:
            return
        
        self.installing_game = True
        self.play_button.setEnabled(False)
        
        def install_game():
            try:
                response = requests.get(GAME_INSTALLER_URL, stream=True, timeout=10)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                with open("installer.zip", 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            percent = int(100 * downloaded_size / total_size) if total_size else 0
                            speed = f"{downloaded_size / 1024:.1f} KB/s"
                            self.worker_signals.game_install_progress.emit(
                                percent, speed, "Descargando instalador..."
                            )
                
                with zipfile.ZipFile("installer.zip", 'r') as zip_ref:
                    file_list = zip_ref.namelist()
                    total_files = len(file_list)
                    for i, file in enumerate(file_list):
                        zip_ref.extract(file, ".")
                        percent = int(100 * (i + 1) / total_files)
                        self.worker_signals.game_install_progress.emit(
                            percent, f"Extrayendo... {percent}%", f"Instalando: {file}"
                        )
                
                os.remove("installer.zip")
                self.worker_signals.game_install_status.emit("Instalación completada")
                self.play_button.setEnabled(True)
                self.installing_game = False
            except Exception as e:
                self.worker_signals.game_install_status.emit(f"Error: {str(e)}")
                self.installing_game = False
                self.play_button.setEnabled(True)
        
        threading.Thread(target=install_game, daemon=True).start()

    def _hide_progress_ui(self):
        self.progress.setValue(0)
        self.percent_label.setText("")
        self.details_label.setText("")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    launcher = ModernGameLauncher()
    launcher.show()
    sys.exit(app.exec_())