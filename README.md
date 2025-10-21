# GeoFarm Data Engineering Project 🌾

A Python + AWS + Geospatial pipeline that automates NDVI analysis using Sentinel-2 data.
This project was built as part of a Data Engineer (Python + AWS + Geospatial Data) learning workflow.

## Features
- Downloads and preprocesses satellite imagery
- Calculates NDVI from NIR/Red bands using Rasterio
- Computes zonal statistics over field polygons
- Loads data into PostGIS
- Uploads processed layers to AWS S3
- Optional REST API (FastAPI) for accessing results

## Tech Stack
**Python | AWS S3 | Rasterio | GeoPandas | PostGIS | SQLAlchemy | FastAPI**

## How to Run
1. Clone this repo  
   ```bash
   git clone https://github.com/<your-username>/geofarm-pipeline.git
   cd geofarm-pipeline

2. Create environment

mamba env create -f environment.yml


3. Run any module

python src/03_ndvi.py --aoi "19.80,50.00,20.20,50.30"