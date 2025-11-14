"""
Crawl Pipeline Orchestrator
Manages the complete data collection workflow
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, date

import pandas as pd

from .dantri_crawler import DantriCrawler
# for future things to come actually...

class DataPipeline:
    def __init__(
        self,
        start_date: str,
        end_date: str,
        output_folder: str = "data",
        auto_save: bool = True
    ):
       
        self.start_date = start_date
        self.end_date = end_date
        self.output_folder = output_folder
        self.auto_save = auto_save
        
        self.crawled_data: Dict[str, pd.DataFrame] = {}
    
    
    async def crawl_press_news_async(self,articles_per_day: Optional[int] = None,max_workers: int = 6,incremental: bool = True) -> pd.DataFrame:
        
        print("\n" + "="*80)
        print("ASYNCHRONOUS DATA COLLECTION - PRESS NEWS")
        print("="*80 + "\n")
        
        try:
            press_crawler = DantriCrawler(
                start_date=self.end_date,    # Newest date (crawl FROM here)
                end_date=self.start_date,    # Oldest date (crawl TO here)
                output_folder=self.output_folder,
                max_workers=max_workers,
                articles_per_day=articles_per_day,
                incremental=incremental,
                auto_save=self.auto_save
            )
            
            press_data = await press_crawler.crawl_and_save_async()
            self.crawled_data['press_news'] = press_data
            
            print("\nNOTE: Press news data saved separately.")
            print("    NOT merged into complete dataset (requires NLP processing).\n")
            
            return press_data
        except Exception as error:
            print(f"Error in VnExpressPressCrawler: {error}\n")
            return pd.DataFrame()
    
    
    async def run_complete_pipeline(
        self,
        include_press_news: bool = True,
        foreign_headless: bool = True,
        foreign_incremental: bool = True,
        press_articles_per_day: Optional[int] = None,
        press_incremental: bool = True
    ) -> Dict[str, pd.DataFrame]:
 
        print("\n" + "="*80)
        print("DATA COLLECTION PIPELINE")
        print(f"Date Range: {self.start_date} → {self.end_date}")
        print("="*80)
        
        # sync source (no actually.. wait for development)
        # asynv source
        async_tasks = []
        
        if include_press_news:
            async_tasks.append(
                self.crawl_press_news_async(
                    articles_per_day=press_articles_per_day,
                    incremental=press_incremental
                )
            )
        
        if async_tasks:
            await asyncio.gather(*async_tasks)

        self.create_complete_dataset()
        
        print("\n" + "="*80)
        print("PIPELINE COMPLETED SUCCESSFULLY")
        print("="*80 + "\n")
        
        return self.crawled_data
    


#=============
async def run_pipeline( start_date: str, end_date: str, output_folder: str = "data",
                       include_press_news: bool = True,
                       auto_save: bool = True ) -> Dict[str, pd.DataFrame]:
    pipeline = DataPipeline(start_date, end_date, output_folder, auto_save)
    return await pipeline.run_complete_pipeline(
        include_press_news=include_press_news
    )