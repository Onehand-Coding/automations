#!/usr/bin/env python3
"""
FastAPI + Flutter Project Generator
Automates fullstack project creation with a FastAPI backend and Flutter frontend.
Based on patterns from docdesk (Flutter) and fullstack.py (generator architecture).
"""

import os
import stat
from pathlib import Path
import textwrap


def create_file(filepath: Path, content: str):
    """Create a file with the given content, creating parent directories if needed."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(textwrap.dedent(content).strip() + "\n", encoding='utf-8')
    print(f"[OK] Created: {filepath}")


def create_backend(root: Path, project_name: str):
    """Create the FastAPI backend (async, JWT auth, based on docdesk pattern)."""
    backend = root / "backend"
    package_name = project_name.replace("-", "_")
    src_app = backend / "src" / package_name

    # pyproject.toml
    create_file(backend / "pyproject.toml", f"""
    [build-system]
    requires = ["hatchling"]
    build-backend = "hatchling.build"

    [project]
    name = "{package_name}-backend"
    version = "0.1.0"
    description = "FastAPI backend"
    requires-python = ">=3.10"
    dependencies = [
        "fastapi>=0.110.0",
        "uvicorn[standard]>=0.27.0",
        "sqlalchemy[asyncio]>=2.0.0",
        "asyncpg>=0.29.0",
        "alembic>=1.13.0",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "bcrypt<5.0.0",
        "pydantic[email]>=2.5.0",
        "pydantic-settings>=2.1.0",
        "python-multipart>=0.0.6",
        "python-dotenv>=1.0.0",
    ]

    [project.scripts]
    dev = "{package_name}.scripts:dev"
    start = "{package_name}.scripts:start"
    db-migrate = "{package_name}.scripts:run_migrations"
    db-upgrade = "{package_name}.scripts:upgrade_db"

    [tool.hatch.build.targets.wheel]
    packages = ["src/{package_name}"]
    """)

    # .env
    create_file(backend / ".env", f"""
    DATABASE_URL=sqlite+aiosqlite:///./{project_name}.db
    SECRET_KEY=change-me-to-a-random-secret-key
    ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=480
    DEBUG=True
    """)

    # src/{package_name}/__init__.py
    create_file(src_app / "__init__.py", """
    __version__ = "0.1.0"
    """)

    # src/{package_name}/main.py
    create_file(src_app / "main.py", f"""
    from contextlib import asynccontextmanager
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from {package_name}.config import settings
    from {package_name}.database import engine, Base, async_session
    from {package_name}.routers import auth, health
    from {package_name}.services.auth_service import get_user_by_email, create_user

    DEMO_EMAIL = "demo@example.com"
    DEMO_PASSWORD = "demo1234"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with async_session() as session:
            user = await get_user_by_email(session, DEMO_EMAIL)
            if user is None:
                await create_user(session, DEMO_EMAIL, DEMO_PASSWORD, "Demo User")
                await session.commit()
                print(f"  Demo user created: {{DEMO_EMAIL}} / {{DEMO_PASSWORD}}")
            else:
                print(f"  Demo user: {{DEMO_EMAIL}} / {{DEMO_PASSWORD}}")
        yield
        await engine.dispose()

    app = FastAPI(
        title="{project_name} API",
        description="FastAPI backend for {project_name}",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

    @app.get("/")
    async def root():
        return {{"message": "{project_name} API", "version": "0.1.0"}}
    """)

    # src/{package_name}/config.py
    create_file(src_app / "config.py", f"""
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        database_url: str = "sqlite+aiosqlite:///./{project_name}.db"
        secret_key: str = "change-me-to-a-random-secret-key"
        algorithm: str = "HS256"
        access_token_expire_minutes: int = 480
        debug: bool = True

        model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    settings = Settings()
    """)

    # src/{package_name}/database.py
    create_file(src_app / "database.py", f"""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy.orm import DeclarativeBase

    from {package_name}.config import settings

    engine = create_async_engine(settings.database_url, echo=settings.debug)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    class Base(DeclarativeBase):
        pass

    async def get_db():
        async with async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    """)

    # src/{package_name}/deps.py
    create_file(src_app / "deps.py", f"""
    from fastapi import Depends, HTTPException, status
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from sqlalchemy.ext.asyncio import AsyncSession
    from jose import JWTError, jwt

    from {package_name}.config import settings
    from {package_name}.database import get_db
    from {package_name}.models.user import User
    from {package_name}.services.auth_service import get_user_by_id

    bearer = HTTPBearer()

    async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(bearer),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        token = credentials.credentials
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            user_id: int = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        user = await get_user_by_id(db, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return user
    """)

    # src/{package_name}/scripts.py
    create_file(src_app / "scripts.py", f"""
    import subprocess
    import sys
    import os
    from pathlib import Path

    def dev():
        backend_dir = Path(__file__).parent.parent.parent
        env = dict(os.environ)
        env['PYTHONPATH'] = f"{{backend_dir}}/src:{{env.get('PYTHONPATH', '')}}"
        cmd = [sys.executable, "-m", "uvicorn",
               "{package_name}.main:app", "--reload",
               "--host", "0.0.0.0", "--port", "8000"]
        subprocess.run(cmd, cwd=str(backend_dir), env=env)

    def start():
        backend_dir = Path(__file__).parent.parent.parent
        env = dict(os.environ)
        env['PYTHONPATH'] = f"{{backend_dir}}/src:{{env.get('PYTHONPATH', '')}}"
        cmd = [sys.executable, "-m", "uvicorn",
               "{package_name}.main:app",
               "--host", "0.0.0.0", "--port", "8000"]
        subprocess.run(cmd, cwd=str(backend_dir), env=env)

    def run_migrations():
        backend_dir = Path(__file__).parent.parent.parent
        env = dict(os.environ)
        env['PYTHONPATH'] = f"{{backend_dir}}/src:{{env.get('PYTHONPATH', '')}}"
        subprocess.run([sys.executable, "-m", "alembic", "revision", "--autogenerate", "-m", "Migration"],
                       cwd=str(backend_dir), env=env)

    def upgrade_db():
        backend_dir = Path(__file__).parent.parent.parent
        env = dict(os.environ)
        env['PYTHONPATH'] = f"{{backend_dir}}/src:{{env.get('PYTHONPATH', '')}}"
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                       cwd=str(backend_dir), env=env)

    if __name__ == "__main__":
        dev()
    """)

    # src/{package_name}/models/__init__.py
    create_file(src_app / "models" / "__init__.py", "")

    # src/{package_name}/models/user.py
    create_file(src_app / "models" / "user.py", f"""
    from sqlalchemy import Column, Integer, String, Boolean, DateTime
    from sqlalchemy.sql import func
    from {package_name}.database import Base

    class User(Base):
        __tablename__ = "users"

        id = Column(Integer, primary_key=True, index=True)
        email = Column(String, unique=True, index=True, nullable=False)
        hashed_password = Column(String, nullable=False)
        full_name = Column(String, nullable=False)
        is_active = Column(Boolean, default=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now())
        updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    """)

    # src/{package_name}/schemas/__init__.py
    create_file(src_app / "schemas" / "__init__.py", "")

    # src/{package_name}/schemas/auth.py
    create_file(src_app / "schemas" / "auth.py", f"""
    from pydantic import BaseModel, EmailStr

    class RegisterRequest(BaseModel):
        email: EmailStr
        password: str
        full_name: str

    class LoginRequest(BaseModel):
        email: EmailStr
        password: str

    class TokenResponse(BaseModel):
        access_token: str
        token_type: str = "bearer"

    class UserResponse(BaseModel):
        id: int
        email: str
        full_name: str
        is_active: bool

        model_config = {{"from_attributes": True}}
    """)

    # src/{package_name}/schemas/health.py
    create_file(src_app / "schemas" / "health.py", f"""
    from pydantic import BaseModel
    from datetime import datetime

    class HealthResponse(BaseModel):
        status: str
        timestamp: datetime
        service: str
    """)

    # src/{package_name}/services/__init__.py
    create_file(src_app / "services" / "__init__.py", "")

    # src/{package_name}/services/auth_service.py
    create_file(src_app / "services" / "auth_service.py", f"""
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    from passlib.context import CryptContext
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from {package_name}.config import settings
    from {package_name}.models.user import User

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    def create_access_token(user_id: int) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
        return jwt.encode({{"sub": user_id, "exp": expire}}, settings.secret_key, algorithm=settings.algorithm)

    async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create_user(db: AsyncSession, email: str, password: str, full_name: str) -> User:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
        )
        db.add(user)
        await db.flush()
        return user
    """)

    # src/{package_name}/routers/__init__.py
    create_file(src_app / "routers" / "__init__.py", "")

    # src/{package_name}/routers/health.py
    create_file(src_app / "routers" / "health.py", f"""
    from fastapi import APIRouter
    from datetime import datetime, timezone
    from {package_name}.schemas.health import HealthResponse

    router = APIRouter()

    @router.get("/health", response_model=HealthResponse)
    async def health_check():
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(timezone.utc),
            service="{project_name} API",
        )
    """)

    # src/{package_name}/routers/auth.py
    create_file(src_app / "routers" / "auth.py", f"""
    from fastapi import APIRouter, Depends, HTTPException, status
    from sqlalchemy.ext.asyncio import AsyncSession

    from {package_name}.database import get_db
    from {package_name}.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
    from {package_name}.services.auth_service import (
        create_user, get_user_by_email, verify_password, create_access_token,
    )

    router = APIRouter()

    @router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
    async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
        existing = await get_user_by_email(db, body.email)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        user = await create_user(db, email=body.email, password=body.password, full_name=body.full_name)
        token = create_access_token(user.id)
        return TokenResponse(access_token=token)

    @router.post("/login", response_model=TokenResponse)
    async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
        user = await get_user_by_email(db, body.email)
        if not user or not verify_password(body.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        token = create_access_token(user.id)
        return TokenResponse(access_token=token)
    """)


def create_frontend(root: Path, project_name: str):
    """Create the Flutter frontend (based on docdesk pattern: feature-first, Riverpod, GoRouter)."""
    frontend = root / "frontend"
    lib = frontend / "lib"

    # -- pubspec.yaml --
    create_file(frontend / "pubspec.yaml", f"""
    name: {project_name.replace('-', '_')}_frontend
    description: "Flutter frontend for {project_name}"
    publish_to: "none"
    version: "0.1.0"

    environment:
      sdk: ^3.12.0

    dependencies:
      flutter:
        sdk: flutter
      go_router: ^14.0.0
      flutter_riverpod: ^2.5.0
      dio: ^5.4.0
      flutter_secure_storage: ^9.2.0
      google_fonts: ^6.2.0
      intl: ^0.19.0
      cupertino_icons: ^1.0.8

    dev_dependencies:
      flutter_test:
        sdk: flutter
      flutter_lints: ^5.0.0

    flutter:
      uses-material-design: true
    """)

    # -- analysis_options.yaml --
    create_file(frontend / "analysis_options.yaml", """
    include: package:flutter_lints/flutter.yaml

    linter:
      rules:
        prefer_const_constructors: true
        prefer_const_declarations: true
        avoid_print: false
    """)

    # -- lib/main.dart --
    create_file(lib / "main.dart", """
    import 'package:flutter/material.dart';
    import 'package:flutter_riverpod/flutter_riverpod.dart';
    import 'app.dart';

    void main() {
      WidgetsFlutterBinding.ensureInitialized();
      runApp(const ProviderScope(child: App()));
    }
    """)

    # -- lib/app.dart --
    create_file(lib / "app.dart", f"""
    import 'package:flutter/material.dart';
    import 'package:flutter_riverpod/flutter_riverpod.dart';
    import 'core/router/app_router.dart';
    import 'core/theme/app_theme.dart';

    class App extends ConsumerWidget {{
      const App({{super.key}});

      @override
      Widget build(BuildContext context, WidgetRef ref) {{
        final router = ref.watch(appRouterProvider);
        return MaterialApp.router(
          title: '{project_name}',
          theme: AppTheme.light,
          darkTheme: AppTheme.dark,
          routerConfig: router,
          debugShowCheckedModeBanner: false,
        );
      }}
    }}
    """)

    # -- lib/core/theme/app_colors.dart --
    create_file(lib / "core" / "theme" / "app_colors.dart", """
    import 'package:flutter/material.dart';

    class AppColors {
      AppColors._();

      static const primary = Color(0xFF2563EB);
      static const primaryLight = Color(0xFF60A5FA);
      static const secondary = Color(0xFF059669);
      static const surface = Color(0xFFF8FAFC);
      static const error = Color(0xFFDC2626);
      static const textPrimary = Color(0xFF1E293B);
      static const textSecondary = Color(0xFF64748B);
      static const border = Color(0xFFE2E8F0);

      static const darkPrimary = Color(0xFF3B82F6);
      static const darkSurface = Color(0xFF1E293B);
      static const darkBackground = Color(0xFF0F172A);
      static const darkTextPrimary = Color(0xFFF1F5F9);
      static const darkTextSecondary = Color(0xFF94A3B8);
    }
    """)

    # -- lib/core/theme/app_text_styles.dart --
    create_file(lib / "core" / "theme" / "app_text_styles.dart", """
    import 'package:flutter/material.dart';
    import 'app_colors.dart';

    class AppTextStyles {
      AppTextStyles._();

      static const headline = TextStyle(
        fontSize: 24,
        fontWeight: FontWeight.bold,
        color: AppColors.textPrimary,
      );
      static const title = TextStyle(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        color: AppColors.textPrimary,
      );
      static const body = TextStyle(
        fontSize: 14,
        color: AppColors.textPrimary,
      );
      static const caption = TextStyle(
        fontSize: 12,
        color: AppColors.textSecondary,
      );
    }
    """)

    # -- lib/core/theme/app_theme.dart --
    create_file(lib / "core" / "theme" / "app_theme.dart", """
    import 'package:flutter/material.dart';
    import 'package:google_fonts/google_fonts.dart';
    import 'app_colors.dart';

    class AppTheme {
      AppTheme._();

      static ThemeData get light => ThemeData(
        useMaterial3: true,
        brightness: Brightness.light,
        colorSchemeSeed: AppColors.primary,
        scaffoldBackgroundColor: AppColors.surface,
        textTheme: GoogleFonts.interTextTheme(),
        appBarTheme: const AppBarTheme(centerTitle: false, elevation: 0),
        inputDecorationTheme: InputDecorationTheme(
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        ),
      );

      static ThemeData get dark => ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        colorSchemeSeed: AppColors.darkPrimary,
        scaffoldBackgroundColor: AppColors.darkBackground,
        textTheme: GoogleFonts.interTextTheme(ThemeData.dark().textTheme),
        appBarTheme: const AppBarTheme(centerTitle: false, elevation: 0),
        inputDecorationTheme: InputDecorationTheme(
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        ),
      );
    }
    """)

    # -- lib/core/network/api_client.dart --
    create_file(lib / "core" / "network" / "api_client.dart", """
    import 'package:dio/dio.dart';
    import 'package:flutter_secure_storage/flutter_secure_storage.dart';

    class ApiClient {
      static const _baseUrl = 'http://localhost:8000/api';
      static final _storage = FlutterSecureStorage();
      static final Dio _dio = Dio(BaseOptions(
        baseUrl: _baseUrl,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
        headers: {'Content-Type': 'application/json'},
      ));

      static Future<void> init() async {
        final token = await _storage.read(key: 'access_token');
        if (token != null) {
          _dio.options.headers['Authorization'] = 'Bearer $token';
        }
      }

      static Future<void> setToken(String token) async {
        await _storage.write(key: 'access_token', value: token);
        _dio.options.headers['Authorization'] = 'Bearer $token';
      }

      static Future<void> clearToken() async {
        await _storage.delete(key: 'access_token');
        _dio.options.headers.remove('Authorization');
      }

      static Future<bool> hasToken() async {
        final token = await _storage.read(key: 'access_token');
        return token != null && token.isNotEmpty;
      }

      static Future<Response<T>> get<T>(
        String path, {
        Map<String, dynamic>? queryParameters,
      }) => _dio.get<T>(path, queryParameters: queryParameters);

      static Future<Response<T>> post<T>(
        String path, {
        dynamic data,
      }) => _dio.post<T>(path, data: data);

      static Future<Response<T>> put<T>(
        String path, {
        dynamic data,
      }) => _dio.put<T>(path, data: data);

      static Future<Response<T>> delete<T>(String path) => _dio.delete<T>(path);
    }
    """)

    # -- lib/core/network/api_exception.dart --
    create_file(lib / "core" / "network" / "api_exception.dart", """
    class ApiException implements Exception {
      final String message;
      final int? statusCode;

      ApiException(this.message, {this.statusCode});

      @override
      String toString() => message;
    }
    """)

    # -- lib/core/router/app_router.dart --
    create_file(lib / "core" / "router" / "app_router.dart", """
    import 'package:flutter_riverpod/flutter_riverpod.dart';
    import 'package:go_router/go_router.dart';
    import '../../core/network/api_client.dart';
    import '../../features/auth/screens/login_screen.dart';
    import '../../features/dashboard/screens/dashboard_screen.dart';
    import '../../shared/widgets/app_shell.dart';

    final appRouterProvider = Provider<GoRouter>((ref) {
      return GoRouter(
        initialLocation: '/login',
        redirect: (context, state) async {
          final loggedIn = await ApiClient.hasToken();
          final loggingIn = state.matchedLocation == '/login';
          if (!loggedIn && !loggingIn) return '/login';
          if (loggedIn && loggingIn) return '/';
          return null;
        },
        routes: [
          GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
          ShellRoute(
            builder: (_, __, child) => AppShell(child: child),
            routes: [
              GoRoute(
                path: '/',
                builder: (_, __) => const DashboardScreen(),
              ),
            ],
          ),
        ],
      );
    });
    """)

    # -- lib/features/auth/providers/auth_provider.dart --
    create_file(lib / "features" / "auth" / "providers" / "auth_provider.dart", """
    import 'package:flutter_riverpod/flutter_riverpod.dart';
    import '../repositories/auth_repository.dart';
    import '../models/auth_state.dart';

    final authRepositoryProvider = Provider<AuthRepository>((ref) => AuthRepository());

    final authStateProvider = StateNotifierProvider<AuthStateNotifier, AuthState>((ref) {
      return AuthStateNotifier(ref.read(authRepositoryProvider));
    });

    class AuthStateNotifier extends StateNotifier<AuthState> {
      final AuthRepository _repository;

      AuthStateNotifier(this._repository) : super(const AuthState.initial());

      Future<void> login(String email, String password) async {
        state = const AuthState.loading();
        try {
          await _repository.login(email, password);
          state = const AuthState.authenticated();
        } catch (e) {
          state = AuthState.error(e.toString());
        }
      }

      Future<void> register(String email, String password, String fullName) async {
        state = const AuthState.loading();
        try {
          await _repository.register(email, password, fullName);
          state = const AuthState.authenticated();
        } catch (e) {
          state = AuthState.error(e.toString());
        }
      }

      Future<void> logout() async {
        await _repository.logout();
        state = const AuthState.initial();
      }
    }
    """)

    # -- lib/features/auth/models/auth_state.dart --
    create_file(lib / "features" / "auth" / "models" / "auth_state.dart", """
    sealed class AuthState {
      const AuthState();
      const factory AuthState.initial() = AuthInitial;
      const factory AuthState.loading() = AuthLoading;
      const factory AuthState.authenticated() = AuthAuthenticated;
      const factory AuthState.error(String message) = AuthError;
    }

    class AuthInitial extends AuthState {
      const AuthInitial();
    }

    class AuthLoading extends AuthState {
      const AuthLoading();
    }

    class AuthAuthenticated extends AuthState {
      const AuthAuthenticated();
    }

    class AuthError extends AuthState {
      final String message;
      const AuthError(this.message);
    }
    """)

    # -- lib/features/auth/repositories/auth_repository.dart --
    create_file(lib / "features" / "auth" / "repositories" / "auth_repository.dart", """
    import 'package:dio/dio.dart';
    import '../../../core/network/api_client.dart';
    import '../../../core/network/api_exception.dart';

    class AuthRepository {
      Future<void> login(String email, String password) async {
        try {
          final response = await ApiClient.post('/auth/login', data: {
            'email': email,
            'password': password,
          });
          final token = response.data['access_token'] as String;
          await ApiClient.setToken(token);
        } on DioException catch (e) {
          throw ApiException(
            e.response?.data['detail'] ?? 'Login failed',
            statusCode: e.response?.statusCode,
          );
        }
      }

      Future<void> register(String email, String password, String fullName) async {
        try {
          final response = await ApiClient.post('/auth/register', data: {
            'email': email,
            'password': password,
            'full_name': fullName,
          });
          final token = response.data['access_token'] as String;
          await ApiClient.setToken(token);
        } on DioException catch (e) {
          throw ApiException(
            e.response?.data['detail'] ?? 'Registration failed',
            statusCode: e.response?.statusCode,
          );
        }
      }

      Future<void> logout() async {
        await ApiClient.clearToken();
      }
    }
    """)

    # -- lib/features/auth/screens/login_screen.dart --
    create_file(lib / "features" / "auth" / "screens" / "login_screen.dart", """
    import 'package:flutter/material.dart';
    import 'package:flutter_riverpod/flutter_riverpod.dart';
    import 'package:go_router/go_router.dart';
    import '../providers/auth_provider.dart';
    import '../models/auth_state.dart';

    class LoginScreen extends ConsumerStatefulWidget {
      const LoginScreen({super.key});

      @override
      ConsumerState<LoginScreen> createState() => _LoginScreenState();
    }

    class _LoginScreenState extends ConsumerState<LoginScreen> {
      final _formKey = GlobalKey<FormState>();
      final _emailController = TextEditingController();
      final _passwordController = TextEditingController();
      bool _isRegister = false;

      @override
      void dispose() {
        _emailController.dispose();
        _passwordController.dispose();
        super.dispose();
      }

      Future<void> _submit() async {
        if (!_formKey.currentState!.validate()) return;
        final auth = ref.read(authStateProvider.notifier);
        if (_isRegister) {
          await auth.register(_emailController.text, _passwordController.text, 'User');
        } else {
          await auth.login(_emailController.text, _passwordController.text);
        }
      }

      @override
      Widget build(BuildContext context) {
        final authState = ref.watch(authStateProvider);

        ref.listen(authStateProvider, (_, next) {
          if (next is AuthAuthenticated) {
            context.go('/');
          }
        });

        return Scaffold(
          body: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Form(
                key: _formKey,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(_isRegister ? 'Create Account' : 'Welcome', style: Theme.of(context).textTheme.headlineLarge),
                    const SizedBox(height: 8),
                    Text(_isRegister ? 'Register a new account' : 'Sign in to continue', style: Theme.of(context).textTheme.bodyMedium),
                    const SizedBox(height: 32),
                    TextFormField(
                      controller: _emailController,
                      decoration: const InputDecoration(labelText: 'Email'),
                      keyboardType: TextInputType.emailAddress,
                      validator: (v) => v == null || v.isEmpty ? 'Email required' : null,
                    ),
                    const SizedBox(height: 16),
                    TextFormField(
                      controller: _passwordController,
                      decoration: const InputDecoration(labelText: 'Password'),
                      obscureText: true,
                      validator: (v) => v == null || v.isEmpty ? 'Password required' : null,
                    ),
                    const SizedBox(height: 24),
                    FilledButton(
                      onPressed: authState is AuthLoading ? null : _submit,
                      child: authState is AuthLoading
                          ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                          : Text(_isRegister ? 'Register' : 'Sign In'),
                    ),
                    const SizedBox(height: 16),
                    TextButton(
                      onPressed: () => setState(() => _isRegister = !_isRegister),
                      child: Text(_isRegister ? 'Already have an account? Sign in' : 'No account? Register'),
                    ),
                    if (authState is AuthError)
                      Padding(
                        padding: const EdgeInsets.only(top: 16),
                        child: Text(authState.message, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                      ),
                  ],
                ),
              ),
            ),
          ),
        );
      }
    }
    """)

    # -- lib/features/dashboard/providers/dashboard_provider.dart --
    create_file(lib / "features" / "dashboard" / "providers" / "dashboard_provider.dart", """
    import 'package:flutter_riverpod/flutter_riverpod.dart';
    import '../repositories/dashboard_repository.dart';
    import '../models/dashboard_state.dart';

    final dashboardRepositoryProvider = Provider<DashboardRepository>((ref) => DashboardRepository());

    final dashboardProvider = StateNotifierProvider<DashboardNotifier, DashboardState>((ref) {
      return DashboardNotifier(ref.read(dashboardRepositoryProvider));
    });

    class DashboardNotifier extends StateNotifier<DashboardState> {
      final DashboardRepository _repository;

      DashboardNotifier(this._repository) : super(const DashboardState.initial());

      Future<void> checkHealth() async {
        state = const DashboardState.loading();
        try {
          final health = await _repository.getHealth();
          state = DashboardState.data(health);
        } catch (e) {
          state = DashboardState.error(e.toString());
        }
      }
    }
    """)

    # -- lib/features/dashboard/models/dashboard_state.dart --
    create_file(lib / "features" / "dashboard" / "models" / "dashboard_state.dart", """
    sealed class DashboardState {
      const DashboardState();
      const factory DashboardState.initial() = DashboardInitial;
      const factory DashboardState.loading() = DashboardLoading;
      const factory DashboardState.data(String message) = DashboardData;
      const factory DashboardState.error(String message) = DashboardError;
    }

    class DashboardInitial extends DashboardState {
      const DashboardInitial();
    }

    class DashboardLoading extends DashboardState {
      const DashboardLoading();
    }

    class DashboardData extends DashboardState {
      final String message;
      const DashboardData(this.message);
    }

    class DashboardError extends DashboardState {
      final String message;
      const DashboardError(this.message);
    }
    """)

    # -- lib/features/dashboard/repositories/dashboard_repository.dart --
    create_file(lib / "features" / "dashboard" / "repositories" / "dashboard_repository.dart", """
    import 'package:dio/dio.dart';
    import '../../../core/network/api_client.dart';
    import '../../../core/network/api_exception.dart';

    class DashboardRepository {
      Future<String> getHealth() async {
        try {
          final response = await ApiClient.get('/health');
          return 'Status: ${response.data['status']} — ${response.data['service']}';
        } on DioException catch (e) {
          throw ApiException(e.response?.data['detail'] ?? 'Health check failed');
        }
      }
    }
    """)

def create_frontend_extra(root: Path, project_name: str = ""):
    """Create remaining Flutter files that need to be outside the main create_frontend."""
    lib = root / "frontend" / "lib"

    # -- lib/features/dashboard/screens/dashboard_screen.dart (full class wrapper) --
    # Re-write the file fully with the correct class structure
    dashboard_screen = lib / "features" / "dashboard" / "screens" / "dashboard_screen.dart"
    dashboard_screen.parent.mkdir(parents=True, exist_ok=True)
    dashboard_screen.write_text(textwrap.dedent(f"""
    import 'package:flutter/material.dart';
    import 'package:flutter_riverpod/flutter_riverpod.dart';
    import '../providers/dashboard_provider.dart';
    import '../models/dashboard_state.dart';

    class DashboardScreen extends ConsumerStatefulWidget {{
      const DashboardScreen({{super.key}});

      @override
      ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
    }}

    class _DashboardScreenState extends ConsumerState<DashboardScreen> {{
      @override
      void initState() {{
        super.initState();
        Future.microtask(() => ref.read(dashboardProvider.notifier).checkHealth());
      }}

      @override
      Widget build(BuildContext context) {{
        final state = ref.watch(dashboardProvider);

        return Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: switch (state) {{
              DashboardInitial() || DashboardLoading() => const CircularProgressIndicator(),
              DashboardData(:final message) => Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.check_circle, size: 64, color: Theme.of(context).colorScheme.primary),
                  const SizedBox(height: 16),
                  Text('Backend Connected', style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: 8),
                  Text(message, textAlign: TextAlign.center),
                ],
              ),
              DashboardError(:final message) => Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.error_outline, size: 64, color: Theme.of(context).colorScheme.error),
                  const SizedBox(height: 16),
                  Text('Connection Error', style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: 8),
                  Text(message, textAlign: TextAlign.center),
                  const SizedBox(height: 16),
                  FilledButton.tonalIcon(
                    onPressed: () => ref.read(dashboardProvider.notifier).checkHealth(),
                    icon: const Icon(Icons.refresh),
                    label: const Text('Retry'),
                  ),
                ],
              ),
            }},
          ),
        );
      }}
    }}
    """).strip() + "\n")
    print(f"[OK] Created: {dashboard_screen}")

    # -- lib/shared/widgets/app_shell.dart --
    create_file(lib / "shared" / "widgets" / "app_shell.dart", f"""
    import 'package:flutter/material.dart';

    class AppShell extends StatelessWidget {{
      final Widget child;
      const AppShell({{super.key, required this.child}});

      @override
      Widget build(BuildContext context) {{
        return Scaffold(
          appBar: AppBar(title: const Text('{project_name}')),
          drawer: Drawer(
            child: ListView(
              children: [
                DrawerHeader(
                  child: Text('{project_name}', style: Theme.of(context).textTheme.headlineSmall),
                ),
                ListTile(
                  leading: const Icon(Icons.dashboard),
                  title: const Text('Dashboard'),
                  selected: true,
                  onTap: () {{}},
                ),
              ],
            ),
          ),
          body: child,
        );
      }}
    }}
    """)

    # -- lib/shared/widgets/app_card.dart --
    create_file(lib / "shared" / "widgets" / "app_card.dart", """
    import 'package:flutter/material.dart';

    class AppCard extends StatelessWidget {
      final Widget child;
      final EdgeInsetsGeometry? padding;

      const AppCard({super.key, required this.child, this.padding});

      @override
      Widget build(BuildContext context) {
        return Card(
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(color: Theme.of(context).dividerColor),
          ),
          child: Padding(
            padding: padding ?? const EdgeInsets.all(16),
            child: child,
          ),
        );
      }
    }
    """)


def create_readme(root: Path, project_name: str):
    """Create README with setup instructions."""
    display_name = project_name.replace("-", " ").title()
    package_name = project_name.replace("-", "_")

    create_file(root / "README.md", f"""
    # {display_name}

    Full-stack application with FastAPI backend and Flutter frontend.

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

    ### 2. Start Flutter Frontend

    ```bash
    cd frontend
    flutter pub get
    flutter run
    ```

    Or for web:

    ```bash
    cd frontend
    flutter run -d chrome
    ```

    ## Project Structure

    ```
    {project_name}/
    ├── backend/              # FastAPI backend (async)
    │   ├── src/{package_name}/
    │   │   ├── main.py       # FastAPI app
    │   │   ├── config.py     # Settings
    │   │   ├── database.py   # Async SQLAlchemy
    │   │   ├── models/       # SQLAlchemy models
    │   │   ├── schemas/      # Pydantic schemas
    │   │   ├── routers/      # API endpoints
    │   │   └── services/     # Business logic
    │   └── pyproject.toml
    └── frontend/             # Flutter app
        ├── lib/
        │   ├── core/         # Network, router, theme
        │   ├── features/     # Feature modules
        │   └── shared/       # Shared widgets
        └── pubspec.yaml
    ```

    ## API Endpoints

    | Method | Endpoint | Description |
    |--------|----------|-------------|
    | GET | `/api/health` | Health check |
    | POST | `/api/auth/register` | Register new user |
    | POST | `/api/auth/login` | Login |

    ## Demo Credentials

    A demo user is auto-created on first backend startup:

    - **Email:** `demo@example.com`
    - **Password:** `demo1234`

    ## Tech Stack

    **Backend:**
    - FastAPI (async) + Uvicorn
    - SQLAlchemy 2.0 (async) + asyncpg
    - Alembic for migrations
    - JWT auth (python-jose + passlib)

    **Frontend:**
    - Flutter + Dart
    - Riverpod (state management)
    - GoRouter (routing)
    - Dio (HTTP client)
    - flutter_secure_storage (JWT persistence)

    ## Next Steps

    - [ ] Set up PostgreSQL (or use `--compose` flag)
    - [ ] Configure Alembic migrations
    - [ ] Add more API endpoints
    - [ ] Add Flutter screens and features
    - [ ] Set up CI/CD
    """)


def create_gitignore(root: Path):
    """Create a .gitignore for Python + Dart/Flutter."""
    create_file(root / ".gitignore", """
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

    # Dart / Flutter
    .dart_tool/
    .packages
    .pub/
    build/
    pubspec.lock
    *.g.dart
    *.freezed.dart
    .flutter-plugins
    .flutter-plugins-dependencies

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
    coverage/
    *.test.js.snap

    # Environment variables
    .env
    .env.local

    # Database
    *.db
    *.db-journal

    # Backend specific
    backend/.venv/
    backend/__pycache__/
    backend/dist/
    backend/build/

    # Process ID files
    *.pids
    """)


def create_start_script(root: Path, project_name: str):
    """Create start.sh script for running backend + Flutter (based on docdesk pattern)."""
    package_name = project_name.replace("-", "_")

    create_file(root / "start.sh", f"""
    #!/bin/bash
    echo "🚀 Starting {project_name}..."

    ROOT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
    BACKEND_DIR="$ROOT_DIR/backend"
    FRONTEND_DIR="$ROOT_DIR/frontend"

    # ==================================
    # Cleanup existing processes
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
    sleep 1
    echo "✅ Cleanup complete"
    echo ""

    # ==================================
    # Start Docker services
    # ==================================
    if [ -f "$ROOT_DIR/docker-compose.yml" ]; then
        echo "🐳 Starting Docker services..."
        cd "$ROOT_DIR"
        docker compose up -d
        echo "✅ Docker services ready"
        echo ""
    fi

    # ==================================
    # Start backend (background)
    # ==================================
    echo "📦 Starting backend..."
    cd "$BACKEND_DIR"
    unset VIRTUAL_ENV
    uv run dev &
    BACKEND_PID=$!
    echo "✅ Backend running on http://localhost:8000"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Demo credentials:"
    echo "  Email:    demo@example.com"
    echo "  Password: demo1234"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    sleep 2

    # ==================================
    # Start frontend (foreground — enables 'r' for hot reload)
    # ==================================
    echo "🎨 Starting Flutter frontend..."
    echo "──────────────────────────────────────"
    echo "  Type 'r' for hot reload"
    echo "  Press Ctrl+C or 'q' to quit"
    echo "──────────────────────────────────────"
    echo ""
    cd "$FRONTEND_DIR"
    flutter run -d chrome

    # Frontend exited; clean up backend and Docker
    echo ""
    echo "🧹 Stopping backend..."
    kill -15 "$BACKEND_PID" 2>/dev/null
    wait "$BACKEND_PID" 2>/dev/null
    echo "✅ Backend stopped"

    if [ -f "$ROOT_DIR/docker-compose.yml" ]; then
        cd "$ROOT_DIR"
        docker compose down
        echo "✅ Docker stopped"
    fi

    cat > "$PID_FILE" << EOF
    BACKEND_PID=
    FRONTEND_PID=
    EOF
    """)

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


def main(project_name: str = "my-flutter-app", compose: bool = False):
    """Main function to orchestrate Flutter + FastAPI project creation."""
    print("=" * 60)
    print("FastAPI + Flutter Project Generator")
    print("=" * 60)

    root = Path.cwd()

    if (root / 'backend').exists() or (root / 'frontend').exists():
        print("\n[WARN] Backend or frontend directory already exists. Skipping.")
        return

    print(f"\n[INFO] Creating Flutter project: {project_name}")

    print("\n[BACKEND] Generating backend structure...")
    create_backend(root, project_name)

    print("\n[FRONTEND] Generating Flutter frontend structure...")
    create_frontend(root, project_name)
    create_frontend_extra(root, project_name)

    print("\n[DOCS] Creating README and .gitignore...")
    create_readme(root, project_name)
    create_gitignore(root)

    if compose:
        print("\n[COMPOSE] Creating docker-compose.yml...")
        create_docker_compose(root, project_name)
        db_name = project_name.replace("-", "_")
        env_path = root / "backend" / ".env"
        env_path.write_text(f"""DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/{db_name}
SECRET_KEY=change-me-to-a-random-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
DEBUG=True
""")

    print("\n[SCRIPT] Creating start.sh...")
    create_start_script(root, project_name)

    print("\n" + "=" * 60)
    print("[SUCCESS] Project created successfully!")
    print("=" * 60)
    print(f"\n[LOCATION] {root.absolute()}")
    print("\n[GUIDE] Next steps:")
    print(f"\n  ./start.sh")
    print(f"     Starts backend + Flutter")
    print(f"\n  Or manually:")
    print(f"\n  1. Backend setup:")
    print(f"     cd backend")
    print(f"     uv sync")
    print(f"     uv run dev")
    print(f"\n  2. Flutter setup (in a new terminal):")
    print(f"     cd frontend")
    print(f"     flutter pub get")
    print(f"     flutter run")
    print(f"\n  3. Open http://localhost:8000/docs for API docs")
    print(f"\n[INFO] Check README.md for more details")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create a Flutter + FastAPI project")
    parser.add_argument("project_name", nargs="?", default="my-flutter-app", help="Name of the project")
    parser.add_argument("--compose", action="store_true", help="Generate docker-compose.yml for PostgreSQL")

    args = parser.parse_args()
    main(args.project_name, compose=args.compose)
