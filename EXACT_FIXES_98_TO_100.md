# 🎯 EXACT FIXES: 98% → 100%

## 📝 Edit test_impl.py - THREE Changes:

### Change #1: Line 71
**Find this (around line 71):**
```python
        try:
            json.loads(text)
            return True
        except:
            return False
```

**Replace with:**
```python
        try:
            json.loads(text)
            return True
        except (json.JSONDecodeError, ValueError, TypeError):
            return False
```

---

### Change #2: Line 133  
**Find this (around line 133):**
```python
        try:
            json.loads(text)
            return True
        except:
            return False
```

**Replace with:**
```python
        try:
            json.loads(text)
            return True
        except (json.JSONDecodeError, ValueError, TypeError):
            return False
```

---

### Change #3: Line 174
**Find this (around line 174):**
```python
            try:
                content_obj = json.loads(content)
            except:
                content_obj = {"raw": content}
```

**Replace with:**
```python
            try:
                content_obj = json.loads(content)
            except (json.JSONDecodeError, ValueError, TypeError):
                content_obj = {"raw": content}
```

---

## 💾 Save and Test:

```bash
# After making the 3 changes, run:
pytest test_impl.py -v
# Should still pass

# Then run coverage:
pytest --cov=. --cov-report=html
```

---

## 📊 Expected Results:

**After fixing test_impl.py:**
- test_impl.py: 91% → 100% ✅
- Coverage: 98% → 99%

**After test_surgical_100.py triggers handlers:**
- error_analyzer.py: 76% → 100% ✅
- Coverage: 99% → 100% 🏆

---

## 🔧 Use This sed Command (Optional):

If you want to fix all 3 automatically:

```bash
# Backup first
cp test_impl.py test_impl.py.backup

# Fix all 3 bare except clauses
sed -i '' 's/except:/except (json.JSONDecodeError, ValueError, TypeError):/g' test_impl.py

# Test it
pytest test_impl.py -v
```

(Remove the `''` after `-i` on Linux)

---

## ✅ Quick Verification:

After editing, check your fixes:
```bash
grep -n "except:" test_impl.py
# Should show NO results (all fixed!)

grep -n "except (json" test_impl.py  
# Should show 3 results (lines 71, 133, 174)
```

---

**Make those 3 changes, then run coverage again!** 🚀
