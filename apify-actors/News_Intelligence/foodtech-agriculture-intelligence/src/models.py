from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class RSSFeed(BaseModel):
    title: str
    link: HttpUrl
    source: Optional[str] = None
    published: Optional[str] = None
    summary: Optional[str] = None

class Article(BaseModel):
    title: str
    url: HttpUrl
    source: Optional[str] = None
    country: Optional[str] = None
    published: Optional[str] = None
    summary: Optional[str] = None

class InputConfig(BaseModel):
    source: str
    customFeedUrl: Optional[str] = None
    maxArticles: int = 10
    # --- ADDED FIELDS ---
    region: Optional[str] = Field("wt-wt", description="Region for DuckDuckGo search (e.g., us-en, za-en). 'wt-wt' means any region.")
    timeLimit: Optional[str] = Field("any", description="Time limit for DuckDuckGo search ('d': day, 'w': week, 'm': month, 'any': no limit).")
    runTestMode: bool = Field(False, description="Enables internal test mode to bypass external API calls.")

class SummaryResult(BaseModel):
    summary: str

class SnippetSource(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None
    date: Optional[str] = None

class DatasetRecord(BaseModel):
    source: Optional[str]
    title: str
    url: HttpUrl
    published: Optional[str] = None
    summary: Optional[str] = Field(None, description="AI-generated summary of the article's content.")
    sentiment: Optional[str] = Field(None, description="Assessed market dynamic/impact (e.g., High Growth, Cooling Market, Policy Driven).")
    category: Optional[str] = Field(None, description="The primary thematic category of the news article (e.g., Residential Sales, Commercial/Office, Investment/Financing).")
    key_entities: Optional[List[str]] = Field(None, description="Key cities, regions, companies, or financial metrics mentioned in the article.")
    snippet_sources: Optional[List[SnippetSource]] = Field(None, description="A list of source titles and URLs used to generate the AI summary.")