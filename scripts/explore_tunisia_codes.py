"""
Explore Tunisia ADM2 codes in GAUL dataset.
"""
import os

try:
    import ee  # type: ignore
except Exception as e:
    raise RuntimeError("earthengine-api not installed") from e


def init_ee():
    project = os.getenv("EE_PROJECT", "capstone-491313")
    try:
        ee.Initialize(project=project)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=project)


init_ee()

# Load Tunisia from GAUL
fc = (
    ee.FeatureCollection("FAO/GAUL/2015/level2")
    .filter(ee.Filter.eq("ADM0_NAME", "Tunisia"))
    .sort("ADM2_CODE")
)

total = int(fc.size().getInfo())
print(f"Total Tunisia ADM2 divisions in GAUL: {total}\n")

# Get first 10 to inspect
fc_list = fc.limit(10).toList(10)

for i in range(10):
    feature = ee.Feature(fc_list.get(i))
    adm1_name = feature.get("ADM1_NAME").getInfo()
    adm2_name = feature.get("ADM2_NAME").getInfo()
    adm2_code = feature.get("ADM2_CODE").getInfo()
    print(f"{i+1}. ADM1: {adm1_name:30} | ADM2: {adm2_name:30} | Code: {adm2_code}")
