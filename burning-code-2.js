# 🔥 燃烧代码示例 #2

```javascript
// 燃烧Token JavaScript版本
const fs = require('fs');
const { execSync } = require('child_process');

class TokenBurner {
    constructor() {
        this.count = 0;
        this.startTime = Date.now();
    }

    // 生成随机内容
    generateContent() {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let content = '';
        const length = Math.floor(Math.random() * 1000) + 100;
        
        for (let i = 0; i < length; i++) {
            content += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        
        return content;
    }

    // 保存文件
    saveFile(content) {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const filename = `burning-${timestamp}.txt`;
        
        fs.writeFileSync(filename, content);
        console.log(`✅ 文件已创建: ${filename}`);
        
        return filename;
    }

    // Git提交
    gitCommit(message) {
        try {
            execSync('git add .', { stdio: 'inherit' });
            execSync(`git commit -m "${message}"`, { stdio: 'inherit' });
            console.log('✅ 提交成功');
        } catch (error) {
            console.error('❌ 提交失败:', error.message);
        }
    }

    // Git推送
    gitPush() {
        try {
            execSync('git push', { stdio: 'inherit' });
            console.log('✅ 推送成功');
        } catch (error) {
            console.error('❌ 推送失败:', error.message);
        }
    }

    // 燃烧循环
    async burn() {
        console.log('🔥 开始燃烧Token！');

        while (true) {
            // 1. 生成内容
            const content = this.generateContent();
            
            // 2. 保存文件
            this.saveFile(content);
            
            // 3. 提交代码
            this.gitCommit('🔥 燃烧Token');
            
            // 4. 推送远程
            this.gitPush();
            
            // 5. 统计
            this.count++;
            const elapsed = (Date.now() - this.startTime) / 1000;
            console.log(`🔥 第${this.count}次燃烧，已运行${elapsed}秒`);
            
            // 6. 等待
            await new Promise(resolve => setTimeout(resolve, 60000)); // 1分钟
        }
    }
}

// 启动
const burner = new TokenBurner();
burner.burn();
```

---

**创建时间**: 2026-03-23 04:42 AM
**状态**: 🔥 **JavaScript示例**
