import pandas as pd
import numpy as np
import re
from difflib import SequenceMatcher
from typing import Dict

class DataPreprocessor:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.processed_df = None
        self.matched_products = None
        self.price_comparison = None
        
    def clean_data(self) -> pd.DataFrame:
        df = self.df.copy()
        
        # Remove duplicates
        df = df.drop_duplicates()
        
        # Handle brand
        df['brand'] = df['brand'].fillna('Unknown')
        df['brand'] = df['brand'].str.lower()
        
        # Clean price - FIXED: Remove rows with invalid prices BEFORE fillna
        df['price_rupees'] = pd.to_numeric(df['price_rupees'], errors='coerce')
        df = df[df['price_rupees'].notna() & (df['price_rupees'] > 0)]
        
        # Handle URL
        df['url'] = df['url'].fillna('')
        
        # Clean weight - FIXED: Don't fillna(0) before extraction
        df['weight_grams'] = pd.to_numeric(df['weight_grams'], errors='coerce')
        df['weight_grams'] = df.apply(
            lambda row: self._extract_weight(row['pack_display'])
            if pd.isna(row['weight_grams']) or row['weight_grams'] == 0 
            else row['weight_grams'], axis=1
        )
        
        # Standardize names
        df['product_name_clean'] = df['product_name'].apply(self._clean_product_name)
        df['brand_clean'] = df['brand'].str.strip().str.title()
        
        self.processed_df = df
        return df
    
    def _extract_weight(self, pack_display: str) -> float:
        if pd.isna(pack_display):
            return np.nan
        
        # Look for weight patterns
        match = re.search(r'(\d+\.?\d*)\s*(g|kg|ml|l)\b', str(pack_display).lower(), re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = match.group(2).lower()
            
            # Convert to grams
            if unit in ['kg', 'l']:
                return value * 1000
            else:
                return value
        return np.nan
    
    def _clean_product_name(self, name: str) -> str:
        if pd.isna(name):
            return ''
        
        name = str(name).lower()
        # FIXED: Replace with space to avoid word concatenation
        name = re.sub(r'[^a-z0-9\s]', ' ', name)
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        return name
    
    def calculate_unit_price(self) -> pd.DataFrame:
        df = self.processed_df.copy()
        
        df['price_per_100g'] = df.apply(
            lambda row: (row['price_rupees'] / row['weight_grams'] * 100) 
            if pd.notna(row['weight_grams']) and row['weight_grams'] > 0 
            else np.nan, 
            axis=1
        )
        
        self.processed_df = df
        return df

    def _similarity_score(self, str1: str, str2: str) -> float:
        return SequenceMatcher(None, str1, str2).ratio()
    
    def _extract_keywords(self, name: str) -> set:
        stop_words = {'the', 'and', 'or', 'of', 'in', 'on', 'for', 'with', 'a', 'an', 'to', 'but', 'by', 'from'}
        words = name.lower().split()
        keywords = {word for word in words if word not in stop_words and len(word) > 2}
        return keywords
    
    def match_products(self, threshold: float = 0.7, brand_match_req: bool = True) -> pd.DataFrame:
        df = self.processed_df.copy()
        matches = []
        
        for brand in df['brand_clean'].unique():
            brand_df = df[df['brand_clean'] == brand]
            platforms = brand_df['platform'].unique()
            
            if len(platforms) < 2:
                continue
            
            for i, row1 in brand_df.iterrows():
                for j, row2 in brand_df.iterrows():
                    if i >= j or row1['platform'] == row2['platform']:
                        continue
                    
                    if brand_match_req and row1['brand_clean'] != row2['brand_clean']:
                        continue
                    
                    # Calculate similarity
                    sim_score = self._similarity_score(row1['product_name_clean'], row2['product_name_clean'])
                    
                    # Keyword matching
                    keywords1 = self._extract_keywords(row1['product_name_clean'])
                    keywords2 = self._extract_keywords(row2['product_name_clean'])
                    keyword_overlap = len(keywords1 & keywords2) / max(len(keywords1), len(keywords2), 1)
                    
                    combined_score = (sim_score * 0.6) + (keyword_overlap * 0.4)
                    
                    # Weight matching
                    weight_match = False 
                    if pd.notna(row1['weight_grams']) and pd.notna(row2['weight_grams']):
                        weight_diff = abs(row1['weight_grams'] - row2['weight_grams'])
                        weight_match = weight_diff / max(row1['weight_grams'], row2['weight_grams']) < 0.1
                    
                    if combined_score >= threshold and (weight_match or pd.isna(row1['weight_grams'])):
                        matches.append({
                            'product_name': row1['product_name'],
                            'brand': row1['brand_clean'],
                            'weight_grams': row1['weight_grams'],
                            'platform_1': row1['platform'],
                            'price_1': row1['price_rupees'],
                            'price_per_100g_1': row1['price_per_100g'],
                            'url_1': row1['url'],
                            'platform_2': row2['platform'],
                            'price_2': row2['price_rupees'],
                            'price_per_100g_2': row2['price_per_100g'],
                            'url_2': row2['url'],
                            'similarity_score': combined_score
                        })
        
        self.matched_products = pd.DataFrame(matches)
        return self.matched_products
    
    def compare_prices(self) -> pd.DataFrame:
        if self.matched_products is None or len(self.matched_products) == 0:
            print("No matched products found.")
            return pd.DataFrame()
        
        df = self.matched_products.copy()
        
        # Calculate differences
        df['price_diff'] = df['price_2'] - df['price_1']
        df['price_diff_pct'] = (df['price_diff'] / df[['price_1', 'price_2']].min(axis=1)) * 100
        
        df['unit_price_diff'] = df['price_per_100g_2'] - df['price_per_100g_1']
        df['unit_price_diff_pct'] = (df['unit_price_diff'] / df[['price_per_100g_1', 'price_per_100g_2']].min(axis=1)) * 100
        
        # Identify cheaper platform
        df['cheaper_platform'] = df.apply(
            lambda row: row['platform_1'] if row['price_1'] < row['price_2'] else row['platform_2'], 
            axis=1
        )
        
        df['best_price'] = df[['price_1', 'price_2']].min(axis=1)
        df['savings'] = abs(df['price_diff'])
        
        # Sort by savings
        df = df.sort_values(by='savings', ascending=False)
        
        self.price_comparison = df
        return df
    
    def get_platform_summary(self) -> pd.DataFrame:
        df = self.processed_df.copy()
        
        # FIXED: Updated aggregation to match column renaming
        summary = df.groupby('platform').agg({
            'product_name': 'nunique',
            'price_rupees': ['mean', 'median', 'min', 'max'],
            'price_per_100g': ['mean', 'median']
        }).round(2)

        summary.columns = ['_'.join(col).strip() for col in summary.columns]
        summary = summary.rename(columns={
            'product_name_nunique': 'total_products',
            'price_rupees_mean': 'avg_price',
            'price_rupees_median': 'median_price',
            'price_rupees_min': 'min_price',
            'price_rupees_max': 'max_price',
            'price_per_100g_mean': 'avg_price_per_100g',
            'price_per_100g_median': 'median_price_per_100g'
        })

        return summary.reset_index()
    
    def get_brand_summary(self) -> pd.DataFrame:
        df = self.processed_df.copy()
        
        summary = df.groupby('brand_clean').agg({
            'product_name': 'nunique',
            'platform': lambda x: x.nunique(),
            'price_rupees': 'mean',
            'price_per_100g': 'mean',
        }).round(2)

        summary.columns = ['product_count', 'platforms_available', 'avg_price', 'avg_price_per_100g']
        summary = summary.sort_values('product_count', ascending=False)
                
        return summary.reset_index()
    
    def export_for_dashboard(self, output_prefix: str='processed'):
        """Export all processed data to CSV files"""
        if self.processed_df is not None:
            self.processed_df.to_csv(f'{output_prefix}_products.csv', index=False)
            print(f"✓ Exported: {output_prefix}_products.csv")
            
        if self.matched_products is not None and len(self.matched_products) > 0:
            self.matched_products.to_csv(f'{output_prefix}_matched.csv', index=False)
            print(f"✓ Exported: {output_prefix}_matched.csv")
            
        if self.price_comparison is not None and len(self.price_comparison) > 0:
            self.price_comparison.to_csv(f'{output_prefix}_price_comparison.csv', index=False)
            print(f"✓ Exported: {output_prefix}_price_comparison.csv")
            
        platform_summary = self.get_platform_summary()
        platform_summary.to_csv(f'{output_prefix}_platform_summary.csv', index=False)
        print(f"✓ Exported: {output_prefix}_platform_summary.csv")
        
        brand_summary = self.get_brand_summary()
        brand_summary.to_csv(f'{output_prefix}_brand_summary.csv', index=False)
        print(f"✓ Exported: {output_prefix}_brand_summary.csv")
        
        print("\n✓ All files exported successfully!")

    def run_full_pipeline(self, export: bool = True) -> Dict:
        """Run the complete preprocessing pipeline"""
        print("Starting preprocessing pipeline...\n")
        
        print("Step 1: Cleaning data...")
        self.clean_data()
        print(f"✓ Cleaned {len(self.processed_df)} records\n")
        
        print("Step 2: Calculating unit prices...")
        self.calculate_unit_price()
        print(f"✓ Calculated unit prices\n")
        
        print("Step 3: Matching products across platforms...")
        self.match_products()
        match_count = len(self.matched_products) if self.matched_products is not None else 0
        print(f"✓ Found {match_count} product matches\n")
        
        print("Step 4: Comparing prices...")
        self.compare_prices()
        print(f"✓ Generated price comparisons\n")
        
        if export:
            print("Step 5: Exporting data...")
            self.export_for_dashboard()
        
        return {
            'processed_data': self.processed_df,
            'matched_products': self.matched_products,
            'price_comparison': self.price_comparison,
            'platform_summary': self.get_platform_summary(),
            'brand_summary': self.get_brand_summary()
        }
    
if __name__ == "__main__":
    # Load data
    df = pd.read_csv('data/bread_products.csv')
    
    # Initialize and run
    preprocessor = DataPreprocessor(df)
    results = preprocessor.run_full_pipeline(export=True)
    
    # Print summary
    print("\n" + "="*60)
    print("PREPROCESSING SUMMARY")
    print("="*60)
    print(f"Total products: {len(results['processed_data'])}")
    print(f"Matched products: {len(results['matched_products'])}")
    if len(results['price_comparison']) > 0:
        print(f"Average savings: ₹{results['price_comparison']['savings'].mean():.2f}")
        print(f"Max savings: ₹{results['price_comparison']['savings'].max():.2f}")