#ABSTRACT
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union
from datetime import datetime, date
import pandas as pd

class BaseCrawler(ABC):
   
    def __init__(
        self, 
        start_date: Union[str, date, datetime],
        end_date: Union[str, date, datetime],
        output_folder: Optional[str] = "data",
        auto_save: bool = True
    ):
        self.start_date = self._parse_date(start_date)
        self.end_date = self._parse_date(end_date)
        self.output_folder = output_folder
        self.auto_save = auto_save
        
        start_dt = datetime.fromisoformat(self.start_date)
        end_dt = datetime.fromisoformat(self.end_date)
        if start_dt > end_dt:
            raise ValueError(f"start_date ({self.start_date}) must be <= end_date ({self.end_date})")
        
        if self.auto_save and self.output_folder is None:
            raise ValueError("auto_save=True requires output_folder to be specified")
        
        self._ensure_output_folder()

    # str/date/datetime date -> str
    @staticmethod
    def _parse_date(date_input: Union[str, date, datetime]) -> str:
 
        if isinstance(date_input, str):
            datetime.fromisoformat(date_input) # inplace True
            return date_input
        elif isinstance(date_input, datetime):
            return date_input.strftime('%Y-%m-%d')
        elif isinstance(date_input, date):
            return date_input.isoformat()
        else:
            raise ValueError(f"Unsupported date format: {type(date_input)}")
    
    def _ensure_output_folder(self) -> None:
        """Create output folder if needed"""
        if self.output_folder is not None:
            Path(self.output_folder).mkdir(parents=True, exist_ok=True)
    
    def _get_output_filepath(self, data_name: str) -> Optional[str]:
        """
        Generate output file path for saving data
        
        Note: Uses fixed filename (no date range) to support incremental crawling.
              Incremental crawlers append/merge new data to existing file.
        """
        if self.output_folder is None:
            return None
        filename = f"{data_name}.csv"
        return os.path.join(self.output_folder, filename)
    
    def save_dataframe(self, dataframe: pd.DataFrame, data_name: str, index: bool = False) -> Optional[str]:
        """Save DataFrame to CSV"""
        filepath = self._get_output_filepath(data_name)
        if filepath is None:
            print(f"Warning: Cannot save {data_name} (no output folder)")
            return None
        dataframe.to_csv(filepath, index=index, encoding='utf-8-sig')
        print(f"Saved {data_name} to: {filepath}")
        return filepath
    
    @abstractmethod
    def crawl(self) -> pd.DataFrame:
        """Main crawling method - must be implemented by subclasses"""
        pass
    
    def crawl_and_save(self) -> pd.DataFrame:
        """Crawl data and optionally save based on auto_save"""
        print(f"\n{'='*80}")
        print(f"{self.__class__.__name__}: {self.start_date} → {self.end_date}")
        print(f"Auto-save: {'Enabled' if self.auto_save else 'Disabled'}")
        if self.auto_save:
            print(f"Output: {self.output_folder}")
        print(f"{'='*80}\n")
        
        dataframe = self.crawl()
        
        if dataframe is not None and not dataframe.empty:
            if self.auto_save:
                self.save_dataframe(dataframe, self._get_data_name(), index=self._save_with_index())
            print(f"Crawled {len(dataframe)} records\n")
        else:
            print(f"No data retrieved\n")
            
        return dataframe
    
    @abstractmethod
    def _get_data_name(self) -> str:
        """Get identifier name for this data source"""
        pass
    
    def _save_with_index(self) -> bool:
        """Determine if DataFrame index should be saved"""
        return False
    