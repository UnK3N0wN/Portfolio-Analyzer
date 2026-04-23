# 📊 Portfolio Analyzer

A Django-based web application to track, analyze, and manage investment portfolios with features like stock tracking, price alerts, and AI-powered insights.

---

## 🚀 Features

* 📈 Track stock investments and holdings
* 💰 Buy & sell assets with transaction history
* 🔔 Set price alerts for stocks
* 🤖 AI-powered insights (portfolio_ai module)
* 📊 Dashboard with portfolio overview
* 👤 User authentication system
* 📋 Watchlist management

---

## 🛠️ Tech Stack

* **Backend:** Python, Django
* **Frontend:** HTML, CSS, JavaScript
* **Database:** SQLite (development)
* **Other Tools:** webhint (code quality), Git

---

## 📁 Project Structure

```
ai_portfolio/
│
├── ai/                # AI-related logic
├── portfolio/         # Core portfolio app
├── portfolio_ai/      # AI integration
├── stocks/            # Stock-related features
├── users/             # Authentication & users
├── templates/         # HTML templates
├── static/            # CSS, JS, images
├── manage.py          # Django entry point
├── Schema.sql         # Database schema
└── README.md
```

---

## ⚙️ Installation & Setup

### Use python 3.12 version for few packages to support

### 1. Clone the repository

```bash
git clone https://github.com/UnK3N0wN/Portfolio-Analyzer.git
cd Portfolio-Analyzer
```

### 2. Create virtual environment

```bash
python -m venv venv
venv\Scripts\activate   # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Run server

```bash
python manage.py runserver
```

---

## 📸 Screenshots

*Add screenshots of your dashboard, portfolio page, etc.*

---

## 📌 Future Improvements

* 🔐 Add JWT authentication
* ☁️ Deploy on cloud (AWS/Render)
* 📊 Advanced analytics & charts
* 📡 Live stock API integration

---

## 🤝 Contributing

Contributions are welcome! Feel free to fork this repo and submit a pull request.

---

## 📄 License

This project is for educational purposes.

---

## 👨‍💻 Author

**Blesson**
GitHub: https://github.com/UnK3N0wN

---

⭐ If you like this project, consider giving it a star!
