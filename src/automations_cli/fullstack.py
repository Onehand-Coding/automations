#!/usr/bin/env python3
"""
FastAPI + React Project Generator
Automates the creation of a full-stack project with FastAPI backend and React frontend.
"""

import os
import sys
import stat
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
    """Create the React frontend with Vite, TypeScript, Tailwind CSS, and shadcn/ui."""
    frontend = root / "frontend"
    src = frontend / "src"
    
    # Create directory structure
    (src / "components" / "ui").mkdir(parents=True, exist_ok=True)
    (src / "lib").mkdir(parents=True, exist_ok=True)
    (src / "integrations").mkdir(parents=True, exist_ok=True)
    (frontend / "public").mkdir(parents=True, exist_ok=True)

    # package.json
    create_file(frontend / "package.json", """
    {
      "name": "frontend",
      "private": true,
      "version": "0.1.0",
      "type": "module",
      "scripts": {
        "dev": "vite",
        "build": "tsc -b && vite build",
        "lint": "eslint .",
        "preview": "vite preview"
      },
      "dependencies": {
        "react": "^18.3.1",
        "react-dom": "^18.3.1",
        "axios": "^1.7.0",
        "clsx": "^2.1.1",
        "tailwind-merge": "^2.3.0",
        "class-variance-authority": "^0.7.0",
        "lucide-react": "^0.395.0",
        "@radix-ui/react-slot": "^1.0.2",
        "tailwindcss-animate": "^1.0.7"
      },
      "devDependencies": {
        "@types/node": "^20.14.0",
        "@types/react": "^18.3.3",
        "@types/react-dom": "^18.3.0",
        "@typescript-eslint/eslint-plugin": "^7.13.0",
        "@typescript-eslint/parser": "^7.13.0",
        "@vitejs/plugin-react-swc": "^3.7.0",
        "autoprefixer": "^10.4.19",
        "eslint": "^8.57.0",
        "eslint-plugin-react-hooks": "^4.6.2",
        "eslint-plugin-react-refresh": "^0.4.7",
        "postcss": "^8.4.38",
        "tailwindcss": "^3.4.4",
        "typescript": "^5.4.5",
        "vite": "^5.3.1"
      }
    }
    """)

    # vite.config.ts
    create_file(frontend / "vite.config.ts", """
    import { defineConfig } from "vite";
    import react from "@vitejs/plugin-react-swc";
    import path from "path";

    export default defineConfig({
      plugins: [react()],
      server: {
        port: 5173,
        proxy: {
          "/api": {
            target: "http://localhost:8000",
            changeOrigin: true,
          },
        },
      },
      resolve: {
        alias: {
          "@": path.resolve(__dirname, "./src"),
        },
      },
    });
    """)

    # tsconfig.json
    create_file(frontend / "tsconfig.json", """
    {
      "files": [],
      "references": [
        { "path": "./tsconfig.app.json" },
        { "path": "./tsconfig.node.json" }
      ],
      "compilerOptions": {
        "baseUrl": ".",
        "paths": {
          "@/*": ["./src/*"]
        }
      }
    }
    """)

    # tsconfig.app.json
    create_file(frontend / "tsconfig.app.json", """
    {
      "compilerOptions": {
        "composite": true,
        "target": "ES2020",
        "useDefineForClassFields": true,
        "lib": ["ES2020", "DOM", "DOM.Iterable"],
        "module": "ESNext",
        "skipLibCheck": true,
        "moduleResolution": "bundler",
        "allowImportingTsExtensions": true,
        "resolveJsonModule": true,
        "isolatedModules": true,
        "noEmit": true,
        "jsx": "react-jsx",
        "strict": true,
        "noUnusedLocals": true,
        "noUnusedParameters": true,
        "noFallthroughCasesInSwitch": true,
        "baseUrl": ".",
        "paths": {
          "@/*": ["./src/*"]
        }
      },
      "include": ["src"]
    }
    """)

    # tsconfig.node.json
    create_file(frontend / "tsconfig.node.json", """
    {
      "compilerOptions": {
        "composite": true,
        "target": "ES2022",
        "lib": ["ES2023"],
        "module": "ESNext",
        "skipLibCheck": true,
        "moduleResolution": "bundler",
        "allowImportingTsExtensions": true,
        "resolveJsonModule": true,
        "isolatedModules": true,
        "noEmit": true,
        "strict": true,
        "noUnusedLocals": true,
        "noUnusedParameters": true,
        "noFallthroughCasesInSwitch": true
      },
      "include": ["vite.config.ts"]
    }
    """)

    # vite-env.d.ts
    create_file(frontend / "vite-env.d.ts", """
    /// <reference types="vite/client" />
    """)

    # tailwind.config.ts
    create_file(frontend / "tailwind.config.ts", """
    import type { Config } from "tailwindcss";

    const config: Config = {
      darkMode: ["class"],
      content: [
        "./pages/**/*.{ts,tsx}",
        "./components/**/*.{ts,tsx}",
        "./app/**/*.{ts,tsx}",
        "./src/**/*.{ts,tsx}",
      ],
      prefix: "",
      theme: {
        container: {
          center: true,
          padding: "2rem",
          screens: {
            "2xl": "1400px",
          },
        },
        extend: {
          colors: {
            border: "hsl(var(--border))",
            input: "hsl(var(--input))",
            ring: "hsl(var(--ring))",
            background: "hsl(var(--background))",
            foreground: "hsl(var(--foreground))",
            primary: {
              DEFAULT: "hsl(var(--primary))",
              foreground: "hsl(var(--primary-foreground))",
            },
            secondary: {
              DEFAULT: "hsl(var(--secondary))",
              foreground: "hsl(var(--secondary-foreground))",
            },
            destructive: {
              DEFAULT: "hsl(var(--destructive))",
              foreground: "hsl(var(--destructive-foreground))",
            },
            muted: {
              DEFAULT: "hsl(var(--muted))",
              foreground: "hsl(var(--muted-foreground))",
            },
            accent: {
              DEFAULT: "hsl(var(--accent))",
              foreground: "hsl(var(--accent-foreground))",
            },
            popover: {
              DEFAULT: "hsl(var(--popover))",
              foreground: "hsl(var(--popover-foreground))",
            },
            card: {
              DEFAULT: "hsl(var(--card))",
              foreground: "hsl(var(--card-foreground))",
            },
          },
          borderRadius: {
            lg: "var(--radius)",
            md: "calc(var(--radius) - 2px)",
            sm: "calc(var(--radius) - 4px)",
          },
          keyframes: {
            "accordion-down": {
              from: { height: "0" },
              to: { height: "var(--radix-accordion-content-height)" },
            },
            "accordion-up": {
              from: { height: "var(--radix-accordion-content-height)" },
              to: { height: "0" },
            },
          },
          animation: {
            "accordion-down": "accordion-down 0.2s ease-out",
            "accordion-up": "accordion-up 0.2s ease-out",
          },
        },
      },
      plugins: [require("tailwindcss-animate")],
    };

    export default config;
    """)

    # postcss.config.js
    create_file(frontend / "postcss.config.js", """
    export default {
      plugins: {
        tailwindcss: {},
        autoprefixer: {},
      },
    };
    """)

    # components.json (shadcn/ui)
    create_file(frontend / "components.json", """
    {
      "$schema": "https://ui.shadcn.com/schema.json",
      "style": "default",
      "rsc": false,
      "tsx": true,
      "tailwind": {
        "config": "tailwind.config.ts",
        "css": "src/index.css",
        "baseColor": "slate",
        "cssVariables": true,
        "prefix": ""
      },
      "aliases": {
        "components": "@/components",
        "utils": "@/lib/utils",
        "ui": "@/components/ui",
        "lib": "@/lib",
        "hooks": "@/hooks"
      }
    }
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
        <script type="module" src="/src/main.tsx"></script>
      </body>
    </html>
    """)

    # src/index.css (with Tailwind and shadcn/ui CSS variables)
    create_file(src / "index.css", """
    @tailwind base;
    @tailwind components;
    @tailwind utilities;

    @layer base {
      :root {
        --background: 0 0% 100%;
        --foreground: 222.2 84% 4.9%;
        --card: 0 0% 100%;
        --card-foreground: 222.2 84% 4.9%;
        --popover: 0 0% 100%;
        --popover-foreground: 222.2 84% 4.9%;
        --primary: 222.2 47.4% 11.2%;
        --primary-foreground: 210 40% 98%;
        --secondary: 210 40% 96.1%;
        --secondary-foreground: 222.2 47.4% 11.2%;
        --muted: 210 40% 96.1%;
        --muted-foreground: 215.4 16.3% 46.9%;
        --accent: 210 40% 96.1%;
        --accent-foreground: 222.2 47.4% 11.2%;
        --destructive: 0 84.2% 60.2%;
        --destructive-foreground: 210 40% 98%;
        --border: 214.3 31.8% 91.4%;
        --input: 214.3 31.8% 91.4%;
        --ring: 222.2 84% 4.9%;
        --radius: 0.5rem;
      }

      .dark {
        --background: 222.2 84% 4.9%;
        --foreground: 210 40% 98%;
        --card: 222.2 84% 4.9%;
        --card-foreground: 210 40% 98%;
        --popover: 222.2 84% 4.9%;
        --popover-foreground: 210 40% 98%;
        --primary: 210 40% 98%;
        --primary-foreground: 222.2 47.4% 11.2%;
        --secondary: 217.2 32.6% 17.5%;
        --secondary-foreground: 210 40% 98%;
        --muted: 217.2 32.6% 17.5%;
        --muted-foreground: 215 20.2% 65.1%;
        --accent: 217.2 32.6% 17.5%;
        --accent-foreground: 210 40% 98%;
        --destructive: 0 62.8% 30.6%;
        --destructive-foreground: 210 40% 98%;
        --border: 217.2 32.6% 17.5%;
        --input: 217.2 32.6% 17.5%;
        --ring: 212.7 26.8% 83.9%;
      }
    }

    @layer base {
      * {
        @apply border-border;
      }
      body {
        @apply bg-background text-foreground;
      }
    }
    """)

    # src/main.tsx
    create_file(src / "main.tsx", """
    import { StrictMode } from "react";
    import { createRoot } from "react-dom/client";
    import App from "./App";
    import "./index.css";

    createRoot(document.getElementById("root")!).render(
      <StrictMode>
        <App />
      </StrictMode>
    );
    """)

    # src/lib/utils.ts (shadcn/ui utility)
    create_file(src / "lib" / "utils.ts", """
    import { type ClassValue, clsx } from "clsx";
    import { twMerge } from "tailwind-merge";

    export function cn(...inputs: ClassValue[]) {
      return twMerge(clsx(inputs));
    }
    """)

    # src/integrations/api.ts (Type-safe API client)
    create_file(src / "integrations" / "api.ts", """
    import axios from "axios";

    export const api = axios.create({
      baseURL: "/api",
      headers: {
        "Content-Type": "application/json",
      },
    });

    export interface HealthResponse {
      status: string;
      timestamp: string;
      service: string;
    }

    export const healthApi = {
      check: () => api.get<HealthResponse>("/health"),
    };
    """)

    # src/components/ui/button.tsx (shadcn/ui Button component)
    create_file(src / "components" / "ui" / "button.tsx", """
    import * as React from "react";
    import { Slot } from "@radix-ui/react-slot";
    import { cva, type VariantProps } from "class-variance-authority";
    import { cn } from "@/lib/utils";

    const buttonVariants = cva(
      "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
      {
        variants: {
          variant: {
            default: "bg-primary text-primary-foreground hover:bg-primary/90",
            destructive:
              "bg-destructive text-destructive-foreground hover:bg-destructive/90",
            outline:
              "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
            secondary:
              "bg-secondary text-secondary-foreground hover:bg-secondary/80",
            ghost: "hover:bg-accent hover:text-accent-foreground",
            link: "text-primary underline-offset-4 hover:underline",
          },
          size: {
            default: "h-10 px-4 py-2",
            sm: "h-9 rounded-md px-3",
            lg: "h-11 rounded-md px-8",
            icon: "h-10 w-10",
          },
        },
        defaultVariants: {
          variant: "default",
          size: "default",
        },
      }
    );

    export interface ButtonProps
      extends React.ButtonHTMLAttributes<HTMLButtonElement>,
        VariantProps<typeof buttonVariants> {
      asChild?: boolean;
    }

    const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
      ({ className, variant, size, asChild = false, ...props }, ref) => {
        const Comp = asChild ? Slot : "button";
        return (
          <Comp
            className={cn(buttonVariants({ variant, size, className }))}
            ref={ref}
            {...props}
          />
        );
      }
    );
    Button.displayName = "Button";

    export { Button, buttonVariants };
    """)

    # src/components/ui/card.tsx (shadcn/ui Card component)
    create_file(src / "components" / "ui" / "card.tsx", """
    import * as React from "react";
    import { cn } from "@/lib/utils";

    const Card = React.forwardRef<
      HTMLDivElement,
      React.HTMLAttributes<HTMLDivElement>
    >(({ className, ...props }, ref) => (
      <div
        ref={ref}
        className={cn(
          "rounded-lg border bg-card text-card-foreground shadow-sm",
          className
        )}
        {...props}
      />
    ));
    Card.displayName = "Card";

    const CardHeader = React.forwardRef<
      HTMLDivElement,
      React.HTMLAttributes<HTMLDivElement>
    >(({ className, ...props }, ref) => (
      <div
        ref={ref}
        className={cn("flex flex-col space-y-1.5 p-6", className)}
        {...props}
      />
    ));
    CardHeader.displayName = "CardHeader";

    const CardTitle = React.forwardRef<
      HTMLParagraphElement,
      React.HTMLAttributes<HTMLHeadingElement>
    >(({ className, ...props }, ref) => (
      <h3
        ref={ref}
        className={cn(
          "text-2xl font-semibold leading-none tracking-tight",
          className
        )}
        {...props}
      />
    ));
    CardTitle.displayName = "CardTitle";

    const CardDescription = React.forwardRef<
      HTMLParagraphElement,
      React.HTMLAttributes<HTMLParagraphElement>
    >(({ className, ...props }, ref) => (
      <p
        ref={ref}
        className={cn("text-sm text-muted-foreground", className)}
        {...props}
      />
    ));
    CardDescription.displayName = "CardDescription";

    const CardContent = React.forwardRef<
      HTMLDivElement,
      React.HTMLAttributes<HTMLDivElement>
    >(({ className, ...props }, ref) => (
      <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
    ));
    CardContent.displayName = "CardContent";

    const CardFooter = React.forwardRef<
      HTMLDivElement,
      React.HTMLAttributes<HTMLDivElement>
    >(({ className, ...props }, ref) => (
      <div
        ref={ref}
        className={cn("flex items-center p-6 pt-0", className)}
        {...props}
      />
    ));
    CardFooter.displayName = "CardFooter";

    export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent };
    """)

    # src/App.tsx
    create_file(src / "App.tsx", """
    import { useState, useEffect } from "react";
    import { healthApi, type HealthResponse } from "@/integrations/api";
    import { Button } from "@/components/ui/button";
    import {
      Card,
      CardContent,
      CardDescription,
      CardFooter,
      CardHeader,
      CardTitle,
    } from "@/components/ui/card";

    function App() {
      const [health, setHealth] = useState<HealthResponse | null>(null);
      const [loading, setLoading] = useState(true);
      const [error, setError] = useState<string | null>(null);

      useEffect(() => {
        const checkHealth = async () => {
          try {
            const response = await healthApi.check();
            setHealth(response.data);
            setLoading(false);
          } catch (err) {
            setError(err instanceof Error ? err.message : "An error occurred");
            setLoading(false);
          }
        };

        checkHealth();
      }, []);

      return (
        <div className="min-h-screen bg-background">
          <div className="container mx-auto py-10">
            <Card className="max-w-2xl mx-auto">
              <CardHeader>
                <CardTitle>FastAPI + React</CardTitle>
                <CardDescription>
                  Full-stack application with FastAPI backend and React frontend
                </CardDescription>
              </CardHeader>
              <CardContent>
                <h2 className="text-lg font-semibold mb-4">Backend Health Check</h2>
                {loading && <p className="text-muted-foreground">Loading...</p>}
                {error && (
                  <p className="text-destructive">Error: {error}</p>
                )}
                {health && (
                  <div className="space-y-2">
                    <p>
                      <span className="font-medium">Status:</span>{" "}
                      <span className="text-green-600">{health.status}</span>
                    </p>
                    <p>
                      <span className="font-medium">Service:</span>{" "}
                      {health.service}
                    </p>
                    <p>
                      <span className="font-medium">Timestamp:</span>{" "}
                      {new Date(health.timestamp).toLocaleString()}
                    </p>
                  </div>
                )}
              </CardContent>
              <CardFooter>
                <Button onClick={() => window.location.reload()}>
                  Refresh
                </Button>
              </CardFooter>
            </Card>
          </div>
        </div>
      );
    }

    export default App;
    """)

    # Create public directory (already created above, but keeping for consistency)
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
*.so

# Logs
logs/
*.log

# IDEs and editors
.vscode/
.idea/
*.sublime-*
*.swp
*.swo
*~

# OS generated files
.DS_Store
Thumbs.db
Desktop.ini

# Testing
.coverage
coverage.xml
*.cover
*.py,cover
.pytest_cache/
.tox/

# Node.js
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.pnpm-debug.log*

# TypeScript
*.tsbuildinfo
next-env.d.ts

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
backend/dist/
backend/build/

# Frontend specific
frontend/dist/
frontend/.vite/
frontend/node_modules/
frontend/build/
frontend/coverage/
frontend/tsconfig.tsbuildinfo

# Testing
*.test.js.snap

# Process ID files (from start.sh)
*.pids
"""
    create_file(root / ".gitignore", gitignore_content)


def create_start_script(root: Path, project_name: str):
    """Create start.sh script for running backend + frontend (adapted from exam-ace pattern)."""
    package_name = project_name.replace("-", "_")

    create_file(root / "start.sh", f"""
    #!/bin/bash
    # Root start script - runs both backend and frontend

    echo "🚀 Starting {project_name}..."

    ROOT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
    BACKEND_DIR="$ROOT_DIR/backend"
    FRONTEND_DIR="$ROOT_DIR/frontend"

    # ==================================
    # Cleanup: Kill any existing processes (gracefully)
    # ==================================
    echo "🧹 Cleaning up existing processes..."

    PID_FILE="$ROOT_DIR/.{package_name}.pids"
    BACKEND_PID=""
    FRONTEND_PID=""

    graceful_kill() {{
        local pid=$1
        local name=$2
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo "   Sending SIGTERM to $name (PID: $pid)..."
            kill -15 "$pid" 2>/dev/null
            for i in 1 2 3 4 5; do
                sleep 1
                if ! kill -0 "$pid" 2>/dev/null; then
                    echo "   ✓ $name stopped gracefully"
                    return 0
                fi
            done
            echo "   ⚠ Force-stopping $name..."
            kill -9 "$pid" 2>/dev/null
        fi
        return 0
    }}

    if [ -f "$PID_FILE" ]; then
        source "$PID_FILE"
        [ -n "$BACKEND_PID" ] && graceful_kill "$BACKEND_PID" "backend"
        [ -n "$FRONTEND_PID" ] && graceful_kill "$FRONTEND_PID" "frontend"
        rm -f "$PID_FILE"
    fi

    pkill -15 -f 'uvicorn.*{package_name}' 2>/dev/null
    pkill -15 -f 'vite.*frontend' 2>/dev/null

    sleep 1
    echo "✅ Cleanup complete"
    echo ""

    # ==================================
    # Start Docker services (if compose file exists)
    # ==================================
    if [ -f "$ROOT_DIR/docker-compose.yml" ]; then
        echo "🐳 Starting Docker services..."
        cd "$ROOT_DIR"
        docker compose up -d
        echo "✅ Docker services ready"
        echo ""
    fi

    cleanup() {{
        echo ""
        echo "👋 Shutting down..."
        kill -15 $BACKEND_PID $FRONTEND_PID 2>/dev/null
        wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
        if [ -f "$ROOT_DIR/docker-compose.yml" ]; then
            cd "$ROOT_DIR" && docker compose down
        fi
        exit 0
    }}

    trap cleanup SIGINT SIGTERM

    echo "📦 Starting backend..."
    cd "$BACKEND_DIR"
    uv run dev &
    BACKEND_PID=$!
    echo "✅ Backend running on http://localhost:8000"
    echo ""

    sleep 2

    echo "🎨 Starting frontend..."
    cd "$FRONTEND_DIR"
    npm run dev &
    FRONTEND_PID=$!
    echo "✅ Frontend running on http://localhost:5173"
    echo ""

    cat > "$PID_FILE" << EOF
    BACKEND_PID=$BACKEND_PID
    FRONTEND_PID=$FRONTEND_PID
    EOF

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Backend:  http://localhost:8000"
    echo "  Frontend: http://localhost:5173"
    echo "  API Docs: http://localhost:8000/docs"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Press Ctrl+C to stop all servers"
    echo ""

    wait $BACKEND_PID $FRONTEND_PID
    """)

    # Make start.sh executable
    start_script = root / "start.sh"
    start_script.chmod(start_script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"[OK] Made executable: {start_script}")


def create_docker_compose(root: Path, project_name: str):
    """Create docker-compose.yml for PostgreSQL."""
    db_name = project_name.replace("-", "_")

    create_file(root / "docker-compose.yml", f"""
    services:
      db:
        image: postgres:16-alpine
        container_name: {project_name}-db
        restart: unless-stopped
        environment:
          POSTGRES_DB: {db_name}
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        ports:
          - "5432:5432"
        volumes:
          - postgres_data:/var/lib/postgresql/data
        healthcheck:
          test: ["CMD-SHELL", "pg_isready -U postgres"]
          interval: 5s
          timeout: 5s
          retries: 5

    volumes:
      postgres_data:
        name: {project_name}-postgres-data
    """)


def create_frontend_readme(root: Path):
    """Create frontend README with setup instructions."""
    create_file(root / "frontend" / "README.md", """
# Frontend

React + TypeScript + Vite + Tailwind CSS + shadcn/ui

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - Re-usable components built with Radix UI and Tailwind CSS
- **Axios** - HTTP client

## Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linter
npm run lint
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── ui/          # shadcn/ui components
│   ├── integrations/    # API clients
│   ├── lib/             # Utilities
│   ├── App.tsx          # Main app component
│   ├── main.tsx         # Entry point
│   └── index.css        # Global styles
├── index.html
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── vite.config.ts
```

## Adding Components

### Using shadcn/ui

This project uses shadcn/ui for components. To add new components:

```bash
# Using npx
npx shadcn-ui@latest add button

# Using pnpm
pnpm dlx shadcn-ui@latest add button
```

Available components: https://ui.shadcn.com

### Manual Components

Create components in `src/components/` and export them:

```tsx
// src/components/MyComponent.tsx
import { cn } from "@/lib/utils";

export function MyComponent({ className, ...props }) {
  return (
    <div className={cn("...", className)} {...props} />
  );
}
```

## API Integration

API calls are configured in `src/integrations/api.ts`:

```tsx
import { api } from "@/integrations/api";

// Use the typed API client
const response = await api.get("/endpoint");
```

## Styling

Use Tailwind CSS utility classes with the `cn` helper for conditional classes:

```tsx
import { cn } from "@/lib/utils";

<div className={cn("base-class", isActive && "active-class")} />
```

## Path Aliases

Use `@/` alias for `src/`:

```tsx
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
```

## Configuration

- **Vite**: `vite.config.ts` - Build and dev server config
- **TypeScript**: `tsconfig.json` - TypeScript config
- **Tailwind**: `tailwind.config.ts` - Theme and plugins
- **shadcn/ui**: `components.json` - Component config
""")


def create_readme(root: Path, project_name: str):
    """Create README with setup instructions."""
    # Convert project name to display format (replace hyphens with spaces, title case)
    display_name = project_name.replace("-", " ").title()
    
    create_file(root / "README.md", f"""
# {display_name}

Full-stack application with FastAPI backend and React frontend.

## Documentation

- **[Frontend Guide](frontend/README.md)** - React + TypeScript + Tailwind CSS + shadcn/ui documentation
- **[Backend Guide](backend/README.md)** - FastAPI + SQLAlchemy documentation

## Quick Start

### 1. Start Backend

```bash
cd backend
uv sync
uv run dev
```

Backend runs at `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

### 2. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`

## Project Structure

```
{project_name}/
├── backend/           # FastAPI backend with src layout
│   ├── src/
│   │   └── app/
│   │       ├── core/       # Configuration and settings
│   │       ├── db/         # Database setup
│   │       ├── models/     # SQLAlchemy models
│   │       ├── routers/    # API endpoints
│   │       └── main.py     # FastAPI app
│   └── pyproject.toml      # Python dependencies
└── frontend/          # React frontend with Vite, TypeScript, Tailwind
    ├── src/
    │   ├── components/    # React components
    │   ├── integrations/  # API clients
    │   └── lib/           # Utilities
    └── package.json
```

## Features

- ✅ FastAPI backend with async support
- ✅ React 18 with TypeScript
- ✅ Tailwind CSS for styling
- ✅ shadcn/ui components
- ✅ Type-safe API integration
- ✅ Hot module replacement (HMR)
- ✅ CORS configured for local development

## API Endpoints

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check endpoint |
| GET | `/` | Root endpoint with welcome message |

## Development

Both servers support hot-reloading. Make changes to the code and see them reflected immediately.

### Adding New Endpoints

1. Create a new router in `backend/src/app/routers/`
2. Import and include it in `backend/src/app/main.py`
3. Add TypeScript types in `frontend/src/integrations/api.ts`

### Adding Database Models

1. Define models in `backend/src/app/models/`
2. Create schemas in `backend/src/app/schemas/`
3. Use the base model from `models/base.py`

## Tech Stack

**Backend:**
- FastAPI - Modern Python web framework
- SQLAlchemy - ORM for database operations
- Uvicorn - ASGI server
- Pydantic - Data validation

**Frontend:**
- React 18 - UI library
- TypeScript - Type safety
- Vite - Build tool and dev server
- Tailwind CSS - Utility-first CSS framework
- shadcn/ui - Re-usable components
- Axios - HTTP client

## Next Steps

- [ ] Set up database migrations (Alembic)
- [ ] Add authentication (JWT)
- [ ] Configure environment variables for production
- [ ] Add testing (pytest, vitest/jest)
- [ ] Set up CI/CD pipeline
- [ ] Configure Docker for deployment
""")


def main(project_name: str = "my-fullstack-app", compose: bool = False):
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
    create_frontend_readme(root)

    if compose:
        print("\n[COMPOSE] Creating docker-compose.yml...")
        create_docker_compose(root, project_name)
        # Update .env with PostgreSQL URL instead of SQLite
        db_name = project_name.replace("-", "_")
        env_path = root / "backend" / ".env"
        env_path.write_text(f"""DATABASE_URL=postgresql://postgres:postgres@localhost:5432/{db_name}
SECRET_KEY=your-secret-key-change-in-production
DEBUG=True
""")

    print("\n[SCRIPT] Creating start.sh...")
    create_start_script(root, project_name)

    # Print success message
    print("\n" + "=" * 60)
    print("[SUCCESS] Project created successfully!")
    print("=" * 60)
    print(f"\n[LOCATION] Project location: {root.absolute()}")
    print("\n[GUIDE] Next steps:")
    print(f"\n  ./start.sh")
    if compose:
        print(f"     Starts PostgreSQL (Docker) + backend + frontend")
    else:
        print(f"     Starts backend + frontend")
    print(f"\n  Or manually:")
    print(f"\n  1. Backend setup:")
    print(f"     cd backend")
    print(f"     uv sync")
    print(f"     uv run dev")
    print(f"\n  2. Frontend setup (in a new terminal):")
    print(f"     cd frontend")
    print(f"     npm install")
    print(f"     npm run dev")
    print(f"\n  3. Open http://localhost:5173 in your browser")
    print(f"\n[INFO] Check README.md for more details")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    try:
        import argparse
        parser = argparse.ArgumentParser(description="Create a fullstack FastAPI + React project")
        parser.add_argument("project_name", nargs="?", default="my-fullstack-app", help="Name of the project")
        parser.add_argument("--compose", action="store_true", help="Generate docker-compose.yml for PostgreSQL")
        
        args = parser.parse_args()
        main(args.project_name, compose=args.compose)
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)
