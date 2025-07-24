# 🎥 IP Camera Video Uploader

Este projeto é uma solução completa para gerenciamento de câmeras IP, que realiza:

- 📹 **Gravação automática** dos streams de câmeras IP.
- ☁️ **Upload diário automático** dos vídeos para o Google Drive (com organização em pastas por câmera e data).
- 📊 **Painel em Streamlit** para gerenciamento e visualização das câmeras configuradas.

---

## 📦 Estrutura do Projeto

```bash
.
├── app.py                  # Painel Streamlit
├── record.py              # Rotina de gravação com ffmpeg
├── upload.py              # Script de upload diário para o Google Drive
├── drive_client.py        # Cliente de integração com Google Drive
├── config/
│   └── cameras.json       # Lista de câmeras IP configuradas
├── recordings/            # Vídeos gravados (gerado automaticamente)
├── client_secrets.json    # Credenciais OAuth do Google
├── token.json             # Token OAuth gerado na primeira execução
├── Dockerfile
├── docker-compose.yml
└── README.md
````

---

## 🚀 Como usar

### 1. 🔧 Configuração inicial


1. **Crie um projeto no Google Cloud e configure o OAuth:**

* Habilite a [Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com)
* Crie uma credencial do tipo "OAuth Client ID"
* Faça o download do `client_secrets.json` e coloque-o na raiz do projeto

---

### 2. 📦 Instalação

```bash
# Clone o projeto
git clone https://github.com/seu-usuario/ip-camera-video-uploader.git
cd ip-camera-video-uploader

# Crie e ative o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# Instale as dependências
pip install -r requirements.txt
```

---

### 3. 🐳 Usando com Docker

#### Build do projeto:

```bash
docker-compose build
```

#### Inicie os serviços principais:

```bash
docker-compose up -d front recording
```

#### Para realizar upload manual (ou via cron):

```bash
docker-compose run --rm uploading
```

Você pode agendar esse comando no `cron` do host para executar diariamente, por exemplo:

```cron
0 2 * * * cd /caminho/do/projeto && docker-compose run --rm uploading
```

---

## 🧠 Funcionalidades

* 🎥 Gravações em `.mp4` com `ffmpeg`
* 📁 Uploads organizados no Google Drive:

  * `/Câmera 1/YYYY-MM-DD/video.mp4`
* ✅ Upload sem intervenção manual após primeira autenticação
* 🌐 Interface com Streamlit para visualizar e editar as câmeras

---

## ✅ Requisitos

* Python 3.8+
* Docker e Docker Compose (opcional)
* Conta no Google com Drive habilitado

---

## ✨ Exemplos de uso

### Streamlit rodando:

```
http://localhost:8501
```

### Pastas no Google Drive:

```
Google Drive/
  └── camera_1/
      └── 2025-07-24/
          └── camera_1_14-30.mp4
```

---

## 🛟 FAQ

### 🔐 O sistema precisa de autenticação toda vez?

Não. Após a primeira autenticação no navegador (OAuth), o token é salvo em `token.json` e reutilizado automaticamente.

### 📆 Posso agendar o upload com Docker?

Sim. Basta **não manter o serviço `uploading` ativo** no `docker-compose` e executá-lo sob demanda via cron ou agendador.

---

## 📜 Licença

Este projeto está sob a licença MIT.

---

## 🤝 Contribuição

Contribuições são bem-vindas! Sinta-se livre para abrir issues ou enviar PRs.