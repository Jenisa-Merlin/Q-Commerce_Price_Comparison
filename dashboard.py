import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# Page configuration
st.set_page_config(
    page_title="E-commerce Price Comparison Dashboard",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .deal-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Load all preprocessed data"""
    try:
        processed_data = pd.read_csv('processed_products.csv')
        matched_products = pd.read_csv('processed_matched.csv')
        price_comparison = pd.read_csv('processed_price_comparison.csv')
        platform_summary = pd.read_csv('processed_platform_summary.csv')
        brand_summary = pd.read_csv('processed_brand_summary.csv')
        
        return {
            'processed': processed_data,
            'matched': matched_products,
            'comparison': price_comparison,
            'platform_summary': platform_summary,
            'brand_summary': brand_summary
        }
    except FileNotFoundError as e:
        st.error(f"Data files not found: {e}")
        st.info("Please run the preprocessing pipeline first to generate the required CSV files.")
        return None

def create_price_distribution(df, platform_filter=None):
    """Create price distribution chart"""
    if platform_filter and len(platform_filter) > 0:
        df = df[df['platform'].isin(platform_filter)]
    
    if len(df) == 0:
        return go.Figure().add_annotation(text="No data available", showarrow=False)
    
    fig = px.box(
        df, 
        x='platform', 
        y='price_rupees',
        color='platform',
        title='Price Distribution by Platform',
        labels={'price_rupees': 'Price (₹)', 'platform': 'Platform'},
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    
    fig.update_layout(
        showlegend=False,
        height=400,
        xaxis_title='Platform',
        yaxis_title='Price (₹)'
    )
    
    return fig

def create_unit_price_comparison(df, platform_filter=None):
    """Create unit price comparison chart"""
    if platform_filter and len(platform_filter) > 0:
        df = df[df['platform'].isin(platform_filter)]
    
    if len(df) == 0:
        return go.Figure().add_annotation(text="No data available", showarrow=False)
    
    # Remove NaN values before grouping
    df_clean = df[df['price_per_100g'].notna()].copy()
    
    if len(df_clean) == 0:
        return go.Figure().add_annotation(text="No unit price data available", showarrow=False)
    
    avg_unit_prices = df_clean.groupby('platform')['price_per_100g'].mean().reset_index()
    avg_unit_prices = avg_unit_prices.sort_values('price_per_100g')
    
    fig = px.bar(
        avg_unit_prices,
        x='platform',
        y='price_per_100g',
        color='platform',
        title='Average Price per 100g by Platform',
        labels={'price_per_100g': 'Price per 100g (₹)', 'platform': 'Platform'},
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    
    fig.update_layout(
        showlegend=False,
        height=400,
        xaxis_title='Platform',
        yaxis_title='Price per 100g (₹)'
    )
    
    return fig

def create_brand_analysis(df):
    """Create brand analysis chart"""
    if len(df) == 0:
        return go.Figure().add_annotation(text="No data available", showarrow=False)
    
    brand_data = df.groupby('brand_clean').agg({
        'product_name': 'count',
        'price_rupees': 'mean'
    }).reset_index()
    
    brand_data.columns = ['Brand', 'Product Count', 'Avg Price']
    brand_data = brand_data.sort_values('Product Count', ascending=False).head(10)
    
    if len(brand_data) == 0:
        return go.Figure().add_annotation(text="No brand data available", showarrow=False)
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Top 10 Brands by Product Count', 'Average Price by Brand'),
        specs=[[{"type": "bar"}, {"type": "bar"}]]
    )
    
    fig.add_trace(
        go.Bar(x=brand_data['Brand'], y=brand_data['Product Count'], 
               marker_color='indianred', name='Product Count'),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(x=brand_data['Brand'], y=brand_data['Avg Price'], 
               marker_color='lightsalmon', name='Avg Price'),
        row=1, col=2
    )
    
    fig.update_layout(height=400, showlegend=False)
    fig.update_xaxes(tickangle=45)
    
    return fig

def create_savings_chart(df):
    """Create savings opportunity chart"""
    if len(df) == 0:
        return go.Figure().add_annotation(text="No savings data available", showarrow=False)
    
    top_savings = df.nlargest(min(15, len(df)), 'savings')
    
    # Truncate long product names
    top_savings = top_savings.copy()
    top_savings['product_name_short'] = top_savings['product_name'].apply(
        lambda x: x[:50] + '...' if len(str(x)) > 50 else x
    )
    
    fig = px.bar(
        top_savings,
        x='savings',
        y='product_name_short',
        orientation='h',
        color='savings',
        title='Top Products with Highest Savings Potential',
        labels={'savings': 'Savings (₹)', 'product_name_short': 'Product'},
        color_continuous_scale='Reds'
    )
    
    fig.update_layout(
        height=500,
        yaxis={'categoryorder': 'total ascending'},
        xaxis_title='Potential Savings (₹)',
        yaxis_title='Product'
    )
    
    return fig

def create_platform_comparison_matrix(df):
    """Create platform vs platform price comparison heatmap"""
    if len(df) == 0:
        return go.Figure().add_annotation(text="No comparison data available", showarrow=False)
    
    # Get unique platforms
    platforms = list(set(df['platform_1'].unique().tolist() + df['platform_2'].unique().tolist()))
    platforms = sorted(platforms)
    
    # Create matrix
    matrix = pd.DataFrame(0.0, index=platforms, columns=platforms)
    
    for _, row in df.iterrows():
        p1, p2 = row['platform_1'], row['platform_2']
        if pd.notna(row['price_1']) and pd.notna(row['price_2']):
            if row['price_1'] < row['price_2']:
                matrix.loc[p1, p2] += 1
            else:
                matrix.loc[p2, p1] += 1
    
    fig = px.imshow(
        matrix,
        labels=dict(x="Platform", y="Platform", color="Times Cheaper"),
        x=matrix.columns,
        y=matrix.index,
        title="Platform Price Comparison Matrix (How many times each platform is cheaper)",
        color_continuous_scale='RdYlGn',
        text_auto=True
    )
    
    fig.update_layout(height=400)
    
    return fig

def main():
    # Header
    st.title("🛒 E-commerce Price Comparison Dashboard")
    st.markdown("### Compare prices across Zepto, JioMart, and Amazon Fresh")
    
    # Load data
    data = load_data()
    
    if data is None:
        st.stop()
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Platform filter
    available_platforms = sorted(data['processed']['platform'].unique().tolist())
    selected_platforms = st.sidebar.multiselect(
        "Select Platforms",
        options=available_platforms,
        default=available_platforms
    )
    
    # Brand filter
    available_brands = sorted(data['processed']['brand_clean'].unique().tolist())
    selected_brands = st.sidebar.multiselect(
        "Select Brands",
        options=available_brands,
        default=[]
    )
    
    # Price range filter
    min_price = float(data['processed']['price_rupees'].min())
    max_price = float(data['processed']['price_rupees'].max())
    price_range = st.sidebar.slider(
        "Price Range (₹)",
        min_value=min_price,
        max_value=max_price,
        value=(min_price, max_price)
    )
    
    # Apply filters
    filtered_data = data['processed'].copy()
    
    if selected_platforms and len(selected_platforms) > 0:
        filtered_data = filtered_data[filtered_data['platform'].isin(selected_platforms)]
    
    if selected_brands and len(selected_brands) > 0:
        filtered_data = filtered_data[filtered_data['brand_clean'].isin(selected_brands)]
    
    filtered_data = filtered_data[
        (filtered_data['price_rupees'] >= price_range[0]) & 
        (filtered_data['price_rupees'] <= price_range[1])
    ]
    
    # Filter comparison data
    filtered_comparison = data['comparison'].copy()
    if selected_platforms and len(selected_platforms) > 0:
        filtered_comparison = filtered_comparison[
            (filtered_comparison['platform_1'].isin(selected_platforms)) &
            (filtered_comparison['platform_2'].isin(selected_platforms))
        ]
    
    # Key Metrics Row
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        delta_text = None
        if len(selected_brands) > 0:
            delta_val = len(filtered_data) - len(data['processed'])
            delta_text = f"{delta_val:+,} filtered"
        
        st.metric(
            label="📦 Total Products",
            value=f"{len(filtered_data):,}",
            delta=delta_text
        )
    
    with col2:
        st.metric(
            label="🔗 Matched Products",
            value=f"{len(filtered_comparison):,}"
        )
    
    with col3:
        avg_savings = filtered_comparison['savings'].mean() if len(filtered_comparison) > 0 else 0
        st.metric(
            label="💰 Avg Savings Potential",
            value=f"₹{avg_savings:.2f}"
        )
    
    with col4:
        total_savings = filtered_comparison['savings'].sum() if len(filtered_comparison) > 0 else 0
        st.metric(
            label="💸 Total Savings Possible",
            value=f"₹{total_savings:,.2f}"
        )
    
    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview", 
        "🏆 Best Deals", 
        "📈 Price Analysis", 
        "🔍 Product Search",
        "📋 Platform Summary"
    ])
    
    with tab1:
        st.header("Market Overview")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.plotly_chart(
                create_price_distribution(filtered_data, selected_platforms),
                use_container_width=True
            )
        
        with col2:
            st.plotly_chart(
                create_unit_price_comparison(filtered_data, selected_platforms),
                use_container_width=True
            )
        
        st.plotly_chart(
            create_brand_analysis(filtered_data),
            use_container_width=True
        )
        
        if len(filtered_comparison) > 0:
            st.plotly_chart(
                create_platform_comparison_matrix(filtered_comparison),
                use_container_width=True
            )
    
    with tab2:
        st.header("🏆 Best Deals & Savings")
        
        if len(filtered_comparison) > 0:
            st.plotly_chart(
                create_savings_chart(filtered_comparison),
                use_container_width=True
            )
            
            st.subheader("Top 10 Deals")
            
            top_deals = filtered_comparison.nlargest(min(10, len(filtered_comparison)), 'savings')[
                ['product_name', 'brand', 'weight_grams', 
                 'platform_1', 'price_1', 'platform_2', 'price_2', 
                 'cheaper_platform', 'best_price', 'savings']
            ].copy()
            
            # Format columns safely
            top_deals['weight_grams'] = top_deals['weight_grams'].apply(
                lambda x: f"{x:.0f}g" if pd.notna(x) else "N/A"
            )
            top_deals['price_1'] = top_deals['price_1'].apply(lambda x: f"₹{x:.2f}")
            top_deals['price_2'] = top_deals['price_2'].apply(lambda x: f"₹{x:.2f}")
            top_deals['best_price'] = top_deals['best_price'].apply(lambda x: f"₹{x:.2f}")
            top_deals['savings'] = top_deals['savings'].apply(lambda x: f"₹{x:.2f}")
            
            top_deals.columns = ['Product', 'Brand', 'Weight', 'Platform 1', 'Price 1', 
                                'Platform 2', 'Price 2', 'Cheaper On', 'Best Price', 'Save']
            
            st.dataframe(
                top_deals,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No matched products found with current filters.")
    
    with tab3:
        st.header("📈 Detailed Price Analysis")
        
        # Price distribution by brand
        if len(selected_brands) > 0:
            brand_filtered = filtered_data[filtered_data['brand_clean'].isin(selected_brands)]
        else:
            brand_filtered = filtered_data
        
        # Remove rows with NaN values for scatter plot
        scatter_data = brand_filtered[
            brand_filtered['weight_grams'].notna() & 
            brand_filtered['price_per_100g'].notna()
        ].copy()
        
        if len(scatter_data) > 0:
            fig = px.scatter(
                scatter_data,
                x='weight_grams',
                y='price_rupees',
                color='platform',
                size='price_per_100g',
                hover_data=['product_name', 'brand_clean'],
                title='Price vs Weight Analysis',
                labels={'weight_grams': 'Weight (g)', 'price_rupees': 'Price (₹)'}
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for scatter plot with current filters.")
        
        # Price trends by category
        col1, col2 = st.columns(2)
        
        with col1:
            if len(filtered_data) > 0:
                platform_avg = filtered_data.groupby('platform')['price_rupees'].agg(
                    ['mean', 'median', 'std']
                ).reset_index()
                platform_avg.columns = ['Platform', 'Mean Price', 'Median Price', 'Std Dev']
                
                st.subheader("Platform Statistics")
                st.dataframe(
                    platform_avg.style.format({
                        'Mean Price': '₹{:.2f}',
                        'Median Price': '₹{:.2f}',
                        'Std Dev': '₹{:.2f}'
                    }),
                    use_container_width=True,
                    hide_index=True
                )
        
        with col2:
            if len(filtered_comparison) > 0:
                platform_wins = filtered_comparison['cheaper_platform'].value_counts().reset_index()
                platform_wins.columns = ['Platform', 'Times Cheapest']
                
                fig = px.pie(
                    platform_wins,
                    values='Times Cheapest',
                    names='Platform',
                    title='Which Platform Offers Best Prices Most Often?'
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.header("🔍 Product Search")
        
        search_term = st.text_input("Search for a product:", "")
        
        if search_term:
            search_results = filtered_data[
                filtered_data['product_name'].str.contains(search_term, case=False, na=False) |
                filtered_data['brand_clean'].str.contains(search_term, case=False, na=False)
            ].copy()
            
            if len(search_results) > 0:
                st.success(f"Found {len(search_results)} products")
                
                # Display results
                display_cols = ['platform', 'product_name', 'brand_clean', 'weight_grams', 
                               'price_rupees', 'price_per_100g']
                
                search_results_display = search_results[display_cols].copy()
                search_results_display['weight_grams'] = search_results_display['weight_grams'].apply(
                    lambda x: f"{x:.0f}g" if pd.notna(x) else "N/A"
                )
                search_results_display['price_rupees'] = search_results_display['price_rupees'].apply(
                    lambda x: f"₹{x:.2f}"
                )
                search_results_display['price_per_100g'] = search_results_display['price_per_100g'].apply(
                    lambda x: f"₹{x:.2f}" if pd.notna(x) else "N/A"
                )
                
                search_results_display.columns = ['Platform', 'Product', 'Brand', 'Weight', 
                                                 'Price', 'Price/100g']
                
                st.dataframe(
                    search_results_display,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Show price comparison for this product
                if len(filtered_comparison) > 0:
                    product_comparisons = filtered_comparison[
                        filtered_comparison['product_name'].str.contains(search_term, case=False, na=False)
                    ]
                    
                    if len(product_comparisons) > 0:
                        st.subheader("Price Comparison")
                        
                        for _, row in product_comparisons.head(5).iterrows():
                            col1, col2, col3 = st.columns([2, 1, 1])
                            
                            with col1:
                                st.write(f"**{row['product_name']}**")
                                weight_str = f"{row['weight_grams']:.0f}g" if pd.notna(row['weight_grams']) else "N/A"
                                st.caption(f"{row['brand']} • {weight_str}")
                            
                            with col2:
                                st.metric(
                                    label=row['platform_1'],
                                    value=f"₹{row['price_1']:.2f}"
                                )
                            
                            with col3:
                                st.metric(
                                    label=row['platform_2'],
                                    value=f"₹{row['price_2']:.2f}",
                                    delta=f"₹{row['price_difference']:.2f}"
                                )
                            
                            st.markdown("---")
            else:
                st.warning("No products found matching your search.")
    
    with tab5:
        st.header("📋 Platform Summary")
        
        summary_data = data['platform_summary'].copy()
        
        st.dataframe(
            summary_data.style.format({
                'total_products': '{:,.0f}',
                'avg_price': '₹{:.2f}',
                'median_price': '₹{:.2f}',
                'min_price': '₹{:.2f}',
                'max_price': '₹{:.2f}',
                'avg_price_per_100g': '₹{:.2f}',
                'median_price_per_100g': '₹{:.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
        
        st.subheader("Brand Summary")
        
        brand_data = data['brand_summary'].head(20).copy()
        
        st.dataframe(
            brand_data.style.format({
                'product_count': '{:,.0f}',
                'platforms_available': '{:,.0f}',
                'avg_price': '₹{:.2f}',
                'avg_price_per_100g': '₹{:.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #666;'>
            <p>💡 Tip: Use the filters in the sidebar to narrow down your search and find the best deals!</p>
            <p>Data updates: Run the preprocessing pipeline to refresh data</p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()