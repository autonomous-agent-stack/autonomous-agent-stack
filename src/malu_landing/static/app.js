// 玛露遮瑕膏落地页 - 交互逻辑

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('reservationForm');
    const successMessage = document.getElementById('successMessage');
    const errorMessage = document.getElementById('errorMessage');
    const reservationId = document.getElementById('reservationId');
    const errorText = document.getElementById('errorText');
    const submitBtn = document.querySelector('.submit-btn');
    
    // 表单验证
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // 获取表单数据
        const formData = new FormData(form);
        const name = formData.get('name').trim();
        const phone = formData.get('phone').trim();
        const shade = formData.get('shade');
        
        // 验证
        if (!name || name.length < 2) {
            showError('请输入有效的姓名（至少2个字符）');
            return;
        }
        
        if (!phone || !/^1[3-9]\d{9}$/.test(phone)) {
            showError('请输入有效的手机号码');
            return;
        }
        
        if (!shade) {
            showError('请选择色号');
            return;
        }
        
        if (!document.getElementById('agree').checked) {
            showError('请同意隐私政策');
            return;
        }
        
        // 模拟提交
        submitBtn.disabled = true;
        submitBtn.textContent = '提交中...';
        
        // 模拟网络延迟
        setTimeout(function() {
            // 生成预约编号
            const id = 'ML' + Date.now().toString(36).toUpperCase();
            
            // 显示成功消息
            reservationId.textContent = id;
            form.style.display = 'none';
            successMessage.style.display = 'block';
            
            // 重置按钮
            submitBtn.disabled = false;
            submitBtn.textContent = '立即预约';
            
            // 3秒后自动重置
            setTimeout(function() {
                resetForm();
            }, 3000);
            
        }, 1000);
    });
    
    // 重置表单
    function resetForm() {
        form.reset();
        form.style.display = 'block';
        successMessage.style.display = 'none';
        errorMessage.style.display = 'none';
    }
    
    // 显示错误消息
    function showError(message) {
        errorText.textContent = message;
        errorMessage.style.display = 'block';
        
        setTimeout(function() {
            errorMessage.style.display = 'none';
        }, 3000);
    }
    
    // 重试按钮
    document.querySelector('.retry-btn').addEventListener('click', resetForm);
    
    // 实时验证
    document.getElementById('phone').addEventListener('input', function(e) {
        const value = e.target.value.replace(/[^\d]/g, '');
        e.target.value = value;
    });
    
    // 输入框焦点效果
    const inputs = document.querySelectorAll('input, select, textarea');
    inputs.forEach(function(input) {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('focused');
        });
    });
});
