import sys
import os
import json
import logging
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QLineEdit, QPushButton, QFileDialog,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QMessageBox, QDialog,
    QProgressBar, QTextBrowser, QHBoxLayout, QGridLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
import pandas as pd
from datetime import datetime
import requests
import re
import xlrd
import urllib3
from urllib.parse import urljoin

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuração do logger para arquivo
logging.basicConfig(
    filename='pfsense_user_add.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

class WorkerThread(QThread):
    progress_update = pyqtSignal(int, int, str)
    log_update = pyqtSignal(str)
    finished = pyqtSignal()
    unsent_users_signal = pyqtSignal(list)

    def __init__(self, api_url, auth_credentials, users_data):
        super().__init__()
        self.api_url = api_url
        self.auth_credentials = auth_credentials
        self.users_data = users_data
        self.unsent_users = []

    def run(self):
        total_users = len(self.users_data)
        for i, user_data in enumerate(self.users_data, start=1):
            try:
                response = requests.post(
                    self.api_url, 
                    auth=self.auth_credentials, 
                    json=user_data, 
                    verify=False, 
                    timeout=10
                )
                
                if response.status_code == 200:
                    log_message = f"[SUCESSO] Usuário '{user_data['descr']}' adicionado."
                    logging.info(log_message)
                    self.progress_update.emit(i, total_users, "success")
                else:
                    log_message = f"[ERRO] Usuário '{user_data['descr']}' não foi adicionado. Status: {response.status_code}, Resposta: {response.text}"
                    self.unsent_users.append(user_data)
                    logging.error(log_message)
                    self.progress_update.emit(i, total_users, "error")
                    
            except requests.exceptions.ConnectionError:
                log_message = f"[ERRO] Falha na conexão com o pfSense. Verifique o endereço IP e a conectividade."
                self.unsent_users.append(user_data)
                logging.error(log_message)
                self.progress_update.emit(i, total_users, "error")
            except requests.exceptions.Timeout:
                log_message = f"[ERRO] Timeout ao conectar com o pfSense."
                self.unsent_users.append(user_data)
                logging.error(log_message)
                self.progress_update.emit(i, total_users, "error")
            except Exception as e:
                log_message = f"[ERRO] Usuário '{user_data['descr']}' não foi adicionado. Detalhes: {e}"
                self.unsent_users.append(user_data)
                logging.error(log_message)
                self.progress_update.emit(i, total_users, "error")
                
            self.log_update.emit(log_message)

        self.unsent_users_signal.emit(self.unsent_users)
        self.finished.emit()

class LoadingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enviando Usuários para pfSense")
        self.setFixedSize(600, 350)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        self.progressBar = QProgressBar()
        self.progressBar.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progressBar)

        self.log_text = QTextBrowser()
        self.log_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.log_text)

        self.worker_thread = None

    def start_process(self, api_url, auth_credentials, users_data):
        self.worker_thread = WorkerThread(api_url, auth_credentials, users_data)
        self.worker_thread.progress_update.connect(self.update_progress)
        self.worker_thread.log_update.connect(self.update_log)
        self.worker_thread.finished.connect(self.process_finished)
        self.worker_thread.unsent_users_signal.connect(self.unsent_users_received)
        self.worker_thread.start()

    def update_progress(self, value, max_value, status):
        percent = int((value / max_value) * 100)
        self.progressBar.setValue(percent)

    def update_log(self, message):
        self.log_text.append(message)
        # Scroll to bottom
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def process_finished(self):
        self.accept()

    def unsent_users_received(self, unsent_users):
        if unsent_users:
            QMessageBox.warning(self, "Aviso", f"{len(unsent_users)} usuários não foram enviados corretamente. Use o botão 'Reenviar Não Enviados' para tentar novamente.")
        else:
            QMessageBox.information(self, "Sucesso", "Todos os usuários foram enviados com sucesso!")

class PFsenseBulkUserAddApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.pfsense_ip = QLineEdit("192.168.56.103")
        self.client_id = QLineEdit()
        self.client_token = QLineEdit()
        self.client_token.setEchoMode(QLineEdit.Password)

        self.excel_file_path = None
        self.unsent_users = []

        self.init_ui()

        # Garantir diretório de backups
        self.backup_dir = "backups"
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Configuração do pfSense
        config_group = QWidget()
        config_layout = QGridLayout(config_group)
        config_layout.addWidget(QLabel("Endereço do pfSense:"), 0, 0)
        config_layout.addWidget(self.pfsense_ip, 0, 1)
        config_layout.addWidget(QLabel("Usuário API:"), 1, 0)
        config_layout.addWidget(self.client_id, 1, 1)
        config_layout.addWidget(QLabel("Token API:"), 2, 0)
        config_layout.addWidget(self.client_token, 2, 1)
        
        main_layout.addWidget(config_group)
        
        # Seleção de arquivo
        file_layout = QHBoxLayout()
        self.browse_file_button = QPushButton("Selecionar Arquivo Excel")
        self.browse_file_button.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_file_button)
        
        self.file_label = QLabel("Nenhum arquivo selecionado")
        file_layout.addWidget(self.file_label)
        file_layout.addStretch()
        
        main_layout.addLayout(file_layout)

        # Lista de usuários
        self.users_tree = QTreeWidget()
        self.users_tree.setColumnCount(5)
        self.users_tree.setHeaderLabels(["Nome", "Usuário", "Senha", "Expiração", "Status"])
        self.users_tree.setSortingEnabled(True)
        main_layout.addWidget(self.users_tree)

        # Botões
        buttons_layout = QHBoxLayout()
        self.send_users_button = QPushButton("Enviar Usuários")
        self.send_users_button.clicked.connect(self.send_users_to_pfSense)
        buttons_layout.addWidget(self.send_users_button)

        self.retry_unsent_button = QPushButton("Reenviar Não Enviados")
        self.retry_unsent_button.clicked.connect(self.retry_unsent_users)
        self.retry_unsent_button.setEnabled(False)
        buttons_layout.addWidget(self.retry_unsent_button)

        self.clear_list_button = QPushButton("Limpar Lista")
        self.clear_list_button.clicked.connect(self.clear_users_list)
        buttons_layout.addWidget(self.clear_list_button)

        main_layout.addLayout(buttons_layout)

        self.setGeometry(200, 150, 900, 650)
        self.setWindowTitle("Auto Cadastro pfSense - AbcLink")

        # Estilo aprimorado
        self.setStyleSheet("""
            QMainWindow { background-color: #f4f7f9; }
            QLabel { font-size: 12pt; color: #222; }
            QLineEdit { font-size: 11pt; padding: 6px; border: 1px solid #aaa; border-radius: 4px; }
            QPushButton {
                font-size: 12pt;
                background-color: #2874A6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                min-width: 130px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1b4f72;
            }
            QPushButton:disabled {
                background-color: #a6a6a6;
            }
            QTreeWidget {
                font-size: 11pt;
                background-color: #ffffff;
                border: 1px solid #bbb;
                border-radius: 6px;
            }
            QTreeWidget::item:selected {
                background-color: #2874A6;
                color: white;
            }
        """)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Selecionar Arquivo Excel", 
            "", 
            "Excel Files (*.xls *.xlsx)"
        )
        if file_path:
            self.excel_file_path = file_path
            self.file_label.setText(os.path.basename(file_path))
            self.show_users_in_tree()

    def validate_user_data(self, username, password, expiration):
        """Valida os dados do usuário"""
        errors = []
        
        if not username or not username.strip():
            errors.append("Usuário não pode estar vazio")
            
        if not password or not password.strip():
            errors.append("Senha não pode estar vazia")
            
        if not re.match(r'^\d+$', username):
            errors.append("Usuário deve conter apenas números")
            
        if not re.match(r'^\d+$', password):
            errors.append("Senha deve conter apenas números")
            
        try:
            datetime.strptime(expiration, "%m/%d/%Y")
        except ValueError:
            errors.append(f"Data de expiração inválida: {expiration}. Use o formato MM/DD/YYYY")
            
        return errors

    def show_users_in_tree(self):
        try:
            if self.excel_file_path.endswith(".xls"):
                df = pd.read_excel(self.excel_file_path, engine="xlrd")
            else:
                df = pd.read_excel(self.excel_file_path, engine="openpyxl")

            # Verificação de colunas com tolerância a variações
            col_mapping = {
                "nome": "Full Name",
                "usuário": "Username", 
                "password": "Password",
                "expiração": "Expiration",
                "status": "Status"
            }
            
            # Padronizar nomes de colunas
            df.columns = [col.strip().lower() for col in df.columns]
            df.rename(columns=col_mapping, inplace=True)
            
            # Verificar colunas necessárias
            required_cols = ["Full Name", "Username", "Password", "Expiration", "Status"]
            for col in required_cols:
                if col not in df.columns:
                    raise ValueError(f"Coluna '{col}' não encontrada no arquivo.")

            df = df[required_cols]
            
            # Limpeza dos dados
            df["Username"] = df["Username"].astype(str).apply(lambda x: re.sub(r"\D", "", x))
            df["Password"] = df["Password"].astype(str).apply(lambda x: re.sub(r"\D", "", x))
            df = df[df["Status"].str.upper() == "SIM"]

            self.users_tree.clear()
            invalid_users = []
            
            for _, row in df.iterrows():
                formatted_date = self.format_to_mm_dd_yyyy(row["Expiration"])
                
                # Validar dados do usuário
                validation_errors = self.validate_user_data(
                    row["Username"], row["Password"], formatted_date
                )
                
                if validation_errors:
                    invalid_users.append(f"{row['Full Name']}: {', '.join(validation_errors)}")
                    continue
                    
                user_item = QTreeWidgetItem([
                    row["Full Name"], row["Username"], row["Password"], formatted_date, "Pendente"
                ])
                self.users_tree.addTopLevelItem(user_item)

            if invalid_users:
                QMessageBox.warning(
                    self, 
                    "Usuários com problemas", 
                    f"{len(invalid_users)} usuários não serão processados devido a erros:\n\n" + 
                    "\n".join(invalid_users[:5]) + 
                    ("\n..." if len(invalid_users) > 5 else "")
                )
                
            QMessageBox.information(
                self, 
                "Sucesso", 
                f"{self.users_tree.topLevelItemCount()} usuários válidos carregados para envio."
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Erro ao carregar arquivo", f"Erro: {str(e)}")
            logging.error(f"Erro ao carregar arquivo Excel: {e}")

    def format_to_mm_dd_yyyy(self, date_value):
        try:
            if isinstance(date_value, str):
                # Tentar diferentes formatos de data
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y", "%m-%d-%Y"):
                    try:
                        return datetime.strptime(date_value, fmt).strftime("%m/%d/%Y")
                    except ValueError:
                        continue
                return date_value  # Retorna original se não conseguir converter
            else:
                return pd.to_datetime(date_value).strftime("%m/%d/%Y")
        except Exception:
            return ""

    def prepare_users_data(self):
        users = []
        for i in range(self.users_tree.topLevelItemCount()):
            item = self.users_tree.topLevelItem(i)
            users.append({
                "name": item.text(1),
                "password": item.text(2),
                "descr": item.text(0),
                "expires": item.text(3),
                "scope": "user",
                "priv": [],
                "disabled": False
            })
        return users

    def send_users_to_pfSense(self):
        ip = self.pfsense_ip.text().strip()
        if not ip:
            QMessageBox.warning(self, "IP não informado", "Por favor, informe o endereço IP do pfSense.")
            return
            
        api_url = f"https://{ip}/api/v2/user"
        auth_credentials = (self.client_id.text(), self.client_token.text())

        if not self.client_id.text() or not self.client_token.text():
            QMessageBox.warning(self, "Campos Vazios", "Por favor, preencha o Client ID e Client Token.")
            return

        if self.users_tree.topLevelItemCount() == 0:
            QMessageBox.warning(self, "Sem Usuários", "Não há usuários para enviar. Selecione um arquivo Excel válido.")
            return

        # Testar conexão com o pfSense
        try:
            test_response = requests.get(
                f"https://{ip}/api/v2/system/version", 
                auth=auth_credentials, 
                verify=False, 
                timeout=5
            )
            if test_response.status_code != 200:
                QMessageBox.critical(
                    self, 
                    "Erro de Conexão", 
                    f"Não foi possível conectar ao pfSense. Status: {test_response.status_code}"
                )
                return
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Erro de Conexão", 
                f"Não foi possível conectar ao pfSense: {str(e)}"
            )
            return

        users_data = self.prepare_users_data()

        # Backup dos dados atuais
        self.save_backup(users_data)

        self.loading_dialog = LoadingDialog(self)
        self.loading_dialog.start_process(api_url, auth_credentials, users_data)
        self.loading_dialog.exec_()

        # Após o processo, salvar usuários não enviados para reenviar
        self.unsent_users = self.loading_dialog.worker_thread.unsent_users if self.loading_dialog.worker_thread else []

        self.retry_unsent_button.setEnabled(bool(self.unsent_users))
        
        # Atualizar status na árvore
        self.update_tree_status()

    def update_tree_status(self):
        """Atualiza o status dos usuários na árvore com base nos não enviados"""
        unsent_usernames = [user['name'] for user in self.unsent_users]
        
        for i in range(self.users_tree.topLevelItemCount()):
            item = self.users_tree.topLevelItem(i)
            username = item.text(1)
            if username in unsent_usernames:
                item.setText(4, "Falhou")
            else:
                item.setText(4, "Enviado")

    def retry_unsent_users(self):
        if not self.unsent_users:
            QMessageBox.information(self, "Nenhum usuário", "Não há usuários para reenviar.")
            self.retry_unsent_button.setEnabled(False)
            return

        ip = self.pfsense_ip.text().strip()
        api_url = f"https://{ip}/api/v2/user"
        auth_credentials = (self.client_id.text(), self.client_token.text())

        self.loading_dialog = LoadingDialog(self)
        self.loading_dialog.start_process(api_url, auth_credentials, self.unsent_users)
        self.loading_dialog.exec_()

        self.unsent_users = self.loading_dialog.worker_thread.unsent_users if self.loading_dialog.worker_thread else []
        self.retry_unsent_button.setEnabled(bool(self.unsent_users))
        
        # Atualizar status na árvore
        self.update_tree_status()

    def clear_users_list(self):
        self.users_tree.clear()
        self.unsent_users = []
        self.retry_unsent_button.setEnabled(False)
        self.file_label.setText("Nenhum arquivo selecionado")
        self.excel_file_path = None
        QMessageBox.information(self, "Lista limpa", "A lista de usuários foi limpa.")

    def save_backup(self, users_data):
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = os.path.join(self.backup_dir, f"backup_users_{now}.json")
        try:
            with open(backup_filename, 'w', encoding='utf-8') as f:
                json.dump(users_data, f, ensure_ascii=False, indent=4)
            logging.info(f"Backup dos usuários salvo em {backup_filename}")
        except Exception as e:
            logging.error(f"Erro ao salvar backup: {e}")

def main():
    app = QApplication(sys.argv)
    
    # Definir ícone da aplicação (se disponível)
    if os.path.exists("icon.png"):
        app.setWindowIcon(QIcon("icon.png"))
    
    window = PFsenseBulkUserAddApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
