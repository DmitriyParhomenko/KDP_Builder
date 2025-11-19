# Dual Repository Setup Guide

## 📦 Repository Structure

### **Private (Full Version)**
- **URL:** `git@github.com:DmitriyParhomenko/KDP_Builder_FULL.git`
- **Contains:** Everything (AI, blocks, patterns, full backend)
- **Access:** Private only

### **Public (Light Version)**
- **URL:** `git@github.com:DmitriyParhomenko/KDP_Builder.git`
- **Contains:** Frontend + basic backend structure
- **Access:** Public (portfolio/showcase)

---

## 🚀 How to Use

### **1. Normal Development**
Work as usual - commit your changes:
```bash
git add .
git commit -m "Your commit message"
```

### **2. Push to Both Repositories**
Use the automated script:
```bash
./push-dual.sh
```

This will:
1. ✅ Push **full version** to private repo
2. ✅ Remove proprietary code (AI, blocks, patterns)
3. ✅ Push **light version** to public repo
4. ✅ Add public README

### **3. Manual Push (if needed)**
```bash
# Push to private only
git push private main

# Push to public only
git push public main
```

---

## 🔒 What's Excluded from Public

The script automatically removes:
- `kdp_builder/ai/` - AI composition engine
- `kdp_builder/blocks/` - Block library system
- `kdp_builder/patterns/` - Pattern database
- `kdp_builder/renderer/` - PDF rendering
- `chroma_db/` - Vector database
- `.env` - Environment variables
- `PRIVATE_*.md` - Private documentation

---

## 📝 Workflow Example

```bash
# 1. Make changes
vim src/components/Canvas.tsx

# 2. Commit
git add .
git commit -m "Add zoom controls"

# 3. Push to both repos
./push-dual.sh
```

---

## 🎯 Benefits

✅ **Private repo:** Full codebase with proprietary AI  
✅ **Public repo:** Clean portfolio piece  
✅ **Automated:** One command pushes to both  
✅ **Safe:** Sensitive code never goes public  

---

## 🔧 Troubleshooting

### If script fails:
```bash
# Check remotes
git remote -v

# Should show:
# private  git@github.com:DmitriyParhomenko/KDP_Builder_FULL.git
# public   git@github.com:DmitriyParhomenko/KDP_Builder.git
```

### Reset if needed:
```bash
# Return to main branch
git checkout main

# Delete temp branch if stuck
git branch -D public-temp
```

---

## 📊 Current Status

- ✅ Private remote configured
- ✅ Public remote configured  
- ✅ Push script created
- ✅ Both repos synced

**Last sync:** Check `git log` for latest commit
