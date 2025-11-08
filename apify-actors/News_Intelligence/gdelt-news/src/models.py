# models.py (GDELT Enrichment Pipeline)

from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
from datetime import datetime


class InputConfig(BaseModel):
    """Configuration model for the GDELT Enrichment Actor input."""
    # 🌟 FIX: API Credentials are now optional in the input,
    # as they will be read from secret environment variables.
    openaiApiKey: Optional[str] = None
    googleApiKey: Optional[str] = None
    googleCseId: Optional[str] = None
    
    # GDELT Query and Fetching Parameters
    query: str
    max_records_limit: int = 100
    timespan_offset: Optional[str] = Field(None)
    start_datetime: Optional[str] = Field(None)
    end_datetime: Optional[str] = Field(None)
    sort_by: Optional[str] = Field("HybridRel")
    source_lang: Optional[str] = Field(None)
    
    # Processing Flags
    runTestMode: bool = Field(False, description="Enables internal test mode to bypass Apify Actor calls.")


class DatasetRecord(BaseModel):
    """Final dataset record to push into Apify dataset."""
    source: Optional[str]
    title: str
    url: HttpUrl
    published: Optional[str] = Field(None, description="The publication date/time in ISO 8601 format.")
    summary: Optional[str] = Field(None, description="The AI Overview summary from Google Search.") 
    
    # Enriched Analysis Fields
    sentiment: Optional[str] = Field(None, description="**Disruptive Potential:** (High Risk, Medium Risk, Low Risk).")
    category: Optional[str] = Field(None, description="**AI Type/Focus:** (e.g., LLM, Computer Vision, Policy).")
    key_entities: Optional[List[str]] = Field(None, description="Key companies, models, or researchers mentioned.")