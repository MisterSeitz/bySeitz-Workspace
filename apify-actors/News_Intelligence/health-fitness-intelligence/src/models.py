from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
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
    maxArticles: int = 20
    # --- NEW DDG FIELDS ---
    region: str = Field("wt-wt", description="Region for search results.")
    timeLimit: str = Field("w", description="Time limit for search results.")
    # ----------------------
    runTestMode: bool = Field(False, description="Enables internal test mode to bypass Apify Actor calls.")

class SummaryResult(BaseModel):
    summary: str

class DatasetRecord(BaseModel):
    source: Optional[str]
    title: str
    url: HttpUrl
    published: Optional[str] = None
    summary: Optional[str] = Field(None, description="AI-generated summary of the article's content.")
    sentiment: Optional[str] = Field(None, description="Assessed importance level of the news event (e.g., High Importance, General Info/Tip).")
    category: Optional[str] = Field(None, description="The primary thematic category of the news article (e.g., General Fitness/Training, Nutrition/Recipes).")
    key_entities: Optional[List[str]] = Field(None, description="Key ingredients, exercises, health concepts, or brands mentioned.")