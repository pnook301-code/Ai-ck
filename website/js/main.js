/* ================================================================
   CK-NEXUS AIOS — Website JavaScript
   ================================================================ */

// ── Terminal Typing Animation ──────────────────────────────────
const commands = [
    'nexus up',
    'Starting CK-NEXUS AIOS stack...',
    '✓ PostgreSQL running on :5432',
    '✓ Redis running on :6379',
    '✓ LiteLLM Gateway running on :4000',
    '✓ n8n Automation running on :5678',
    '✓ Qdrant Vector DB running on :6333',
    '✓ Open WebUI running on :3000',
    '',
    'nexus health',
    '  LiteLLM:  ✓',
    '  n8n:      ✓',
    '  Qdrant:   ✓',
    '  WebUI:    ✓',
    '  Postgres: ✓',
    '  Redis:    ✓',
    '',
    'nexus models',
    'Available: 100+ models across 15 providers',
    'Free tier: Groq Llama 3.3 70B, Mixtral 8x7B, Gemma 2',
    'Frontier: GPT-5.5, Claude Opus 4, Gemini Pro',
    '',
    'nexus ask "What is the meaning of life?"',
    '42. But with CK-NEXUS AIOS, you can ask much harder questions.',
];

let cmdIndex = 0;
let charIndex = 0;
let isDeleting = false;
let currentText = '';

function typeTerminal() {
    const terminalText = document.getElementById('terminalText');
    if (!terminalText) return;

    if (cmdIndex >= commands.length) {
        cmdIndex = 0;
        terminalText.parentElement.parentElement.innerHTML = `
            <div class="terminal-line">
                <span class="terminal-prompt">$</span>
                <span class="terminal-text" id="terminalText"></span>
                <span class="terminal-cursor">|</span>
            </div>`;
        typeTerminal();
        return;
    }

    const currentCmd = commands[cmdIndex];

    if (!isDeleting) {
        currentText = currentCmd.substring(0, charIndex + 1);
        charIndex++;

        if (charIndex === currentCmd.length) {
            isDeleting = true;
            setTimeout(typeTerminal, currentCmd === '' ? 200 : 800);
            return;
        }
    } else {
        isDeleting = false;
        charIndex = 0;
        currentText = '';
        cmdIndex++;

        const body = document.getElementById('terminalBody');
        const line = document.createElement('div');
        line.className = 'terminal-line';
        line.innerHTML = `<span class="terminal-prompt">$</span> <span style="color: var(--text-secondary)">${currentCmd}</span>`;
        body.appendChild(line);

        if (body.children.length > 8) {
            body.removeChild(body.firstChild);
        }

        setTimeout(typeTerminal, 100);
        return;
    }

    terminalText.textContent = currentText;
    setTimeout(typeTerminal, isDeleting ? 30 : 60);
}

// ── Stat Counter Animation ─────────────────────────────────────
function animateCounters() {
    document.querySelectorAll('.stat-number[data-count]').forEach(el => {
        const target = parseInt(el.getAttribute('data-count'));
        const duration = 2000;
        const step = target / (duration / 16);
        let current = 0;

        const timer = setInterval(() => {
            current += step;
            if (current >= target) {
                el.textContent = target;
                clearInterval(timer);
            } else {
                el.textContent = Math.floor(current);
            }
        }, 16);
    });
}

// ── Scroll Effects ─────────────────────────────────────────────
function handleScroll() {
    const navbar = document.getElementById('navbar');
    if (window.scrollY > 50) {
        navbar.style.padding = '8px 0';
        navbar.style.background = 'rgba(10, 10, 15, 0.95)';
    } else {
        navbar.style.padding = '16px 0';
        navbar.style.background = 'rgba(10, 10, 15, 0.8)';
    }
}

// ── Intersection Observer for Animations ───────────────────────
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            if (entry.target.classList.contains('hero-stats')) {
                animateCounters();
            }
        }
    });
}, { threshold: 0.1 });

// ── Mobile Navigation ──────────────────────────────────────────
document.getElementById('mobileToggle')?.addEventListener('click', () => {
    const links = document.querySelector('.nav-links');
    const actions = document.querySelector('.nav-actions');
    links.style.display = links.style.display === 'flex' ? 'none' : 'flex';
    actions.style.display = actions.style.display === 'flex' ? 'none' : 'flex';
});

// ── Initialize ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(typeTerminal, 1000);
    window.addEventListener('scroll', handleScroll);

    document.querySelectorAll('.feature-card, .platform-card, .pricing-card, .install-step, .doc-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.5s, transform 0.5s';
        observer.observe(el);
    });

    document.querySelectorAll('.visible').forEach(el => {
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
    });

    const statsObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounters();
                statsObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.3 });

    const statsEl = document.querySelector('.hero-stats');
    if (statsEl) statsObserver.observe(statsEl);
});

// Make elements visible on scroll
const style = document.createElement('style');
style.textContent = `.visible { opacity: 1 !important; transform: translateY(0) !important; }`;
document.head.appendChild(style);
