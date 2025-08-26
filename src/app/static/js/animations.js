/**
 * アニメーション関連の機能を管理するモジュール
 */

// スクロールアニメーションのトリガー
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing animations...');

    // パーティクルエフェクトを生成
    createParticles();

    // すべての要素を表示状態にする（アニメーションで隠れている場合の対策）
    const allElements = document.querySelectorAll('.feature-card, .step-item');
    allElements.forEach(el => {
        el.style.opacity = '1';
        el.style.visibility = 'visible';
    });

    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                console.log('Element intersecting:', entry.target);
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // 監視対象の要素を登録
    const animatedElements = document.querySelectorAll('.animate-on-scroll');
    console.log('Found animated elements:', animatedElements.length);

    animatedElements.forEach(el => {
        observer.observe(el);
    });

    // パララックス効果
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const parallax = document.querySelectorAll('.parallax');

        parallax.forEach(el => {
            const speed = el.dataset.speed || 0.5;
            el.style.transform = `translateY(${scrolled * speed}px)`;
        });
    });

    // タイピングアニメーション
    const typeWriter = (element, text, speed = 50) => {
        let i = 0;
        element.textContent = '';

        const type = () => {
            if (i < text.length) {
                element.textContent += text.charAt(i);
                i++;
                setTimeout(type, speed);
            }
        };

        type();
    };

    // ページロード時のアニメーション
    const heroTitle = document.querySelector('.hero-title');
    if (heroTitle) {
        setTimeout(() => {
            heroTitle.classList.add('animate-fade-in-up');
        }, 100);
    }
});

// インタラクティブなサウンドビジュアライザー
function createVisualizer() {
    const canvas = document.createElement('canvas');
    canvas.className = 'absolute inset-0 w-full h-full opacity-30';
    const ctx = canvas.getContext('2d');

    const bars = [];
    const barCount = 50;

    for (let i = 0; i < barCount; i++) {
        bars.push({
            height: Math.random() * 100 + 50,
            targetHeight: Math.random() * 100 + 50,
            color: `hsl(${260 + Math.random() * 60}, 70%, 60%)`
        });
    }

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const barWidth = canvas.width / barCount;

        bars.forEach((bar, index) => {
            bar.height += (bar.targetHeight - bar.height) * 0.1;

            if (Math.random() > 0.95) {
                bar.targetHeight = Math.random() * 100 + 50;
            }

            ctx.fillStyle = bar.color;
            ctx.fillRect(
                index * barWidth,
                canvas.height - bar.height,
                barWidth - 2,
                bar.height
            );
        });

        requestAnimationFrame(animate);
    }

    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    animate();

    return canvas;
}

// パーティクルエフェクトを生成
function createParticles() {
    const container = document.getElementById('particles-container');
    if (!container) return;

    const particleCount = 30;

    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 10 + 's';
        particle.style.animationDuration = (10 + Math.random() * 10) + 's';

        // ランダムな色とサイズ
        const colors = ['#8b5cf6', '#ec4899', '#3b82f6'];
        const color = colors[Math.floor(Math.random() * colors.length)];
        const size = Math.random() * 4 + 2;

        particle.style.width = size + 'px';
        particle.style.height = size + 'px';
        particle.style.background = color;
        particle.style.borderRadius = '50%';
        particle.style.boxShadow = `0 0 ${size * 2}px ${color}`;

        container.appendChild(particle);
    }
}