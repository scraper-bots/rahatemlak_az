#!/usr/bin/env python3
"""
Real Estate Market Analysis - Chart Generation
Generates business-focused visualizations for market insights
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import re
import warnings
warnings.filterwarnings('ignore')

# Set style for professional charts
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.titleweight'] = 'bold'

# Create charts directory
CHARTS_DIR = Path('charts')
CHARTS_DIR.mkdir(exist_ok=True)

# Load data
print("Loading data...")
df = pd.read_csv('properties.csv')
print(f"✓ Loaded {len(df):,} properties\n")


def clean_price(price_str):
    """Extract numeric price from string"""
    if pd.isna(price_str) or price_str == '':
        return None
    try:
        # Remove 'AZN' and commas, convert to float
        return float(re.sub(r'[^\d.]', '', price_str.replace(',', '')))
    except:
        return None


def clean_area(area_str):
    """Extract numeric area from string"""
    if pd.isna(area_str) or area_str == '':
        return None
    try:
        # Extract first number (square meters)
        match = re.search(r'(\d+)', area_str)
        if match:
            return float(match.group(1))
    except:
        return None


def extract_rooms(rooms_str):
    """Extract number of rooms"""
    if pd.isna(rooms_str) or rooms_str == '':
        return None
    try:
        match = re.search(r'(\d+)', rooms_str)
        if match:
            return int(match.group(1))
    except:
        return None


# Data preprocessing
print("Preprocessing data...")
df['price_numeric'] = df['price'].apply(clean_price)
df['area_numeric'] = df['area'].apply(clean_area)
df['rooms_numeric'] = df['rooms'].apply(extract_rooms)

# Remove outliers for better visualization
df_clean = df[(df['price_numeric'].notna()) &
              (df['price_numeric'] > 1000) &
              (df['price_numeric'] < 1000000)].copy()

print(f"✓ Cleaned dataset: {len(df_clean):,} properties\n")


# ============================================================================
# CHART 1: Market Inventory by Property Type
# ============================================================================
print("Generating Chart 1: Market Inventory by Property Type...")

property_type_counts = df_clean['property_type'].value_counts().head(10)

fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.barh(range(len(property_type_counts)), property_type_counts.values,
               color='steelblue', edgecolor='black', linewidth=0.5)

# Add value labels
for i, (idx, value) in enumerate(property_type_counts.items()):
    ax.text(value + max(property_type_counts.values)*0.01, i, f'{value:,}',
            va='center', fontweight='bold')

ax.set_yticks(range(len(property_type_counts)))
ax.set_yticklabels(property_type_counts.index)
ax.set_xlabel('Number of Properties', fontweight='bold')
ax.set_title('Market Inventory by Property Type\nTotal Available Listings',
             pad=20)
ax.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.savefig(CHARTS_DIR / '01_inventory_by_type.png', dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ Saved: 01_inventory_by_type.png")


# ============================================================================
# CHART 2: Average Price by Property Type
# ============================================================================
print("Generating Chart 2: Average Price by Property Type...")

avg_price_by_type = df_clean.groupby('property_type')['price_numeric'].mean().sort_values(ascending=False).head(10)

fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.barh(range(len(avg_price_by_type)), avg_price_by_type.values / 1000,
               color='coral', edgecolor='black', linewidth=0.5)

for i, (idx, value) in enumerate(avg_price_by_type.items()):
    ax.text(value/1000 + max(avg_price_by_type.values)/1000*0.01, i,
            f'{value/1000:.0f}K', va='center', fontweight='bold')

ax.set_yticks(range(len(avg_price_by_type)))
ax.set_yticklabels(avg_price_by_type.index)
ax.set_xlabel('Average Price (Thousands AZN)', fontweight='bold')
ax.set_title('Average Property Prices by Type\nMarket Positioning', pad=20)
ax.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.savefig(CHARTS_DIR / '02_avg_price_by_type.png', dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ Saved: 02_avg_price_by_type.png")


# ============================================================================
# CHART 3: Market Share by District
# ============================================================================
print("Generating Chart 3: Market Share by District...")

district_counts = df_clean['district'].value_counts().head(10)

fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.bar(range(len(district_counts)), district_counts.values,
              color='mediumseagreen', edgecolor='black', linewidth=0.5)

for i, (idx, value) in enumerate(district_counts.items()):
    percentage = (value / len(df_clean)) * 100
    ax.text(i, value + max(district_counts.values)*0.01,
            f'{value:,}\n({percentage:.1f}%)', ha='center', fontweight='bold')

ax.set_xticks(range(len(district_counts)))
ax.set_xticklabels(district_counts.index, rotation=45, ha='right')
ax.set_ylabel('Number of Properties', fontweight='bold')
ax.set_title('Geographic Distribution of Available Properties\nTop 10 Districts by Inventory',
             pad=20)
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(CHARTS_DIR / '03_market_share_by_district.png', dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ Saved: 03_market_share_by_district.png")


# ============================================================================
# CHART 4: Average Price by District
# ============================================================================
print("Generating Chart 4: Average Price by District...")

avg_price_by_district = df_clean.groupby('district')['price_numeric'].mean().sort_values(ascending=False).head(10)

fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.bar(range(len(avg_price_by_district)), avg_price_by_district.values / 1000,
              color='indianred', edgecolor='black', linewidth=0.5)

for i, (idx, value) in enumerate(avg_price_by_district.items()):
    ax.text(i, value/1000 + max(avg_price_by_district.values)/1000*0.01,
            f'{value/1000:.0f}K', ha='center', fontweight='bold')

ax.set_xticks(range(len(avg_price_by_district)))
ax.set_xticklabels(avg_price_by_district.index, rotation=45, ha='right')
ax.set_ylabel('Average Price (Thousands AZN)', fontweight='bold')
ax.set_title('Premium vs. Affordable Districts\nAverage Property Prices by Location',
             pad=20)
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(CHARTS_DIR / '04_avg_price_by_district.png', dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ Saved: 04_avg_price_by_district.png")


# ============================================================================
# CHART 5: Price Distribution (Market Segments)
# ============================================================================
print("Generating Chart 5: Price Distribution by Market Segment...")

# Define price segments
bins = [0, 50000, 100000, 150000, 200000, 300000, float('inf')]
labels = ['<50K\nEntry', '50-100K\nAffordable', '100-150K\nMid-Range',
          '150-200K\nPremium', '200-300K\nLuxury', '>300K\nUltra-Luxury']

df_clean['price_segment'] = pd.cut(df_clean['price_numeric'], bins=bins, labels=labels)
segment_counts = df_clean['price_segment'].value_counts().sort_index()

fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.bar(range(len(segment_counts)), segment_counts.values,
              color=['#90EE90', '#FFD700', '#FFA500', '#FF6347', '#DC143C', '#8B0000'],
              edgecolor='black', linewidth=0.5)

for i, (idx, value) in enumerate(segment_counts.items()):
    percentage = (value / len(df_clean)) * 100
    ax.text(i, value + max(segment_counts.values)*0.01,
            f'{value:,}\n({percentage:.1f}%)', ha='center', fontweight='bold')

ax.set_xticks(range(len(segment_counts)))
ax.set_xticklabels(segment_counts.index, rotation=0)
ax.set_ylabel('Number of Properties', fontweight='bold')
ax.set_title('Market Segmentation by Price Range\nDistribution Across Price Tiers',
             pad=20)
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(CHARTS_DIR / '05_price_distribution_segments.png', dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ Saved: 05_price_distribution_segments.png")


# ============================================================================
# CHART 6: Inventory by Number of Rooms
# ============================================================================
print("Generating Chart 6: Inventory by Room Count...")

rooms_counts = df_clean[df_clean['rooms_numeric'].notna()]['rooms_numeric'].value_counts().sort_index()
rooms_counts = rooms_counts[rooms_counts.index <= 6]  # Focus on common room counts

fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.bar(rooms_counts.index, rooms_counts.values,
              color='slateblue', edgecolor='black', linewidth=0.5, width=0.6)

for i, value in zip(rooms_counts.index, rooms_counts.values):
    percentage = (value / len(df_clean)) * 100
    ax.text(i, value + max(rooms_counts.values)*0.01,
            f'{value:,}\n({percentage:.1f}%)', ha='center', fontweight='bold')

ax.set_xlabel('Number of Rooms', fontweight='bold')
ax.set_ylabel('Number of Properties', fontweight='bold')
ax.set_title('Property Supply by Room Configuration\nMarket Demand Analysis', pad=20)
ax.set_xticks(rooms_counts.index)
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(CHARTS_DIR / '06_inventory_by_rooms.png', dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ Saved: 06_inventory_by_rooms.png")


# ============================================================================
# CHART 7: Price vs. Room Count
# ============================================================================
print("Generating Chart 7: Average Price by Room Count...")

df_rooms = df_clean[(df_clean['rooms_numeric'].notna()) & (df_clean['rooms_numeric'] <= 6)]
avg_price_by_rooms = df_rooms.groupby('rooms_numeric')['price_numeric'].mean()

fig, ax = plt.subplots(figsize=(12, 6))
line = ax.plot(avg_price_by_rooms.index, avg_price_by_rooms.values / 1000,
               marker='o', linewidth=3, markersize=10, color='darkblue')
ax.fill_between(avg_price_by_rooms.index, 0, avg_price_by_rooms.values / 1000,
                alpha=0.2, color='blue')

for i, value in zip(avg_price_by_rooms.index, avg_price_by_rooms.values):
    ax.text(i, value/1000 + max(avg_price_by_rooms.values)/1000*0.02,
            f'{value/1000:.0f}K', ha='center', fontweight='bold', fontsize=11)

ax.set_xlabel('Number of Rooms', fontweight='bold')
ax.set_ylabel('Average Price (Thousands AZN)', fontweight='bold')
ax.set_title('Price Scaling by Property Size\nRoom Count vs. Market Value', pad=20)
ax.set_xticks(avg_price_by_rooms.index)
ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig(CHARTS_DIR / '07_price_vs_rooms.png', dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ Saved: 07_price_vs_rooms.png")


# ============================================================================
# CHART 8: Top Districts - Price vs. Inventory Matrix
# ============================================================================
print("Generating Chart 8: District Performance Matrix...")

top_districts = df_clean['district'].value_counts().head(10).index
district_data = df_clean[df_clean['district'].isin(top_districts)].groupby('district').agg({
    'price_numeric': 'mean',
    'property_id': 'count'
}).reset_index()
district_data.columns = ['district', 'avg_price', 'count']

fig, ax1 = plt.subplots(figsize=(14, 6))

x = range(len(district_data))
ax1.bar(x, district_data['count'], color='lightblue', edgecolor='black',
        linewidth=0.5, label='Number of Properties', alpha=0.7)
ax1.set_xlabel('District', fontweight='bold')
ax1.set_ylabel('Number of Properties', fontweight='bold', color='blue')
ax1.tick_params(axis='y', labelcolor='blue')

ax2 = ax1.twinx()
ax2.plot(x, district_data['avg_price'] / 1000, color='red', marker='D',
         linewidth=3, markersize=8, label='Average Price (K AZN)')
ax2.set_ylabel('Average Price (Thousands AZN)', fontweight='bold', color='red')
ax2.tick_params(axis='y', labelcolor='red')

ax1.set_xticks(x)
ax1.set_xticklabels(district_data['district'], rotation=45, ha='right')
ax1.set_title('Supply & Demand Indicators by District\nInventory Volume vs. Price Point',
              pad=20)
ax1.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(CHARTS_DIR / '08_district_matrix.png', dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ Saved: 08_district_matrix.png")


# ============================================================================
# CHART 9: Document Availability Impact
# ============================================================================
print("Generating Chart 9: Document Status Impact on Pricing...")

df_clean['has_document'] = df_clean['document'].apply(
    lambda x: 'With Document' if pd.notna(x) and x.strip() != '' else 'No Document'
)

doc_price_comparison = df_clean.groupby('has_document')['price_numeric'].agg(['mean', 'count'])

fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.bar(range(len(doc_price_comparison)), doc_price_comparison['mean'] / 1000,
              color=['lightcoral', 'lightgreen'], edgecolor='black', linewidth=0.5)

for i, (idx, row) in enumerate(doc_price_comparison.iterrows()):
    ax.text(i, row['mean']/1000 + doc_price_comparison['mean'].max()/1000*0.02,
            f'{row["mean"]/1000:.0f}K\n({row["count"]:,} properties)',
            ha='center', fontweight='bold')

ax.set_xticks(range(len(doc_price_comparison)))
ax.set_xticklabels(doc_price_comparison.index)
ax.set_ylabel('Average Price (Thousands AZN)', fontweight='bold')
ax.set_title('Legal Documentation Impact on Market Value\nPrice Premium Analysis',
             pad=20)
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(CHARTS_DIR / '09_document_impact.png', dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ Saved: 09_document_impact.png")


# ============================================================================
# CHART 10: Top 3 Districts - Detailed Breakdown
# ============================================================================
print("Generating Chart 10: Top Districts Detailed Analysis...")

top_3_districts = df_clean['district'].value_counts().head(3).index
top_3_data = df_clean[df_clean['district'].isin(top_3_districts)]

# Group by district and property type
breakdown = top_3_data.groupby(['district', 'property_type']).size().unstack(fill_value=0)
# Keep only top 5 property types overall
top_types = df_clean['property_type'].value_counts().head(5).index
breakdown = breakdown[breakdown.columns.intersection(top_types)]

fig, ax = plt.subplots(figsize=(14, 6))
breakdown.plot(kind='bar', stacked=True, ax=ax, colormap='Set3',
               edgecolor='black', linewidth=0.5)

ax.set_xlabel('District', fontweight='bold')
ax.set_ylabel('Number of Properties', fontweight='bold')
ax.set_title('Market Composition in Top 3 Districts\nProperty Type Distribution',
             pad=20)
ax.legend(title='Property Type', bbox_to_anchor=(1.05, 1), loc='upper left')
ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(CHARTS_DIR / '10_top_districts_breakdown.png', dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ Saved: 10_top_districts_breakdown.png")


# ============================================================================
# Summary Statistics for README
# ============================================================================
print("\n" + "="*60)
print("ANALYSIS SUMMARY - Key Business Metrics")
print("="*60)

print(f"\nMarket Overview:")
print(f"  • Total Properties Available: {len(df_clean):,}")
print(f"  • Average Price: {df_clean['price_numeric'].mean()/1000:.0f}K AZN")
print(f"  • Median Price: {df_clean['price_numeric'].median()/1000:.0f}K AZN")
print(f"  • Price Range: {df_clean['price_numeric'].min()/1000:.0f}K - {df_clean['price_numeric'].max()/1000:.0f}K AZN")

print(f"\nTop 3 Property Types:")
top_types = df_clean['property_type'].value_counts().head(3)
for i, (ptype, count) in enumerate(top_types.items(), 1):
    pct = (count / len(df_clean)) * 100
    print(f"  {i}. {ptype}: {count:,} ({pct:.1f}%)")

print(f"\nTop 3 Districts by Inventory:")
top_districts_list = df_clean['district'].value_counts().head(3)
for i, (district, count) in enumerate(top_districts_list.items(), 1):
    avg_price = df_clean[df_clean['district'] == district]['price_numeric'].mean()
    print(f"  {i}. {district}: {count:,} properties (Avg: {avg_price/1000:.0f}K AZN)")

print(f"\nMost Common Room Count: {int(df_clean['rooms_numeric'].mode()[0])} rooms")

doc_availability = (df_clean['document'].notna().sum() / len(df_clean)) * 100
print(f"Properties with Documentation: {doc_availability:.1f}%")

print(f"\nPrice Segments:")
for segment, count in segment_counts.items():
    pct = (count / len(df_clean)) * 100
    print(f"  • {segment}: {count:,} ({pct:.1f}%)")

print("\n" + "="*60)
print("✓ All charts generated successfully in charts/ directory")
print("="*60 + "\n")
