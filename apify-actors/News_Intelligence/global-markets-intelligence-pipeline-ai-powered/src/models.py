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


class InputConfig(BaseModel):
    """Actor input config loaded from Apify input_schema.json."""
    source: str
    customFeedUrl: Optional[str] = None
    maxArticles: int = 20
    useSummarization: bool = True # This will now trigger the LLM summary
    runTestMode: bool = Field(False, description="Enables internal test mode to bypass all external API calls.")


class SummaryResult(BaseModel):
    """Summarization output (LLM-generated)."""
    summary: str


class DatasetRecord(BaseModel):
    """Final dataset record to push into Apify dataset."""
    source: Optional[str]
    title: str
    url: HttpUrl
    published: Optional[str] = None
    # Summary now holds the LLM-generated text (or the RSS summary if LLM failed)
    summary: Optional[str] = Field(None, description="The LLM-generated summary.") 
    
    # NEW FIELDS FOR ANALYSIS (used by both LLM and AV)
    sentiment: Optional[str] = Field(None, description="Sentiment analysis result (Positive, Neutral, Negative).")
    category: Optional[str] = Field(None, description="Primary market category (e.g., Technology, Geopolitics).")
    key_entities: Optional[List[str]] = Field(None, description="Key companies or people mentioned.")
    gdelt_tone: Optional[float] = Field(None, description="Repurposed for LLM/Alpha Vantage numerical score (-10.0 to +10.0).")