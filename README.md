<div align="center">

# 🌱 Green Journey Advisor

**Sustainable Travel Planning & Booking Platform for the UK**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4+-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

<br>

### 🎥 Project Demo Video (2–3 min walkthrough)

[![Green Journey Advisor Demo](https://img.youtube.com/vi/AN8vrBRv02M/0.jpg)](https://youtu.be/AN8vrBRv02M?si=t0RQrUnYKv3vTHDo)

**Click the image above or →** [Watch Full Demo on YouTube](https://youtu.be/AN8vrBRv02M?si=t0RQrUnYKv3vTHDo)

</div>

<br>

## ✨ Overview

**Green Journey Advisor** is a full-stack web application designed to help users plan and book environmentally conscious journeys across the UK.

The platform empowers travelers to make informed decisions by providing transparent CO₂ emission data, cost comparisons, and student-friendly discounts — all wrapped in a modern, responsive interface.

### Core Philosophy
> Sustainable travel should be **easy**, **affordable**, and **transparent**.

<br>

## 🎯 Key Features

- 🔍 Smart journey search (origin → destination, one-way/return, date, passengers)
- 🌍 Real CO₂ emissions comparison with visual progress bars
- 💰 Automatic highlighting of student discounts
- 📊 Complete booking flow: search → select → confirm → payment simulation → ticket
- 🎫 Downloadable ticket with QR code (transaction reference)
- 👤 User accounts with booking history, modification & cancellation
- 📱 Fully responsive design + mobile menu
- ⚡ Modern UI with smooth animations & Tailwind CSS
- 🛡️ Secure session management & input validation

<br>

## 🛠️ Tech Stack

| Layer            | Technology                          | Purpose                                 |
|------------------|-------------------------------------|-----------------------------------------|
| Backend          | Python • Flask                      | REST-like routing, business logic       |
| Database         | MySQL                               | Persistent storage of journeys/bookings |
| Frontend         | Jinja2 • Tailwind CSS • JavaScript  | Dynamic templates & modern styling      |
| Session          | Flask-Session (filesystem)          | User authentication & state             |
| QR Code          | qrcode.js                           | Ticket generation                       |
| Styling          | Tailwind CSS + custom gradients     | Clean, responsive, professional look    |
| Deployment-ready | requirements.txt + .gitignore       | Easy local & cloud deployment           |

<br>

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- MySQL 8.0+ (or compatible)
- Git

### Quick Setup (Local Development)

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/green-journey-advisor.git
cd green-journey-advisor

# 2. Create & activate virtual environment
python -m venv venv
source venv/bin/activate    # Linux/macOS
venv\Scripts\activate       # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file (example)
cp .env.example .env        # if you have example file
# Then edit .env with your MySQL credentials

# 5. Create and initialize database
# → Use MySQL Workbench / terminal to create database 'green_journey_db'
# → Import schema (if you have .sql file) or let app create tables

# 6. Run the application
flask run
# or
python app.py
