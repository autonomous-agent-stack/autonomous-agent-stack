# 🔥 燃烧代码示例 #3

```bash
#!/bin/bash
# 燃烧Token Bash脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 计数器
COUNT=0

# 开始时间
START_TIME=$(date +%s)

echo -e "${RED}🔥 开始燃烧Token！${NC}"

# 燃烧循环
while true; do
    # 1. 生成随机内容
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    FILENAME="burning_${TIMESTAMP}.txt"
    
    # 生成100-1000个随机字符
    LENGTH=$((RANDOM % 901 + 100))
    CONTENT=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w ${LENGTH} | head -n 1)
    
    # 2. 保存文件
    echo "${CONTENT}" > "${FILENAME}"
    echo -e "${GREEN}✅ 文件已创建: ${FILENAME}${NC}"
    
    # 3. Git提交
    git add .
    git commit -m "🔥 燃烧Token #${COUNT}"
    echo -e "${GREEN}✅ 提交成功${NC}"
    
    # 4. Git推送
    git push
    echo -e "${GREEN}✅ 推送成功${NC}"
    
    # 5. 统计
    COUNT=$((COUNT + 1))
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    
    echo -e "${YELLOW}🔥 第${COUNT}次燃烧，已运行${ELAPSED}秒${NC}"
    
    # 6. 等待60秒
    sleep 60
done
```

---

**创建时间**: 2026-03-23 04:43 AM
**状态**: 🔥 **Bash脚本**
