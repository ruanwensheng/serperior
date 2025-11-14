#ABSTRACT
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union
from datetime import datetime, date
import pandas as pd

from .base_crawler import BaseCrawler




class AsyncBaseCrawler(BaseCrawler):
    """
    Base class for asynchronous crawlers
    
    Note: Async crawlers handle saving internally within crawl_async()
          This allows proper incremental merge logic during the crawl process
          
          Date validation is relaxed for async crawlers to support reversed
          date ranges (e.g., press crawler: start=newest, end=oldest)
    """
    
    def __init__(
        self,
        start_date: Union[str, date, datetime],
        end_date: Union[str, date, datetime],
        output_folder: Optional[str] = "data",
        auto_save: bool = True
    ):
        """
        Initialize async crawler with relaxed date validation
        
        Note: Skips start <= end validation to allow reversed ranges
              (e.g., VnExpressPressCrawler uses start=newest, end=oldest)
        """
        # Parse dates without validation
        self.start_date = self._parse_date(start_date)
        self.end_date = self._parse_date(end_date)
        self.output_folder = output_folder
        self.auto_save = auto_save
        
        # Convert to datetime for internal use
        self.start_dt = datetime.fromisoformat(self.start_date)
        self.end_dt = datetime.fromisoformat(self.end_date)
        
        # Validate auto_save requirement
        if self.auto_save and self.output_folder is None:
            raise ValueError("auto_save=True requires output_folder to be specified")
        
        self._ensure_output_folder()
    
    @abstractmethod
    async def crawl_async(self) -> pd.DataFrame:
        """Asynchronous crawling method - must be implemented by subclasses"""
        pass
    
    def crawl(self) -> pd.DataFrame:
        """Not supported - use crawl_async() instead"""
        raise NotImplementedError("AsyncBaseCrawler requires async execution. Use crawl_async()")
    
    async def crawl_and_save_async(self) -> pd.DataFrame:
        """Async crawl (save handled internally by crawl_async for proper incremental logic)"""
        print(f"\n{'='*80}")
        print(f"{self.__class__.__name__}: {self.start_date} → {self.end_date}")
        print(f"Auto-save: {'Enabled' if self.auto_save else 'Disabled'}")
        if self.auto_save:
            print(f"Output: {self.output_folder}")
        print(f"{'='*80}\n")
        
        dataframe = await self.crawl_async()
        
        if dataframe is not None and not dataframe.empty:
            print(f"Returned {len(dataframe)} records\n")
        else:
            print(f"No data retrieved\n")
        
        return dataframe