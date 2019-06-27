# -*- coding: utf-8 -*-
# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.4'
#       jupytext_version: 1.1.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# +
from gssutils import *

scraper = Scraper('https://digital.nhs.uk/data-and-information/publications/statistical/statistics-on-alcohol')
scraper
# -

scraper.select_dataset(latest=True)
scraper

dist = scraper.distribution(mediaType='application/zip')
dist

# +
from zipfile import ZipFile
from io import BytesIO
from chardet import detect
from IPython.core.display import HTML

tables = {}

with dist.open() as csv_pack:
    # need to read the file as ZipFile does seek()
    csv_pack_data = BytesIO(csv_pack.read())
    with ZipFile(csv_pack_data) as zf:
        for csv_file in zf.namelist():
            if csv_file.endswith('.csv'):
                with zf.open(csv_file) as csv_stream:
                    # also need to read the data as there are some different character
                    # encodings we need to guess
                    raw_csv_data = csv_stream.read()
                    detected = detect(raw_csv_data)
                    table = pd.read_csv(BytesIO(raw_csv_data), encoding=detected['encoding'])
                    table_name = csv_file[:-4]
                    display(HTML(f'<h2>{table_name}</h2>'))
                    display(table)
                    tables[table_name] = table
# -

import re
title_years = re.compile(r'(.*?)([0-9]+(_to_[0-9]+)?)')
titles = {}
for (filename, table) in tables.items():
    match = title_years.match(filename)
    if match:
        titles[filename] = match.group(1).replace('_', ' ').strip()
        years = match.group(2)
        display(HTML(f'<h2>{titles[filename]}</h2>'))
        for col in table:
            if col not in ['Year', 'Value']:
                table[col] = table[col].astype('category')
                display(HTML(f'<h3>{col}</h3>'))
                display(table[col].cat.categories)
                                           

# +
from pathlib import Path
out = Path('out')
out.mkdir(exist_ok=True)

for (filename, table) in tables.items():
    title = titles[filename]
    if title.lower() == 'alcohol affordability':
        table['Period'] = table['Year'].map(lambda x: f'year/{x}')
        table = table.drop(columns='Year')
        table['Revision'] = table['Metric'].map(
            lambda x: 'revised' if x.endswith(' (revised)') else 'original-value')
        table.rename(columns={'Metric': 'Alcohol affordability'}, inplace=True)
        table['Alcohol affordability'].cat.rename_categories(
            lambda x: pathify(x[:-len(" (18+) (revised)")] if x.endswith(" (18+) (revised)") else
                      x[:-len(" (revised)")] if x.endswith(" (revised)") else x),
            inplace=True)
        table['Measure Type'] = 'Ratio'
        table['Unit'] = 'index'
    elif title.lower() == 'alcohol specific deaths':
        table['Period'] = table['Year'].map(lambda x: f'year/{x}')
        table['Underlying Cause of Death'] = table['ICD10_Code'].map(
            lambda x: pathify(x) if x != 'Total' else 'all-alcohol-related-deaths')
        table = table.drop(columns=['Year', 'ICD10_Code', 'ICD10_Description'])
        table.rename(columns={'Metric': 'Sex'}, inplace=True)
        table['Sex'].cat.rename_categories(
            {'All persons': 'T',
             'Male': 'M', 'Female': 'F'}, inplace=True)
        table['Measure Type'] = 'Count'
        table['Unit'] = 'deaths'
    elif title.lower() == 'household expenditure alcohol':
        table['Period'] = table['Year'].map(lambda x: f'year/{x}')
        table.rename(columns={'Metric': 'Household expenditure type'}, inplace=True)
        table['Household expenditure type'].cat.rename_categories(pathify, inplace=True)
        table = table.drop(columns=['Year', 'Unnamed: 3', 'Unnamed: 4'])
        table['Measure Type'] = 'Household expenditure'
        table['Unit'] = table['Household expenditure type'].map(
            lambda x: 'percent' if 'percentage' in x else 'gbp')
        table['Value'] = table['Value'].map(
            lambda x: x.replace(',', ''))
    elif title.lower() == 'prescription items community':
        table['Period'] = table['Year'].map(lambda x: f'year/{x}')
        table.rename(columns={
            'Metric_Primary': 'Metric',
            'Metric_Secondary': 'Prescription item'}, inplace=True)
        table['Unit'] = table['Metric'].map(
            lambda x: 'gbp' if x.endswith('(£)') else 'gbp-thousands' if x.endswith('(£ 000s)') else 'prescription-items')
        table['Metric'].cat.rename_categories({
            'Average Net Ingredient Cost per item (£)': 'average-net-ingredient-cost-per-item',
            'Net Ingredient Cost (£ 000s)': 'net-ingredient-cost',
            'Prescribed in NHS hospitals': 'prescribed-in-nhs-hospitals',
            'Prescribed in primary care': 'prescribed-in-primary-care',
            'Prescription Items - All Settings': 'all-prescription-settings'
        }, inplace=True)
        table.rename(columns={'Metric': 'Prescription'}, inplace=True)
        table['Prescription item'].cat.rename_categories(pathify, inplace=True)
        table = table.drop(columns=['Year'])
        table['Measure Type'] = table['Unit'].map(
            lambda x: 'Count' if x == 'prescription-items' else 'GBP Total')
        table['Value'] = pd.to_numeric(table['Value'], errors='coerce', downcast='integer')
        table.dropna(subset=['Value'], inplace=True)
        table['Value'] = table['Value'].astype('int')
    elif title.lower() == 'prescription items region':
        table['Period'] = table['Year'].map(lambda x: f'year/{x}')
        table.rename(columns={
            'ONS_Code': 'Geography',
            'Metric_Primary': 'Metric',
            'Metric_Secondary': 'Prescription item'
        }, inplace=True)
        table.drop(table[(table['Geography'] == 'XXXXXXXX') |
                         (table['Geography'].isna())].index, inplace=True)
        table['Metric'].cat.rename_categories(pathify, inplace=True)
        table.rename(columns={'Metric': 'Prescription'}, inplace=True)
        table['Prescription item'].cat.rename_categories(pathify, inplace=True)
        table = table.drop(columns=['Year', 'Org_Code', 'Org_Name'])
        table['Measure Type'] = 'Count'
        table['Unit'] = 'prescription-items'
        table['Value'] = pd.to_numeric(table['Value'], errors='coerce', downcast='integer')
        table.dropna(subset=['Value'], inplace=True)
        table['Value'] = table['Value'].astype('int')
    else:        
        continue
    display(HTML(f'<h2>{title}</h2>'))
    display(table)
    table.to_csv(out / f'{pathify(title)}.csv', index = False)
    schema = CSVWMetadata('https://ons-opendata.github.io/ref_alcohol/')
    schema.create(out / f'{pathify(title)}.csv', out / f'{pathify(title)}.csv-schema.json')
# -

for filename in tables.keys():
    basename = pathify(titles[filename])
    scraper.set_dataset_id(f'gss_data/health/nhs-statistics-on-alcohol-england/{basename}')
    scraper.dataset.title = titles[filename]
    scraper.dataset.comment = {
        'prescription items community': 'Number of prescription items, net ingredient cost and average net ingredient cost per item of drugs prescribed, for the treatment of alcohol dependence, dispensed in the community, England.',
        'prescription items region': 'Number of prescription items and prescription items per 100,000 population, for the treatment of alcohol dependence, prescribed in primary care and dispensed in the community, by Commissioning Region and Area Team, England.',
        'alcohol specific deaths': 'Alcohol-related deaths by gender, England.',
        'alcohol affordability': 'Indices of alcohol price, retail prices, alcohol price index relative to retail prices index (all items), real household disposable income, real disposable income per adult and affordability of alcohol, United Kingdom.',
        'household expenditure alcohol': 'Household expenditure on off trade alcohol at current prices, United Kingdom.'
    }.get(titles[filename].lower())
    scraper.dataset.family = 'health'
    scraper.dataset.theme = THEME['health-social-care']
    with open(out / f'{basename}.csv-metadata.trig', 'wb') as metadata:
        metadata.write(scraper.generate_trig())


