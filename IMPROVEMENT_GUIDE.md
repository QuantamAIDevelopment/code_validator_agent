# Code Quality Improvement Guide

## Current Score: 43.2/100 (LOW)
## Target Score: 70+ (Production Ready)

---

## 🎯 Priority 1: Fix Long Functions (Impact: +10 points)

### Files to Refactor:
1. **ward_geojson_service.py**
   - `get_ward_data()` - 93 lines → Split into 3 functions
   - `get_ward_geojson()` - 64 lines → Split into 2 functions
   - `upload_ward_geojson()` - 56 lines → Split into 2 functions

2. **vrp_solver.py**
   - `_calculate_distance_matrix()` - 66 lines → Extract helper functions
   - `solve_vrp()` - 60 lines → Split into smaller steps

3. **vehicle_service.py**
   - `_standardize_vehicle_data()` - 51 lines → Split validation logic

### How to Fix:
```python
# BEFORE (93 lines)
def get_ward_data(ward_id):
    # ... 93 lines of code ...
    pass

# AFTER (Split into smaller functions)
def get_ward_data(ward_id):
    ward = _fetch_ward(ward_id)
    geojson = _process_geojson(ward)
    metadata = _extract_metadata(ward)
    return _build_response(ward, geojson, metadata)

def _fetch_ward(ward_id):
    # 15 lines
    pass

def _process_geojson(ward):
    # 20 lines
    pass

def _extract_metadata(ward):
    # 15 lines
    pass

def _build_response(ward, geojson, metadata):
    # 10 lines
    pass
```

---

## 🎯 Priority 2: Reduce Code Duplication (Impact: +8 points)

### File: ward_geojson_endpoints.py (30% duplication)

**Problem:** Same code repeated in multiple endpoints

**Solution:** Extract common logic into helper functions

```python
# BEFORE (Duplicated)
@app.post("/upload")
def upload():
    # Validation logic (20 lines)
    # Processing logic (15 lines)
    # Response logic (10 lines)
    pass

@app.put("/update")
def update():
    # Same validation logic (20 lines)
    # Same processing logic (15 lines)
    # Same response logic (10 lines)
    pass

# AFTER (DRY - Don't Repeat Yourself)
def _validate_request(data):
    # 20 lines
    pass

def _process_geojson(data):
    # 15 lines
    pass

def _build_response(result):
    # 10 lines
    pass

@app.post("/upload")
def upload():
    _validate_request(request.data)
    result = _process_geojson(request.data)
    return _build_response(result)

@app.put("/update")
def update():
    _validate_request(request.data)
    result = _process_geojson(request.data)
    return _build_response(result)
```

---

## 🎯 Priority 3: Add Error Handling (Impact: +6 points)

### Files Missing Error Handling:
- blackboard.py
- capacity_optimizer.py
- directions_generator.py
- export_to_geojson.py
- folium_map.py
- hierarchical_clustering.py
- trip_assignment.py
- ward_cluster_manager.py

**Add try-except blocks:**

```python
# BEFORE
def process_data(data):
    result = expensive_operation(data)
    return result

# AFTER
import logging
logger = logging.getLogger(__name__)

def process_data(data):
    try:
        result = expensive_operation(data)
        return result
    except ValueError as e:
        logger.error(f"Invalid data: {e}")
        raise
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise
```

---

## 🎯 Priority 4: Optimize Nested Loops (Impact: +5 points)

### Files with O(n²) complexity:
- compute_routes.py
- get_osrm_directions.py
- osrm_routing.py
- trip_assignment.py
- vrp_solver.py

**Use dictionaries/sets for O(1) lookups:**

```python
# BEFORE (O(n²))
for item in list1:
    for other in list2:
        if item.id == other.id:
            process(item, other)

# AFTER (O(n))
lookup = {other.id: other for other in list2}
for item in list1:
    if item.id in lookup:
        process(item, lookup[item.id])
```

---

## 🎯 Priority 5: Increase Test Coverage (Impact: +10 points)

**Current:** 5.9% coverage  
**Target:** 60%+ coverage

### Create tests for:
1. **Core business logic** (vrp_solver.py, ward_geojson_service.py)
2. **API endpoints** (all *_api.py files)
3. **Data processing** (compute_routes.py, trip_assignment.py)

```python
# tests/test_vrp_solver.py
import pytest
from app.core.vrp_solver import solve_vrp

def test_solve_vrp_basic():
    vehicles = [{"id": 1, "capacity": 100}]
    locations = [{"lat": 0, "lng": 0}]
    result = solve_vrp(vehicles, locations)
    assert result is not None
    assert "routes" in result

def test_solve_vrp_empty_vehicles():
    with pytest.raises(ValueError):
        solve_vrp([], [])
```

---

## 🎯 Priority 6: Add Comments & Documentation (Impact: +4 points)

### Files with <2% comments:
- vehicles_api.py
- blackboard.py
- blackboard_entry.py
- compute_routes.py
- get_osrm_directions.py
- road_snapper.py
- snap_buildings.py
- ward_geojson_service.py

**Add docstrings:**

```python
def calculate_distance(lat1, lng1, lat2, lng2):
    """
    Calculate Haversine distance between two coordinates.
    
    Args:
        lat1 (float): Latitude of first point
        lng1 (float): Longitude of first point
        lat2 (float): Latitude of second point
        lng2 (float): Longitude of second point
    
    Returns:
        float: Distance in kilometers
    
    Example:
        >>> calculate_distance(0, 0, 1, 1)
        157.2
    """
    # Implementation
    pass
```

---

## 📊 Expected Score After Fixes:

| Priority | Impact | Cumulative Score |
|----------|--------|------------------|
| Start | - | 43.2 |
| Fix long functions | +10 | 53.2 |
| Reduce duplication | +8 | 61.2 |
| Add error handling | +6 | 67.2 |
| Optimize loops | +5 | 72.2 ✅ |
| Increase tests | +10 | 82.2 ✅ |
| Add comments | +4 | 86.2 ✅ |

**Target: 70+ (Production Ready)** achieved after Priority 4!

---

## 🚀 Quick Wins (Do These First):

1. **Add logging to config.py** (5 minutes)
2. **Add error handling to 8 files** (2 hours)
3. **Add docstrings to all functions** (3 hours)
4. **Split 3 longest functions** (4 hours)

**Total time: ~1 day of work → Score jumps to 65-70!**

---

## 🛠️ Tools to Help:

```bash
# Find long functions
pylint --disable=all --enable=too-many-lines yourfile.py

# Find duplicates
pylint --disable=all --enable=duplicate-code .

# Check test coverage
pytest --cov=app --cov-report=html

# Auto-format code
black .
isort .
```

---

## ✅ Checklist:

- [ ] Split functions >50 lines
- [ ] Remove code duplication >20%
- [ ] Add try-except to all functions
- [ ] Optimize nested loops
- [ ] Write tests (60%+ coverage)
- [ ] Add docstrings to all functions
- [ ] Add logging to all modules
- [ ] Run pylint and fix warnings

**After completing checklist: Re-run audit to verify 70+ score!**
