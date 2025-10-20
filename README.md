# ⚙️ FastAPI roject Setup

---

# 1. Project Environment to run FastAPI app/server :

### cd fastapi_project

### Create a virtual environment
python -m venv venv

### Activate the virtual environment
### On Windows:
venv\Scripts\activate

### On macOS/Linux:
source venv/bin/activate

----------------------

# 2. Install All Required Packages:

- Core FastAPI + Server + Templating:
  pip install fastapi uvicorn jinja2 python-multipart

- Database (PostgreSQL):
  pip install psycopg2-binary

- Web Requests & Parsing:
  pip install requests beautifulsoup4 urllib3

- Async + Security + CORS:
  pip install aiofiles slowapi python-dotenv

- Authentication (JWT, OAuth2):
  pip install python-jose passlib[bcrypt]

- Utilities:
  pip install pydantic email-validator

- (Logging, HTML):
  pip install loguru

-------------------------

# 3. You need a requirements.txt:

fastapi  
uvicorn  
jinja2  
python-multipart  
psycopg2-binary  
requests  
beautifulsoup4  
urllib3  
aiofiles  
slowapi  
python-dotenv  
python-jose  
passlib[bcrypt]  
pydantic  
email-validator  
loguru  

## Then install everything with:
pip install -r requirements.txt

------------------------

# 4. Run the Server

python -m uvicorn main:app --host 0.0.0.0 --port your_port --reload

Then open:
http://localhost:your_port
