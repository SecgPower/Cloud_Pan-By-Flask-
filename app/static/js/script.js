// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 为所有表单添加提交确认
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!confirm('确定要提交表单吗？')) {
                e.preventDefault();
            }
        });
    });
    
    // 添加页面滚动效果
    const navLinks = document.querySelectorAll('nav a');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            // 只处理内部链接
            if (targetId.startsWith('#')) {
                e.preventDefault();
                const targetElement = document.querySelector(targetId);
                if (targetElement) {
                    targetElement.scrollIntoView({
                        behavior: 'smooth'
                    });
                }
            }
        });
    });
});
