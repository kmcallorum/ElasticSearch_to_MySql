# 🚀 QUICK SETUP - 5 MINUTES TO AUTOMATED COVERAGE

## 📁 FILE PLACEMENT:

```
your-repo/
├── .github/
│   ├── workflows/
│   │   └── tests.yml                    ← Download: tests.yml
│   └── scripts/
│       └── update_readme_coverage.py    ← Download: update_readme_coverage.py
├── README.md                             ← Add badges from README_WITH_COVERAGE.md
└── requirements.txt                      ← Add lines from requirements_additions.txt
```

## ⚡ QUICK STEPS:

### 1. Create Directories
```bash
mkdir -p .github/workflows
mkdir -p .github/scripts
```

### 2. Add Files
```bash
# Download and place:
# - tests.yml → .github/workflows/tests.yml
# - update_readme_coverage.py → .github/scripts/update_readme_coverage.py

chmod +x .github/scripts/update_readme_coverage.py
```

### 3. Update requirements.txt
```bash
# Add these lines:
pytest>=7.4.0
pytest-cov>=4.1.0
beautifulsoup4>=4.12.0
```

### 4. Set Up Codecov
1. Go to https://codecov.io/
2. Sign in with GitHub
3. Add your repository
4. Copy upload token
5. Add to GitHub: Settings → Secrets → Actions → New secret
   - Name: `CODECOV_TOKEN`
   - Value: Your token

### 5. Update README.md
Add at the top (replace YOUR_USERNAME and REPO):
```markdown
[![Tests](https://github.com/YOUR_USERNAME/REPO/workflows/Tests%20and%20Coverage/badge.svg)](https://github.com/YOUR_USERNAME/REPO/actions)
[![codecov](https://codecov.io/gh/YOUR_USERNAME/REPO/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/REPO)
```

### 6. Test Locally
```bash
# Generate coverage
pytest --cov=. --cov-report=html

# Run update script
python .github/scripts/update_readme_coverage.py

# Check README - should have coverage table at end
tail -50 README.md
```

### 7. Commit & Push
```bash
git add .github/ README.md requirements.txt
git commit -m "Add automated coverage reporting"
git push
```

### 8. Verify
- Go to GitHub → Actions tab
- Watch workflow run
- After completion:
  - ✅ Check coverage badge updates
  - ✅ Check README has coverage table
  - ✅ Check Codecov dashboard

## 🎉 DONE!

Every commit now:
- ✅ Runs 293 tests
- ✅ Generates coverage
- ✅ Updates badges
- ✅ Updates README with coverage table
- ✅ Uploads to Codecov

## 📊 WHAT YOU'LL SEE:

In README.md:
```
[![Tests](badge)]] [![codecov](badge)]

Your content here...

---

## 📊 Test Coverage

**Overall Coverage: 100%**

| File | Statements | Missing | Coverage |
|------|------------|---------|----------|
| pipeline.py | 155 | 0 | 100% |
...
```

On Codecov:
- Beautiful coverage graphs
- File-by-file breakdown
- Coverage trends over time
- Pull request coverage checks

## 🔧 TROUBLESHOOTING:

**Workflow not running?**
- Check `.github/workflows/tests.yml` exists
- Verify YAML syntax (no tabs!)
- Check branch name (main vs master)

**Coverage not updating?**
- Verify `CODECOV_TOKEN` is set
- Check workflow completed successfully
- Look for bot commit with "[skip ci]"

**README not updating?**
- Check `beautifulsoup4` in requirements.txt
- Verify script has correct path
- Check GitHub Actions logs for errors

## 💡 ALTERNATIVE: MANUAL UPDATE

Don't want auto-updates? Just run manually:

```bash
# After any changes
pytest --cov=. --cov-report=html
python .github/scripts/update_readme_coverage.py
git add README.md
git commit -m "Update coverage"
git push
```

## 📚 FILES PROVIDED:

1. ✅ `tests.yml` - GitHub Actions workflow
2. ✅ `update_readme_coverage.py` - README updater script
3. ✅ `README_WITH_COVERAGE.md` - Example README with badges
4. ✅ `COVERAGE_AUTOMATION_SETUP.md` - Detailed setup guide
5. ✅ `requirements_additions.txt` - Packages to add

---

**Total Setup Time: 5 minutes**
**Result: Professional automated coverage reporting!** 🎯
