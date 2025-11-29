# Access System (ALSS) - Setup Guide

This repository contains the Access System (ALSS) project. Follow the steps below to set up and run the application locally.

---

## Prerequisites

Before starting, make sure you have the following installed on your machine:

- [Git](https://git-scm.com/)
- [Node.js](https://nodejs.org/)
- [Python 3.13+](https://www.python.org/downloads/) (for the backend)
- [SQLite / PostgreSQL / MySQL] depending on your database configuration
- Optional: [VS Code](https://code.visualstudio.com/) 

## Setup Instructions

1. **Create a new directory** called `tracer`:

   mkdir tracer
2.Navigate to the directory:
    cd tracer
3. Clone the repository:git clone https://github.com/wikunzabrivian-arch/Atss.git

4. cd Atss/backend

    Copy code
5. cd ../frontend
    Run npm install to install dependencies to run frontend use npm run dev
6. fter running the frontend server, click on the localhost link shown in the terminal ( http://127.0.0.1:3000) to access the application in your browser
7. If you encounter errors like InconsistentMigrationHistory, you can run:python manage.py migrate --fake
8. Or reset the database:
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
