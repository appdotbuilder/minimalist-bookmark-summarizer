from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum


class BookmarkStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ContentExtractionStatus(str, Enum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    FILTERING = "filtering"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"


class SummaryJobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Persistent models (stored in database)
class BookmarkUpload(SQLModel, table=True):
    """Represents an uploaded HTML bookmark file"""

    __tablename__ = "bookmark_uploads"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str = Field(max_length=255)
    file_path: str = Field(max_length=500)
    file_size: int = Field(description="File size in bytes")
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    processing_status: BookmarkStatus = Field(default=BookmarkStatus.PENDING)
    total_bookmarks: Optional[int] = Field(default=None, description="Total number of bookmarks found in file")
    processed_bookmarks: int = Field(default=0, description="Number of bookmarks processed")
    error_message: Optional[str] = Field(default=None, max_length=1000)
    processing_started_at: Optional[datetime] = Field(default=None)
    processing_completed_at: Optional[datetime] = Field(default=None)

    bookmarks: List["Bookmark"] = Relationship(back_populates="upload")
    summary_jobs: List["SummaryJob"] = Relationship(back_populates="upload")


class Bookmark(SQLModel, table=True):
    """Individual bookmark extracted from uploaded file"""

    __tablename__ = "bookmarks"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    upload_id: int = Field(foreign_key="bookmark_uploads.id")
    title: str = Field(max_length=500, description="Original bookmark title")
    url: str = Field(max_length=2000, description="Bookmark URL")
    folder_path: Optional[str] = Field(default=None, max_length=1000, description="Safari bookmark folder hierarchy")
    date_added: Optional[datetime] = Field(default=None, description="When bookmark was added to Safari")
    processing_status: ContentExtractionStatus = Field(default=ContentExtractionStatus.PENDING)
    processing_started_at: Optional[datetime] = Field(default=None)
    processing_completed_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None, max_length=1000)
    retry_count: int = Field(default=0, description="Number of processing retries")

    upload: BookmarkUpload = Relationship(back_populates="bookmarks")
    extracted_content: Optional["ExtractedContent"] = Relationship(back_populates="bookmark")


class ExtractedContent(SQLModel, table=True):
    """Content extracted from bookmark URL with 24-hour filtering applied"""

    __tablename__ = "extracted_contents"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    bookmark_id: int = Field(foreign_key="bookmarks.id", unique=True)
    extraction_time: datetime = Field(default_factory=datetime.utcnow)
    page_title: Optional[str] = Field(default=None, max_length=500)
    page_url: str = Field(max_length=2000, description="Final URL after redirects")
    raw_content: str = Field(description="Raw extracted content from page")
    filtered_content: Optional[str] = Field(default=None, description="Content filtered to last 24 hours")
    content_date: Optional[datetime] = Field(default=None, description="Latest content date found on page")
    content_metadata: Dict[str, Any] = Field(
        default={}, sa_column=Column(JSON), description="Metadata about content extraction"
    )
    has_recent_content: bool = Field(default=False, description="Whether page contains content from last 24 hours")
    content_summary: Optional[str] = Field(default=None, max_length=2000, description="AI-generated summary nugget")
    summary_generated_at: Optional[datetime] = Field(default=None)
    extraction_method: str = Field(max_length=100, description="Method used for content extraction")
    page_load_time: Optional[Decimal] = Field(default=None, description="Time taken to load page in seconds")

    bookmark: Bookmark = Relationship(back_populates="extracted_content")


class SummaryJob(SQLModel, table=True):
    """Job for generating final summary from all bookmark summaries"""

    __tablename__ = "summary_jobs"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    upload_id: int = Field(foreign_key="bookmark_uploads.id")
    status: SummaryJobStatus = Field(default=SummaryJobStatus.PENDING)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    bookmarks_included: int = Field(default=0, description="Number of bookmarks with summaries included")
    final_summary: Optional[str] = Field(default=None, description="Final consolidated summary")
    summary_metadata: Dict[str, Any] = Field(
        default={}, sa_column=Column(JSON), description="Metadata about summary generation"
    )
    error_message: Optional[str] = Field(default=None, max_length=1000)
    llm_model_used: Optional[str] = Field(
        default=None, max_length=100, description="LLM model used for final summarization"
    )
    token_count: Optional[int] = Field(default=None, description="Approximate token count for final summary")

    upload: BookmarkUpload = Relationship(back_populates="summary_jobs")


class ProcessingLog(SQLModel, table=True):
    """Audit log for tracking processing steps and performance"""

    __tablename__ = "processing_logs"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    upload_id: Optional[int] = Field(default=None, foreign_key="bookmark_uploads.id")
    bookmark_id: Optional[int] = Field(default=None, foreign_key="bookmarks.id")
    operation: str = Field(max_length=100, description="Operation being performed")
    status: str = Field(max_length=50, description="Operation status")
    duration_seconds: Optional[Decimal] = Field(default=None, description="Time taken for operation")
    details: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), description="Additional operation details")
    error_details: Optional[str] = Field(default=None, max_length=2000)


# Non-persistent schemas (for validation, forms, API requests/responses)
class BookmarkUploadCreate(SQLModel, table=False):
    filename: str = Field(max_length=255)
    file_path: str = Field(max_length=500)
    file_size: int


class BookmarkCreate(SQLModel, table=False):
    upload_id: int
    title: str = Field(max_length=500)
    url: str = Field(max_length=2000)
    folder_path: Optional[str] = Field(default=None, max_length=1000)
    date_added: Optional[datetime] = Field(default=None)


class ExtractedContentCreate(SQLModel, table=False):
    bookmark_id: int
    page_title: Optional[str] = Field(default=None, max_length=500)
    page_url: str = Field(max_length=2000)
    raw_content: str
    filtered_content: Optional[str] = Field(default=None)
    content_date: Optional[datetime] = Field(default=None)
    content_metadata: Dict[str, Any] = Field(default={})
    has_recent_content: bool = Field(default=False)
    extraction_method: str = Field(max_length=100)
    page_load_time: Optional[Decimal] = Field(default=None)


class ContentSummaryUpdate(SQLModel, table=False):
    content_summary: str = Field(max_length=2000)
    summary_generated_at: datetime


class SummaryJobCreate(SQLModel, table=False):
    upload_id: int


class SummaryJobUpdate(SQLModel, table=False):
    status: SummaryJobStatus
    bookmarks_included: Optional[int] = Field(default=None)
    final_summary: Optional[str] = Field(default=None)
    summary_metadata: Optional[Dict[str, Any]] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    llm_model_used: Optional[str] = Field(default=None)
    token_count: Optional[int] = Field(default=None)


class ProcessingLogCreate(SQLModel, table=False):
    upload_id: Optional[int] = Field(default=None)
    bookmark_id: Optional[int] = Field(default=None)
    operation: str = Field(max_length=100)
    status: str = Field(max_length=50)
    duration_seconds: Optional[Decimal] = Field(default=None)
    details: Dict[str, Any] = Field(default={})
    error_details: Optional[str] = Field(default=None)


# Response schemas for API
class BookmarkSummaryResponse(SQLModel, table=False):
    """Response schema for individual bookmark processing results"""

    bookmark_id: int
    title: str
    url: str
    status: ContentExtractionStatus
    has_recent_content: bool
    content_summary: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)


class UploadSummaryResponse(SQLModel, table=False):
    """Response schema for upload processing results"""

    upload_id: int
    filename: str
    status: BookmarkStatus
    total_bookmarks: Optional[int] = Field(default=None)
    processed_bookmarks: int
    bookmarks_with_summaries: int
    final_summary: Optional[str] = Field(default=None)
    processing_time_seconds: Optional[int] = Field(default=None)
    upload_time: str  # ISO format datetime string
    processing_completed_at: Optional[str] = Field(default=None)  # ISO format datetime string
