# Project Setup

## Prerequisites

I have used the following tools and versions to run this project:

- Python 3.9 or higher  
- pip  
- Git  
- GCC (required for executing C programs)

To verify installation:

python --version  
pip --version  
gcc --version  

---

## Clone the Repository

git clone https://github.com/muonorb/Epariksha.git  
cd Epariksha

---

## Create and Activate Virtual Environment

### Windows

python -m venv venv  
venv\Scripts\activate  

### macOS / Linux

python3 -m venv venv  
source venv/bin/activate  

Once activated, `(venv)` will appear in the terminal.

---

## Install Dependencies

pip install --upgrade pip  
pip install -r requirements.txt  

---

## Apply Database Migrations

python manage.py makemigrations  
python manage.py migrate  

---

## Create Superuser/Admin (Optional)

python manage.py createsuperuser  

Follow the prompts to create an admin user.

---

## Run the Project

python manage.py runserver  

Open the application in the browser:

http://127.0.0.1:8000/  

Admin panel:

http://127.0.0.1:8000/admin/  

---
