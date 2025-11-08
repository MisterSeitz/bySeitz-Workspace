from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
from datetime import datetime


class RSSFeed(BaseModel):
    """Represents a single feed entry from an RSS source."""
    title: str
    link: HttpUrl
    source: Optional[str] = None
    published: Optional[str] = None
    summary: Optional[str] = None


class Article(BaseModel):
    """Represents a fetched and parsed news article."""
    title: str
    url: HttpUrl
    source: Optional[str] = None
    country: Optional[str] = None
    published: Optional[str] = None
    summary: Optional[str] = None
    # Removed content and image fields


class InputConfig(BaseModel):
    """Actor input config loaded from Apify input_schema.json."""
    source: str
    customFeedUrl: Optional[str] = None
    maxArticles: int = 20
    useSummarization: bool = True
    runTestMode: bool = Field(False, description="Enables internal test mode to bypass Apify Actor calls.")


class SummaryResult(BaseModel):
    """Summarization output (LLM-generated)."""
    summary: str


class DatasetRecord(BaseModel):
    """Final dataset record to push into Apify dataset."""
    source: Optional[str]
    title: str
    url: HttpUrl
    published: Optional[str] = None
    # Summary now holds the AI Overview text
    summary: Optional[str] = Field(None, description="The AI Overview summary from Google Search.") 
    
    # NEW FIELDS FOR ENHANCED VALUE
    sentiment: Optional[str] = Field(None, description="Sentiment analysis result (Positive, Neutral, Negative).")
    category: Optional[str] = Field(None, description="Primary market category (e.g., Funding, Acquisitions, IPOs).")
    key_entities: Optional[List[str]] = Field(None, description="Key companies, investors, or people mentioned.")