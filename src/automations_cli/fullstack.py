#!/usr/bin/env python3
"""
FastAPI + React Project Generator
Automates the creation of a full-stack project with FastAPI backend and React frontend.
"""

from pathlib import Path
import textwrap


def create_file(filepath: Path, content: str):
    """Create a file with the given content, creating parent directories if needed."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(textwrap.dedent(content).strip() + "\n", encoding='utf-8')
    print(f"[OK] Created: {filepath}")


def create_backend(root: Path, project_name: str):
    """Create the FastAPI backend."""
    backend = root / "backend"
    # Use src layout with project name: src/{project_name}
    # Replace hyphens with underscores for valid Python package name
    package_name = project_name.replace("-", "_")
    src_app = backend / "src" / package_name

    # pyproject.toml
    create_file(backend / "pyproject.toml", f"""
    [build-system]
    requires = ["hatchling"]
    build-backend = "hatchling.build"

    [project]
    name = "{project_name}"
    version = "0.1.0"
    description = "FastAPI backend"
    requires-python = ">=3.10"
    dependencies = [
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "sqlalchemy>=2.0.0",
        "pydantic-settings>=2.0.0",
        "python-dotenv>=1.0.0",
    ]

    [project.scripts]
    dev = "{package_name}.scripts:dev"
    start = "{package_name}.scripts:start"
    alembic-init = "{package_name}.scripts:alembic_init"
    db-migrate = "{package_name}.scripts:run_migrations"
    db-upgrade = "{package_name}.scripts:upgrade_db"

    [tool.hatch.build.targets.wheel]
    packages = ["src/{package_name}"]
    """)

    # .env
    create_file(backend / ".env", f"""
    DATABASE_URL=sqlite:///./{project_name}.db
    SECRET_KEY=your-secret-key-change-in-production
    DEBUG=True
    """)

    # src/{project_name}/__init__.py
    create_file(src_app / "__init__.py", """
    __version__ = "0.1.0"
    """)

    # src/{project_name}/main.py
    create_file(src_app / "main.py", f"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from {package_name}.core.config import settings
    from {package_name}.routers import health

    app = FastAPI(
        title="FastAPI Backend",
        description="Backend API for the application",
        version="0.1.0"
    )

    # CORS configuration for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],  # Vite default port
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router, prefix="/api", tags=["health"])

    @app.get("/")
    async def root():
        return {{"message": "Welcome to FastAPI Backend", "version": "0.1.0"}}
    """)

    # src/{project_name}/scripts.py - Development and deployment scripts
    scripts_content = f'''
import subprocess
import sys
import os
from pathlib import Path


def dev():
    """Run the development server with auto-reload."""
    backend_dir = Path(__file__).parent.parent.parent
    env = dict(**os.environ)
    env['PYTHONPATH'] = f"{{backend_dir}}/src:{{env.get('PYTHONPATH', '')}}"
    
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "{package_name}.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
    ]
    subprocess.run(cmd, cwd=str(backend_dir), env=env)


def start():
    """Run the production server."""
    backend_dir = Path(__file__).parent.parent.parent
    env = dict(**os.environ)
    env['PYTHONPATH'] = f"{{backend_dir}}/src:{{env.get('PYTHONPATH', '')}}"
    
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "{package_name}.main:app",
        "--host", "0.0.0.0",
        "--port", "8000"
    ]
    subprocess.run(cmd, cwd=str(backend_dir), env=env)


def alembic_init():
    """Initialize Alembic for database migrations."""
    backend_dir = Path(__file__).parent.parent.parent
    env = dict(**os.environ)
    env['PYTHONPATH'] = f"{{backend_dir}}/src:{{env.get('PYTHONPATH', '')}}"
    
    cmd = [
        sys.executable, "-m", "alembic", "init", "alembic"
    ]
    subprocess.run(cmd, cwd=str(backend_dir), env=env)


def run_migrations():
    """Generate database migrations."""
    backend_dir = Path(__file__).parent.parent.parent
    env = dict(**os.environ)
    env['PYTHONPATH'] = f"{{backend_dir}}/src:{{env.get('PYTHONPATH', '')}}"
    
    cmd = [
        sys.executable, "-m", "alembic", "revision", "--autogenerate", "-m", "Initial migration"
    ]
    subprocess.run(cmd, cwd=str(backend_dir), env=env)


def upgrade_db():
    """Upgrade the database to the latest migration."""
    backend_dir = Path(__file__).parent.parent.parent
    env = dict(**os.environ)
    env['PYTHONPATH'] = f"{{backend_dir}}/src:{{env.get('PYTHONPATH', '')}}"
    
    cmd = [
        sys.executable, "-m", "alembic", "upgrade", "head"
    ]
    subprocess.run(cmd, cwd=str(backend_dir), env=env)


if __name__ == "__main__":
    dev()
'''
    create_file(src_app / "scripts.py", scripts_content)

    # src/{project_name}/core/__init__.py
    create_file(src_app / "core" / "__init__.py", "")

    # src/{project_name}/core/config.py
    create_file(src_app / "core" / "config.py", f"""
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        database_url: str = "sqlite:///./{project_name}.db"
        secret_key: str = "your-secret-key"
        debug: bool = True

        model_config = SettingsConfigDict(
            env_file=".env",
            case_sensitive=False
        )

    settings = Settings()
    """)

    # src/{project_name}/db/__init__.py
    create_file(src_app / "db" / "__init__.py", "")

    # src/{project_name}/db/database.py
    database_content = f'''
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, declarative_base
    from {package_name}.core.config import settings

    engine = create_engine(
        settings.database_url,
        connect_args={{"check_same_thread": False}} if "sqlite" in settings.database_url else {{}}
    )

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()

    def get_db():
        """Dependency for getting database session."""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    '''
    create_file(src_app / "db" / "database.py", database_content)

    # src/{project_name}/models/__init__.py
    create_file(src_app / "models" / "__init__.py", "")

    # Create the content as a variable to avoid f-string + triple quote issues
    models_base_content = f'''
    from sqlalchemy import Column, Integer, DateTime
    from datetime import datetime
    from {package_name}.db.database import Base

    class BaseModel(Base):
        \'\'\'Base model with common fields for all models.\'\'\'
        __abstract__ = True

        id = Column(Integer, primary_key=True, index=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Example model - uncomment and modify as needed
    # class User(BaseModel):
    #     __tablename__ = "users"
    #
    #     email = Column(String, unique=True, index=True, nullable=False)
    #     username = Column(String, unique=True, index=True, nullable=False)
    #     hashed_password = Column(String, nullable=False)
    '''
    create_file(src_app / "models" / "base.py", models_base_content)

    # src/{project_name}/schemas/__init__.py
    create_file(src_app / "schemas" / "__init__.py", "")

    # Create the schemas/health.py content as a variable
    schemas_health_content = f'''
    from pydantic import BaseModel
    from datetime import datetime

    class HealthResponse(BaseModel):
        \'\'\'Schema for health check response.\'\'\'
        status: str
        timestamp: datetime
        service: str

        class Config:
            json_schema_extra = {{
                "example": {{
                    "status": "healthy",
                    "timestamp": "2024-01-01T00:00:00",
                    "service": "FastAPI Backend"
                }}
            }}

    # Example schemas - uncomment and modify as needed
    # class UserBase(BaseModel):
    #     email: str
    #     username: str
    #
    # class UserCreate(UserBase):
    #     password: str
    #
    # class UserResponse(UserBase):
    #     id: int
    #     created_at: datetime
    #
    #     class Config:
    #         from_attributes = True
    '''
    create_file(src_app / "schemas" / "health.py", schemas_health_content)

    # src/{project_name}/routers/__init__.py
    create_file(src_app / "routers" / "__init__.py", "")

    # Create the routers/health.py content as a variable
    routers_health_content = f'''
    from fastapi import APIRouter
    from datetime import datetime
    from {package_name}.schemas.health import HealthResponse

    router = APIRouter()

    @router.get("/health", response_model=HealthResponse)
    async def health_check():
        \'\'\'Health check endpoint with proper schema validation.\'\'\'
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            service="FastAPI Backend"
        )
    '''
    create_file(src_app / "routers" / "health.py", routers_health_content)


def create_frontend(root: Path):
    """Create the React frontend with Vite."""
    frontend = root / "frontend"
    src = frontend / "src"

    # package.json
    create_file(frontend / "package.json", """
    {
      "name": "frontend",
      "private": true,
      "version": "0.1.0",
      "type": "module",
      "scripts": {
        "dev": "vite",
        "build": "vite build",
        "preview": "vite preview"
      },
      "dependencies": {
        "react": "^18.2.0",
        "react-dom": "^18.2.0",
        "axios": "^1.6.0"
      },
      "devDependencies": {
        "@types/react": "^18.2.0",
        "@types/react-dom": "^18.2.0",
        "@vitejs/plugin-react": "^4.2.0",
        "vite": "^5.0.0"
      }
    }
    """)

    # vite.config.js
    create_file(frontend / "vite.config.js", """
    import { defineConfig } from 'vite'
    import react from '@vitejs/plugin-react'

    export default defineConfig({
      plugins: [react()],
      server: {
        port: 5173,
        proxy: {
          '/api': {
            target: 'http://localhost:8000',
            changeOrigin: true,
          }
        }
      }
    })
    """)

    # index.html
    create_file(frontend / "index.html", """
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>FastAPI + React App</title>
      </head>
      <body>
        <div id="root"></div>
        <script type="module" src="/src/main.jsx"></script>
      </body>
    </html>
    """)

    # src/main.jsx
    create_file(src / "main.jsx", """
    import React from 'react'
    import ReactDOM from 'react-dom/client'
    import App from './App'
    import './index.css'

    ReactDOM.createRoot(document.getElementById('root')).render(
      <React.StrictMode>
        <App />
      </React.StrictMode>,
    )
    """)

    # src/App.jsx
    create_file(src / "App.jsx", """
    import { useState, useEffect } from 'react'
    import axios from 'axios'

    function App() {
      const [health, setHealth] = useState(null)
      const [loading, setLoading] = useState(true)
      const [error, setError] = useState(null)

      useEffect(() => {
        const checkHealth = async () => {
          try {
            const response = await axios.get('/api/health')
            setHealth(response.data)
            setLoading(false)
          } catch (err) {
            setError(err.message)
            setLoading(false)
          }
        }

        checkHealth()
      }, [])

      return (
        <div className="container">
          <h1>FastAPI + React</h1>
          <div className="card">
            <h2>Backend Health Check</h2>
            {loading && <p>Loading...</p>}
            {error && <p className="error">Error: {error}</p>}
            {health && (
              <div className="success">
                <p>Status: {health.status}</p>
                <p>Service: {health.service}</p>
                <p>Timestamp: {health.timestamp}</p>
              </div>
            )}
          </div>
          <p className="info">
            Edit <code>src/App.jsx</code> and save to test HMR
          </p>
        </div>
      )
    }

    export default App
    """)

    # src/index.css
    create_file(src / "index.css", """
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
        'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
        sans-serif;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      background: #242424;
      color: rgba(255, 255, 255, 0.87);
    }

    .container {
      max-width: 800px;
      margin: 0 auto;
      padding: 2rem;
      text-align: center;
    }

    h1 {
      font-size: 3rem;
      margin-bottom: 2rem;
      background: linear-gradient(45deg, #646cff, #535bf2);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }

    .card {
      background: #1a1a1a;
      padding: 2rem;
      border-radius: 8px;
      margin: 2rem 0;
    }

    .card h2 {
      margin-bottom: 1rem;
    }

    .success {
      color: #4ade80;
    }

    .error {
      color: #f87171;
    }

    .info {
      color: #888;
      margin-top: 2rem;
    }

    code {
      background: #1a1a1a;
      padding: 0.2rem 0.4rem;
      border-radius: 4px;
      font-family: 'Courier New', monospace;
    }
    """)

    # Create public directory
    (frontend / "public").mkdir(parents=True, exist_ok=True)


def create_gitignore(root: Path):
    """Create a .gitignore file for the fullstack project."""
    gitignore_content = """
# Python
*.pyc
__pycache__/
*.pyo
*.pyd
.Python
env/
venv/
.venv/
pip-wheel-metadata/
build/
dist/
*.egg-info/

# Logs
logs/
*.log

# IDEs and editors
.vscode/
.idea/
*.sublime-*

# OS generated files
.DS_Store
Thumbs.db

# Testing
.coverage
coverage.xml
*.cover

# Virtual environments
.venv/

# Node.js
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
dist/
build/

# Environment variables
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# Database
*.db
*.db-journal

# Vite
!.vite/

# Backend specific
backend/.venv/
backend/__pycache__/

# Frontend specific
frontend/dist/
frontend/.vite/
frontend/node_modules/
"""
    create_file(root / ".gitignore", gitignore_content)


def create_readme(root: Path, project_name: str):
    """Create README with setup instructions."""
    create_file(root / "README.md", f"""
    # {project_name}

    Full-stack application with FastAPI backend and React frontend.

    ## Project Structure

    ```
    {project_name}/
    ├── backend/          # FastAPI backend with src layout
    │   ├── src/
    │   │   └── app/
    │   │       ├── core/       # Configuration and settings
    │   │       ├── db/         # Database setup
    │   │       ├── models/     # SQLAlchemy models
    │   │       ├── routers/    # API endpoints
    │   │       └── main.py     # FastAPI app
    │   └── pyproject.toml      # Python dependencies
    └── frontend/         # React frontend with Vite
        ├── src/
        └── package.json
    ```

    ## Setup Instructions

    ### Backend Setup

    1. Navigate to backend directory:
       ```bash
       cd backend
       ```

    2. Install dependencies with uv:
       ```bash
       uv sync
       ```

    3. Run the development server:
       ```bash
       uv run dev
       ```

    The backend will be available at `http://localhost:8000`
    - API docs: `http://localhost:8000/docs`
    - Health check: `http://localhost:8000/api/health`

    ### Frontend Setup

    1. Navigate to frontend directory:
       ```bash
       cd frontend
       ```

    2. Install dependencies:
       ```bash
       npm install
       ```

    3. Run the development server:
       ```bash
       npm run dev
       ```

    The frontend will be available at `http://localhost:5173`

    ## Development

    Both servers support hot-reloading. Make changes to the code and see them reflected immediately.

    ### Adding New Endpoints

    1. Create a new router in `backend/src/app/routers/`
    2. Import and include it in `backend/src/app/main.py`

    ### Adding Database Models

    1. Define models in `backend/src/app/models/`
    2. Use the base model from `models/base.py`
    3. Create and run migrations as needed

    ## Tech Stack

    **Backend:**
    - FastAPI - Modern Python web framework
    - SQLAlchemy - ORM for database operations
    - Uvicorn - ASGI server
    - Pydantic - Data validation

    **Frontend:**
    - React - UI library
    - Vite - Build tool and dev server
    - Axios - HTTP client

    ## Next Steps

    - [ ] Set up database migrations (Alembic)
    - [ ] Add authentication (JWT)
    - [ ] Configure environment variables
    - [ ] Add testing (pytest, vitest)
    - [ ] Set up Docker for deployment
    """)


def main(project_name: str = "my-fullstack-app"):
    """Main function to orchestrate project creation."""
    print("=" * 60)
    print("FastAPI + React Project Generator")
    print("=" * 60)

    # Use current working directory as the project root (already set by project_generator)
    root = Path.cwd()

    if (root / 'backend').exists() or (root / 'frontend').exists():
        print(f"\n[WARN] Backend or frontend directory already exists in current location. Overwrite? Skipping creation.")
        return

    print(f"\n[INFO] Creating fullstack project: {project_name}")
    
    # Create backend and frontend
    print("\n[BACKEND] Generating backend structure...")
    create_backend(root, project_name)

    print("\n[FRONTEND] Generating frontend structure...")
    create_frontend(root)

    print("\n[DOCS] Creating README and .gitignore...")
    create_readme(root, project_name)
    create_gitignore(root)

    # Print success message
    print("\n" + "=" * 60)
    print("[SUCCESS] Project created successfully!")
    print("=" * 60)
    print(f"\n[LOCATION] Project location: {root.absolute()}")
    print("\n[GUIDE] Next steps:")
    print(f"\n1. Backend setup:")
    print(f"   cd backend")
    print(f"   uv sync")
    print(f"   uv run dev")
    print(f"\n2. Frontend setup (in a new terminal):")
    print(f"   cd frontend")
    print(f"   npm install")
    print(f"   npm run dev")
    print(f"\n3. Open http://localhost:5173 in your browser")
    print(f"\n[INFO] Check README.md for more details")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create a fullstack FastAPI + React project")
    parser.add_argument("project_name", nargs="?", default="my-fullstack-app", help="Name of the project")
    
    args = parser.parse_args()
    main(args.project_name)
