import uuid
from datetime import datetime

from sqlalchemy import String, ForeignKey, Numeric, Integer, SmallInteger, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    repositories: Mapped[list["Repository"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    financial_config: Mapped["FinancialConfig"] = relationship(back_populates="company", uselist=False, cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="engineering_manager")
    hashed_password: Mapped[str | None] = mapped_column(String(255))
    github_access_token: Mapped[str | None] = mapped_column(Text)  # stored ENCRYPTED via app/core/security.py
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped["Company"] = relationship(back_populates="users")


class FinancialConfig(Base):
    __tablename__ = "financial_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), unique=True)
    avg_developer_hourly_rate: Mapped[float] = mapped_column(Numeric(10, 2), default=50.00)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    working_hours_per_month: Mapped[float] = mapped_column(Numeric(6, 2), default=160.00)
    risk_multiplier: Mapped[float] = mapped_column(Numeric(4, 2), default=1.00)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="financial_config")


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(20), default="github")
    external_repo_id: Mapped[str] = mapped_column(String(100), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    connected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="repositories")
    scan_jobs: Mapped[list["ScanJob"]] = relationship(back_populates="repository", cascade="all, delete-orphan")


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    commit_sha: Mapped[str | None] = mapped_column(String(40))
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    repository: Mapped["Repository"] = relationship(back_populates="scan_jobs")
    code_metrics: Mapped[list["CodeMetric"]] = relationship(back_populates="scan_job", cascade="all, delete-orphan")
    financial_result: Mapped["FinancialLossResult"] = relationship(back_populates="scan_job", uselist=False, cascade="all, delete-orphan")
    priority_fixes: Mapped[list["PriorityFix"]] = relationship(back_populates="scan_job", cascade="all, delete-orphan")


class CodeMetric(Base):
    __tablename__ = "code_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scan_jobs.id", ondelete="CASCADE"))
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    language: Mapped[str | None] = mapped_column(String(50))
    cyclomatic_complexity: Mapped[float | None] = mapped_column(Numeric(10, 2))
    maintainability_index: Mapped[float | None] = mapped_column(Numeric(10, 2))
    lines_of_code: Mapped[int | None] = mapped_column(Integer)
    churn_last_90_days: Mapped[int] = mapped_column(Integer, default=0)
    unique_authors_90_days: Mapped[int] = mapped_column(Integer, default=0)
    last_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scan_job: Mapped["ScanJob"] = relationship(back_populates="code_metrics")


class FinancialLossResult(Base):
    __tablename__ = "financial_loss_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scan_jobs.id", ondelete="CASCADE"), unique=True)
    overall_health_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    monthly_financial_loss: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    estimated_dev_hours_wasted_monthly: Mapped[float | None] = mapped_column(Numeric(10, 2))
    time_to_market_delay_days: Mapped[float | None] = mapped_column(Numeric(6, 2))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scan_job: Mapped["ScanJob"] = relationship(back_populates="financial_result")


class PriorityFix(Base):
    __tablename__ = "priority_fixes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scan_jobs.id", ondelete="CASCADE"))
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    rank: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    estimated_monthly_loss: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    reason_summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scan_job: Mapped["ScanJob"] = relationship(back_populates="priority_fixes")
