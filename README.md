# Auto_Cadastro_PfSense
Uma aplicação desktop desenvolvida em Python com PyQt5 para adicionar usuários em massa no pfSense através de sua API REST

📋 Funcionalidades

    Importação de usuários a partir de arquivos Excel (.xls, .xlsx)

    Validação de dados dos usuários antes do envio

    Interface intuitiva com visualização em árvore dos usuários

    Envio assíncrono com barra de progresso e logs em tempo real

    Sistema de repetição para usuários que falharam no envio

    Backup automático dos dados enviados

    Registro de logs detalhado para auditoria

🚀 Pré-requisitos
No pfSense:

    Habilitar a API REST:

        Acessar: System > API

        Marcar: Enable REST API

        Configurar as permissões necessárias

    Criar um usuário de API:

        Acessar: System > User Manager

        Criar usuário com privilégios apropriados

        Gerar/definir token de API

No sistema:

    Python 3.7 ou superior

    pfSense com API REST habilitada

    Arquivo Excel com a estrutura correta

📦 Instalação

    Clone o repositório:

bash

git clone <url-do-repositorio>
cd pfsense-bulk-user-add

    Crie um ambiente virtual (recomendado):

bash

python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

    Instale as dependências:

bash

pip install -r requirements.txt

📊 Estrutura do Arquivo Excel

O arquivo Excel deve conter as seguintes colunas:

<img width="624" height="267" alt="image" src="https://github.com/user-attachments/assets/366de0ab-853b-4ae5-a102-02b26fc175ab" />

<img width="594" height="223" alt="image" src="https://github.com/user-attachments/assets/2ec01fd6-e9cc-478f-82ad-2f3e13329814" />




🖥️ Como Usar
1. Configuração Inicial

https://screenshots/main-screen.png

    Endereço do pfSense: Informe o IP ou hostname do seu pfSense

    Usuário API: Digite o nome do usuário criado para a API

    Token API: Insira o token de autenticação da API

2. Importar Usuários

    Clique em "Selecionar Arquivo Excel"

    Selecione seu arquivo Excel com os usuários

    Os usuários válidos serão exibidos na tabela

3. Enviar Usuários

    Clique em "Enviar Usuários"

    Aguarde o processo de envio na janela de progresso

    Verifique os logs para acompanhar o progresso

4. Reenviar Falhas

    Se houver usuários que falharam, use "Reenviar Não Enviados"

    Apenas os usuários com falha serão reenviados

🔧 Estrutura do Projeto

<img width="738" height="157" alt="image" src="https://github.com/user-attachments/assets/b2e91af3-e83f-401d-a74e-033227eb023e" />


⚙️ Configuração da API no pfSense
1. Habilitar API REST

    Acesse: System > API

    Marque: Enable REST API

    Configure as interfaces permitidas

2. Criar Usuário de API

    Acesse: System > User Manager > Add

    Defina:

        Username: nome do usuário API

        Password: senha forte

        Privileges: atribua privilégios apropriados

3. Gerar Token de API

    Use o comando no pfSense:

bash

# Gerar token para o usuário
pfSsh.php playback genToken <username>

🐛 Solução de Problemas
Erros Comuns:

    Conexão Recusada

        Verifique se o IP do pfSense está correto

        Confirme se a API REST está habilitada

    Autenticação Falhou

        Verifique usuário e token

        Confirme as permissões do usuário API

    Erro de Formato de Data

        Use o formato DD/MM/YYYY ou MM/DD/YYYY no Excel

    Usuários Não São Importados

        Verifique se a coluna "Status" contém "SIM"

Logs de Depuração:

Os logs detalhados são salvos em pfsense_user_add.log
📝 Exemplo de Arquivo Excel

Crie um arquivo Excel com esta estrutura:
python

import pandas as pd
from datetime import datetime

data = {
    'Nome': ['João Silva', 'Maria Santos', 'Pedro Costa'],
    'Usuário': [1001, 1002, 1003],
    'Password': [123456, 654321, 112233],
    'Expiração': ['31/12/2024', '31/12/2024', '31/12/2024'],
    'Status': ['SIM', 'SIM', 'NÃO']
}

df = pd.DataFrame(data)
df.to_excel('usuarios.xlsx', index=False)

🔒 Considerações de Segurança

    ⚠️ Não exponha a API para a internet sem proteção adequada

    🔑 Use tokens com tempo de expiração limitado

    📁 Mantenha backups seguros dos arquivos de configuração

    🚫 Não armazene senhas em claro nos arquivos Excel

📞 Suporte

Para problemas ou dúvidas:

    Verifique os logs em pfsense_user_add.log

    Confirme a configuração da API no pfSense

    Verifique o formato do arquivo Excel

📄 Licença

Este projeto foi feito para uso interno da AbcLink para suprir um necessidade.

🔄 Atualizações
Versão 1.0.0

    ✅ Importação de usuários a partir de Excel

    ✅ Interface gráfica com PyQt5

    ✅ Envio assíncrono com feedback visual

    ✅ Sistema de repetição para falhas

    ✅ Backup automático dos dados

    ✅ Logs detalhados de operação
