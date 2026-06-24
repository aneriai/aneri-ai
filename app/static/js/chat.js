/**
 * AneriAI Chat – Front-end logic
 * Connects to /api/chat and /api/health on the Flask back-end.
 */
class ChatBot {
    constructor() {
        this.messagesContainer = document.getElementById('chatMessages');
        this.messageInput      = document.getElementById('messageInput');
        this.sendButton        = document.getElementById('sendButton');
        this.statusText        = document.getElementById('statusText');
        this.statusDot         = document.getElementById('statusDot');
        this.isProcessing      = false;

        this.init();
    }

    init() {
        // Send on Enter (no shift)
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Send button click
        this.sendButton.addEventListener('click', () => this.sendMessage());

        // Auto-resize textarea
        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
        });

        // Focus on load
        this.messageInput.focus();

        // Health check
        this.checkHealth();
    }

    /* ── Health check ── */
    async checkHealth() {
        try {
            const res  = await fetch('/api/health');
            const data = await res.json();

            if (data.status === 'healthy') {
                this.setStatus('Available', 'online');
            } else {
                this.setStatus('Starting…', 'thinking');
            }
        } catch {
            this.setStatus('Connecting…', 'offline');
        }
    }

    /* ── Status helpers ── */
    setStatus(text, type) {
        this.statusText.textContent = text;
        this.statusDot.classList.remove('offline');
        if (type === 'offline') {
            this.statusDot.classList.add('offline');
        } else if (type === 'thinking') {
            this.statusDot.style.background = '#f59e0b';
            this.statusDot.style.animation  = 'none';
        } else {
            this.statusDot.style.background = '#4ade80';
            this.statusDot.style.animation  = '';
        }
    }

    /* ── Send a message ── */
    async sendMessage(overrideText = null) {
        const message = overrideText || this.messageInput.value.trim();
        if (!message || this.isProcessing) return;

        // Clear input
        this.messageInput.value = '';
        this.messageInput.style.height = 'auto';

        // Add user bubble
        this.addMessage(message, 'user');

        // Start loading
        this.showTypingIndicator();
        this.isProcessing = true;
        this.setInputEnabled(false);
        this.setStatus('Thinking…', 'thinking');

        try {
            const res  = await fetch('/api/chat', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ question: message })
            });

            const data = await res.json();
            this.removeTypingIndicator();

            if (data.error && !data.response) {
                this.addMessage('Sorry, I ran into an issue. Please try again.', 'bot');
            } else {
                this.addMessage(data.response, 'bot');
                if (data.sources && data.sources.length > 0) {
                    this.showSources(data.sources);
                }
            }

        } catch (err) {
            this.removeTypingIndicator();
            this.addMessage(
                'Connection problem — please check that the server is running and try again.',
                'bot'
            );
            console.error('Chat error:', err);
        } finally {
            this.isProcessing = false;
            this.setInputEnabled(true);
            this.setStatus('Available', 'online');
            this.scrollToBottom();
            this.messageInput.focus();
        }
    }

    /* ── Add a message bubble ── */
    addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        if (sender === 'user') {
            avatarDiv.textContent = 'You';
        } else {
            avatarDiv.innerHTML = '<img src="/static/img/logo.png" alt="Logo" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">';
        }

        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        textDiv.innerHTML = this.formatMessage(text);

        contentDiv.appendChild(avatarDiv);
        contentDiv.appendChild(textDiv);
        messageDiv.appendChild(contentDiv);

        const ts = document.createElement('div');
        ts.className = 'message-timestamp';
        ts.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        messageDiv.appendChild(ts);

        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    /* ── Format markdown-like text ── */
    formatMessage(text) {
        // Escape HTML first
        let safe = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        // Bold and italic
        safe = safe
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>');

        // Bullet lists
        const lines = safe.split('\n');
        const out   = [];
        let inList  = false;

        for (const line of lines) {
            const isBullet = /^[-•*]\s+/.test(line.trim());
            if (isBullet) {
                if (!inList) { out.push('<ul>'); inList = true; }
                out.push(`<li>${line.replace(/^[-•*]\s+/, '')}</li>`);
            } else {
                if (inList) { out.push('</ul>'); inList = false; }
                if (line.trim() === '') {
                    out.push('</p><p>');
                } else {
                    out.push(line);
                }
            }
        }
        if (inList) out.push('</ul>');

        let html = out.join('\n')
            .replace(/\n/g, ' ')
            .replace(/<\/p><p>\s*<\/p><p>/g, '</p><p>');  // collapse double blanks

        return `<p>${html}</p>`
            .replace(/<p><\/p>/g, '')
            .replace(/<p><ul>/g, '<ul>')
            .replace(/<\/ul><\/p>/g, '</ul>');
    }

    /* ── Typing indicator ── */
    showTypingIndicator() {
        this.removeTypingIndicator();

        const el = document.createElement('div');
        el.id        = 'typingIndicator';
        el.className = 'message bot-message typing-indicator';
        el.innerHTML = `
            <div class="message-content">
                <div class="message-avatar"><img src="/static/img/logo.png" alt="Logo" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;"></div>
                <div class="message-text">
                    <div class="typing-dots">
                        <span></span><span></span><span></span>
                    </div>
                </div>
            </div>`;
        this.messagesContainer.appendChild(el);
        this.scrollToBottom();
    }

    removeTypingIndicator() {
        document.getElementById('typingIndicator')?.remove();
    }

    /* ── Sources panel ── */
    showSources(sources) {
        const div = document.createElement('div');
        div.className = 'sources-container';

        const items = sources.map(s => `
            <div class="source-item">
                <span class="source-score">${Math.round(s.score * 100)}%</span>
                <span class="source-text">${s.text.slice(0, 160)}…</span>
            </div>`).join('');

        div.innerHTML = `
            <details>
                <summary>📄 ${sources.length} source${sources.length > 1 ? 's' : ''} used</summary>
                ${items}
            </details>`;

        this.messagesContainer.appendChild(div);
        this.scrollToBottom();
    }

    /* ── Helpers ── */
    setInputEnabled(enabled) {
        this.messageInput.disabled = !enabled;
        this.sendButton.disabled   = !enabled;
        if (enabled) this.messageInput.focus();
    }

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
}

/* ── Suggestion chip handler (called from HTML) ── */
function askSuggestion(btn) {
    const text = btn.textContent.trim();
    if (window._chatBot) {
        window._chatBot.sendMessage(text);
    }
}

/* ── Bootstrap ── */
document.addEventListener('DOMContentLoaded', () => {
    window._chatBot = new ChatBot();
});